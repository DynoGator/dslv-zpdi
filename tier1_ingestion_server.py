"""dslv-zpdi Tier-1 WSS Ingestion Server — SPEC-008 crypto pipeline.

Receives, authenticates, decrypts, and verifies payloads from Tier-2 mobile
nodes, then routes them through the canonical Layer-2/3 pipeline.

Pipeline (per message):
  1. Bearer-token authentication (at handshake via process_request)
  2. AES-256-GCM envelope decryption  (if enc == "aes-256-gcm")
  3. HMAC-SHA256 signature verification
  4. SHA-256 integrity check
  5. Route via SPEC-007 mobile router
  6. Persist to secondary JSONL log

Environment variables (shared key material with mobile node .env):
  ZPDI_WSS_TOKEN       Bearer token required in Authorization header
  ZPDI_HMAC_SECRET     Shared HMAC-SHA256 secret
  ZPDI_AES_KEY         Base64-encoded 32-byte AES-256-GCM key (optional)
  ZPDI_SERVER_HOST     Bind address          (default: 0.0.0.0)
  ZPDI_SERVER_PORT     Bind port             (default: 8443)
  ZPDI_SERVER_TLS_CERT Path to TLS cert PEM  (omit for plain WS)
  ZPDI_SERVER_TLS_KEY  Path to TLS key PEM
  ZPDI_SECONDARY_LOG   Secondary JSONL path  (default: ./logs/tier1_secondary.jsonl)
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac as hmac_lib
import json
import logging
import os
import ssl
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from websockets.asyncio.server import ServerConnection, serve
from websockets.datastructures import Headers
from websockets.http11 import Request, Response

from src.dslv_zpdi.layer3_telemetry.mobile_router import route_packet, SecondaryLog

logging.basicConfig(
    level=os.environ.get("ZPDI_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("zpdi.tier1")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_WSS_TOKEN: str = os.environ.get("ZPDI_WSS_TOKEN", "")
_HMAC_SECRET: bytes = os.environ.get("ZPDI_HMAC_SECRET", "").encode("utf-8")
_AES_KEY_B64: str = os.environ.get("ZPDI_AES_KEY", "")
SERVER_HOST: str = os.environ.get("ZPDI_SERVER_HOST", "0.0.0.0")
SERVER_PORT: int = int(os.environ.get("ZPDI_SERVER_PORT", "8443"))
TLS_CERT: str | None = os.environ.get("ZPDI_SERVER_TLS_CERT")
TLS_KEY: str | None = os.environ.get("ZPDI_SERVER_TLS_KEY")
SECONDARY_LOG_PATH = Path(os.environ.get("ZPDI_SECONDARY_LOG", "./logs/tier1_secondary.jsonl"))

_secondary_log = SecondaryLog(SECONDARY_LOG_PATH)


# ---------------------------------------------------------------------------
# Crypto helpers
# ---------------------------------------------------------------------------

def _load_aesgcm() -> AESGCM | None:
    if not _AES_KEY_B64:
        return None
    try:
        key = base64.b64decode(_AES_KEY_B64)
        if len(key) != 32:
            log.error("ZPDI_AES_KEY must be 32 bytes after base64 decode (got %d)", len(key))
            return None
        return AESGCM(key)
    except Exception as exc:
        log.error("Failed to load ZPDI_AES_KEY: %s", exc)
        return None


_AESGCM: AESGCM | None = _load_aesgcm()


def _decrypt_envelope(aesgcm: AESGCM, envelope: dict[str, Any]) -> bytes | None:
    """Decrypt an AES-256-GCM envelope dict; return plaintext or None on failure."""
    try:
        nonce = base64.b64decode(envelope["nonce"])
        ct = base64.b64decode(envelope["ct"])
        return aesgcm.decrypt(nonce, ct, None)
    except (KeyError, ValueError, Exception) as exc:
        log.warning("AES-256-GCM decryption failed: %s", exc)
        return None


def _verify_hmac(raw: bytes, received_hex: str) -> bool:
    """Constant-time HMAC-SHA256 verification."""
    if not _HMAC_SECRET:
        return True  # HMAC not configured — skip verification
    expected = hmac_lib.new(_HMAC_SECRET, raw, hashlib.sha256).hexdigest()
    return hmac_lib.compare_digest(expected, received_hex)


def _verify_sha256(raw: bytes, received_hex: str) -> bool:
    """Verify SHA-256 digest of the canonical payload bytes."""
    actual = hashlib.sha256(raw).hexdigest()
    return hmac_lib.compare_digest(actual, received_hex)


# ---------------------------------------------------------------------------
# Handshake authentication hook
# ---------------------------------------------------------------------------

def _make_auth_hook(token: str):
    """Return a process_request hook that enforces Bearer-token authentication."""
    def process_request(conn: ServerConnection, request: Request) -> Response | None:
        if not token:
            return None  # Auth not configured — allow all connections
        auth = request.headers.get("Authorization", "")
        if auth == f"Bearer {token}":
            return None  # Proceed
        log.warning("Rejected connection: invalid or missing Bearer token (peer=%s)", conn.remote_address)
        return Response(
            401,
            "Unauthorized",
            Headers([("Content-Type", "text/plain"), ("WWW-Authenticate", "Bearer")]),
            b"Unauthorized\n",
        )
    return process_request


# ---------------------------------------------------------------------------
# Payload processing
# ---------------------------------------------------------------------------

@dataclass
class _IngestResult:
    accepted: bool
    reason: str
    node: str = ""
    modality: str = ""
    route_stream: str = ""


def _process_message(raw_message: str | bytes) -> _IngestResult:
    """Full SPEC-008 ingestion pipeline for a single WebSocket message."""

    # --- 1. Parse outer JSON ---
    try:
        if isinstance(raw_message, bytes):
            outer = json.loads(raw_message.decode("utf-8"))
        else:
            outer = json.loads(raw_message)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return _IngestResult(False, f"JSON parse error: {exc}")

    if not isinstance(outer, dict):
        return _IngestResult(False, "payload is not a JSON object")

    # --- 2. AES-256-GCM decryption (if envelope present) ---
    if outer.get("enc") == "aes-256-gcm":
        if _AESGCM is None:
            return _IngestResult(False, "encrypted payload received but ZPDI_AES_KEY not configured")
        plaintext = _decrypt_envelope(_AESGCM, outer)
        if plaintext is None:
            return _IngestResult(False, "AES-256-GCM decryption failed")
        try:
            body = json.loads(plaintext.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return _IngestResult(False, f"inner JSON parse error after decrypt: {exc}")
    else:
        body = outer

    if not isinstance(body, dict):
        return _IngestResult(False, "inner payload is not a JSON object")

    # --- 3. Extract and strip authentication fields ---
    received_sha256 = body.pop("sha256", None)
    received_hmac = body.pop("hmac", None)

    # Reconstruct canonical bytes (same serialisation as the mobile node)
    try:
        canonical_raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        return _IngestResult(False, f"canonical serialisation failed: {exc}")

    # --- 4. SHA-256 integrity check ---
    if received_sha256 is not None:
        if not _verify_sha256(canonical_raw, received_sha256):
            return _IngestResult(False, "SHA-256 integrity check FAILED")
    else:
        log.debug("payload has no sha256 field — skipping integrity check")

    # --- 5. HMAC-SHA256 signature verification ---
    if _HMAC_SECRET:
        if received_hmac is None:
            return _IngestResult(False, "HMAC required (ZPDI_HMAC_SECRET set) but payload has no hmac field")
        if not _verify_hmac(canonical_raw, received_hmac):
            return _IngestResult(False, "HMAC-SHA256 verification FAILED")

    # Restore sha256 for downstream consumers
    if received_sha256 is not None:
        body["sha256"] = received_sha256

    # --- 6. Route via SPEC-007 ---
    route = route_packet(body)
    body["route"] = route

    # --- 7. Persist to secondary log ---
    _secondary_log._write_sync(body)  # synchronous — called from async context via to_thread

    node = body.get("node", body.get("node_id", "unknown"))
    modality = body.get("modality", "unknown")
    r_smooth = body.get("r_smooth", 0.0)
    log.info(
        "ACCEPTED node=%s modality=%s r_smooth=%.3f stream=%s",
        node, modality, r_smooth, route.get("stream", "?"),
    )
    return _IngestResult(True, "ok", node=node, modality=modality, route_stream=route.get("stream", ""))


# ---------------------------------------------------------------------------
# WebSocket handler
# ---------------------------------------------------------------------------

_stats = {"accepted": 0, "rejected": 0, "connections": 0}


async def _handle_connection(websocket: ServerConnection) -> None:
    addr = websocket.remote_address
    _stats["connections"] += 1
    log.info("Connection established from %s (total=%d)", addr, _stats["connections"])
    try:
        async for message in websocket:
            result = await asyncio.to_thread(_process_message, message)
            if result.accepted:
                _stats["accepted"] += 1
            else:
                _stats["rejected"] += 1
                log.warning("REJECTED from %s: %s", addr, result.reason)
    except Exception as exc:
        log.debug("Connection from %s closed with error: %s", addr, exc)
    finally:
        log.info("Disconnected from %s (accepted=%d rejected=%d)",
                 addr, _stats["accepted"], _stats["rejected"])


# ---------------------------------------------------------------------------
# TLS / SSL context
# ---------------------------------------------------------------------------

def _build_ssl_context() -> ssl.SSLContext | None:
    if not TLS_CERT or not TLS_KEY:
        return None
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        ctx.load_cert_chain(TLS_CERT, TLS_KEY)
        log.info("TLS enabled: cert=%s", TLS_CERT)
        return ctx
    except (ssl.SSLError, FileNotFoundError) as exc:
        log.error("Failed to load TLS cert/key: %s — falling back to plain WS", exc)
        return None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    _secondary_log.prepare()

    ssl_ctx = _build_ssl_context()
    scheme = "wss" if ssl_ctx else "ws"

    if _WSS_TOKEN:
        log.info("Bearer-token authentication ENABLED")
    else:
        log.warning("ZPDI_WSS_TOKEN not set — accepting all connections without auth")

    if _HMAC_SECRET:
        log.info("HMAC-SHA256 verification ENABLED")
    else:
        log.warning("ZPDI_HMAC_SECRET not set — HMAC verification disabled")

    if _AESGCM:
        log.info("AES-256-GCM decryption ENABLED")
    else:
        log.info("ZPDI_AES_KEY not set — encrypted payloads will be rejected")

    auth_hook = _make_auth_hook(_WSS_TOKEN)

    log.info("Tier-1 ingestion server starting on %s://%s:%d", scheme, SERVER_HOST, SERVER_PORT)

    async with serve(
        _handle_connection,
        SERVER_HOST,
        SERVER_PORT,
        ssl=ssl_ctx,
        process_request=auth_hook,
        ping_interval=20,
        ping_timeout=10,
        close_timeout=5,
        max_size=2 ** 20,
    ):
        log.info("Server ready — awaiting Tier-2 connections")
        await asyncio.Future()  # run until cancelled


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Server stopped by user")
        sys.exit(0)
