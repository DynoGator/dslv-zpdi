"""dslv-zpdi Tier-1 mobile metrology node (Rev 3.5 — Hardened).

Asynchronous daemon that polls Termux sensors from inside a Debian proot,
enriches each payload with GPS location when available, signs with
HMAC-SHA256 for provenance, optionally encrypts with AES-256-GCM, and
fans out to local HDF5 storage and a hardened WSS transport with circuit-
breaker backoff and silent failover to a JSONL log if the socket drops.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import hmac
import json
import logging
import os
import secrets
import signal
import sqlite3
import ssl
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import websockets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from websockets.asyncio.client import ClientConnection
from websockets.exceptions import ConnectionClosed, InvalidHandshake, WebSocketException
from websockets.protocol import State

from src.layer1_ingestion.gps_poller import GPSPoller
from src.layer1_ingestion.mobile_ingestion import (
    build_mobile_payload,
    IngestionPayload,
    SENSORS,
    TERMUX_SENSOR_BIN,
    score_mobile_payload,
)
from src.layer3_telemetry.mobile_router import route_packet, SecondaryLog

# ---------------------------------------------------------------------------
# Environment-configurable constants
# ---------------------------------------------------------------------------
DEFAULT_STREAM_DELAY_MS = int(os.environ.get("ZPDI_STREAM_DELAY_MS", "250"))
DEFAULT_WSS_URI = os.environ.get("ZPDI_WSS_URI", "wss://edge.placeholder.invalid:8443/ingest")
DEFAULT_HDF5_PATH = Path(os.environ.get("ZPDI_HDF5_PATH", "./data/zpdi_stream.h5"))
DEFAULT_SQLITE_PATH = Path(os.environ.get("ZPDI_SQLITE_PATH", "./data/zpdi_cache.db"))
DEFAULT_FALLBACK_LOG = Path(os.environ.get("ZPDI_FALLBACK_LOG", "./logs/zpdi_fallback.jsonl"))
DEFAULT_HEALTH_LOG = Path(os.environ.get("ZPDI_HEALTH_LOG", "./logs/health.jsonl"))
DEFAULT_CA_BUNDLE = os.environ.get("ZPDI_WSS_CA_BUNDLE") or None
DEFAULT_WSS_TOKEN = os.environ.get("ZPDI_WSS_TOKEN", "")
DEFAULT_HMAC_SECRET = os.environ.get("ZPDI_HMAC_SECRET", "").encode("utf-8")
DEFAULT_NODE_ID = os.environ.get("ZPDI_NODE_ID", "dslv-zpdi/mobile-tier2")
DEFAULT_AES_KEY_B64 = os.environ.get("ZPDI_AES_KEY", "")

QUEUE_MAX = 4096
HDF5_DATASET = "payloads"
HDF5_CHUNK = 256

log = logging.getLogger("zpdi")

# Module-level stream liveness counter
_stream_sample_count = 0


@dataclass(frozen=True)
class Payload:
    """A single hashed, signed sensor sample ready for both sinks."""

    body: dict[str, Any]
    raw: bytes      # canonical JSON bytes — the exact bytes that were hashed
    digest: str     # hex SHA-256 of `raw`


# ---------------------------------------------------------------------------
# Crypto helpers
# ---------------------------------------------------------------------------

def _load_aes_key() -> AESGCM | None:
    """Load AES-256-GCM key from base64 env var, if present."""
    if not DEFAULT_AES_KEY_B64:
        return None
    try:
        key = base64.b64decode(DEFAULT_AES_KEY_B64)
        if len(key) != 32:
            log.error("ZPDI_AES_KEY must decode to exactly 32 bytes (got %d)", len(key))
            return None
        return AESGCM(key)
    except Exception as exc:
        log.error("Failed to load ZPDI_AES_KEY: %s", exc)
        return None


def _encrypt_payload(aesgcm: AESGCM, plaintext: bytes) -> dict[str, str]:
    """Encrypt plaintext with AES-256-GCM and return an envelope dict."""
    nonce = secrets.token_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return {
        "enc": "aes-256-gcm",
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ct": base64.b64encode(ciphertext).decode("ascii"),
    }


def _sign_payload(raw: bytes, secret: bytes) -> str:
    """Compute HMAC-SHA256 over raw bytes and return hex digest."""
    if not secret:
        return ""
    return hmac.new(secret, raw, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Sensor streaming
# ---------------------------------------------------------------------------

async def _release_sensors() -> None:
    """Fire `termux-sensor -c` to tell Android to release sensor handles."""
    try:
        proc = await asyncio.create_subprocess_exec(
            TERMUX_SENSOR_BIN, "-c",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await asyncio.wait_for(proc.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            await proc.wait()
    except Exception as exc:
        log.debug("sensor release call failed: %s", exc)


async def _drain_stderr(stream: asyncio.StreamReader) -> None:
    """Drain termux-sensor stderr so a full pipe never blocks the writer."""
    while True:
        line = await stream.readline()
        if not line:
            return
        log.debug("termux-sensor stderr: %s", line.decode("utf-8", errors="replace").rstrip())


async def _consume_stream(
    stdout: asyncio.StreamReader,
    queues: tuple[asyncio.Queue[Payload], ...],
    gps_poller: GPSPoller,
) -> None:
    """Parse termux-sensor's continuous JSON stream and fan out to queues."""
    decoder = json.JSONDecoder()
    buf = ""
    while True:
        line = await stdout.readline()
        if not line:
            return
        buf += line.decode("utf-8", errors="replace")
        while True:
            stripped = buf.lstrip()
            if not stripped:
                buf = ""
                break
            try:
                reading, idx = decoder.raw_decode(stripped)
            except json.JSONDecodeError:
                buf = stripped
                break
            buf = stripped[idx:]
            if not isinstance(reading, dict):
                continue
            # Fetch latest location fix (non-blocking)
            loc = await gps_poller.get_latest()
            loc_dict = loc.to_dict() if loc else None
            for sensor_name, sensor_reading in reading.items():
                if sensor_name not in SENSORS:
                    continue
                ingestion = build_mobile_payload(sensor_name, sensor_reading, loc_dict)
                ingestion.node_id = DEFAULT_NODE_ID
                payload = _ingestion_to_legacy(ingestion)
                if payload is None:
                    continue
                global _stream_sample_count
                _stream_sample_count += 1
                for q in queues:
                    try:
                        q.put_nowait(payload)
                    except asyncio.QueueFull:
                        with contextlib.suppress(asyncio.QueueEmpty):
                            q.get_nowait()
                        try:
                            q.put_nowait(payload)
                        except asyncio.QueueFull:
                            pass


async def _stream(
    queues: tuple[asyncio.Queue[Payload], ...],
    stop: asyncio.Event,
    gps_poller: GPSPoller,
) -> None:
    """Keep a termux-sensor subprocess alive for the daemon's lifetime."""
    backoff = 0.5
    while not stop.is_set():
        cmd = [
            TERMUX_SENSOR_BIN,
            "-s", ",".join(SENSORS),
            "-d", str(DEFAULT_STREAM_DELAY_MS),
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
        except (FileNotFoundError, OSError) as exc:
            log.error("failed to spawn termux-sensor: %s", exc)
            try:
                await asyncio.wait_for(stop.wait(), timeout=backoff)
                return
            except asyncio.TimeoutError:
                backoff = min(backoff * 2, 5.0)
                continue

        log.info("termux-sensor stream started pid=%s delay=%dms sensors=%d", proc.pid, DEFAULT_STREAM_DELAY_MS, len(SENSORS))
        backoff = 0.5
        assert proc.stdout is not None and proc.stderr is not None
        stderr_task = asyncio.create_task(_drain_stderr(proc.stderr))
        consume_task = asyncio.create_task(_consume_stream(proc.stdout, queues, gps_poller))
        stop_task = asyncio.create_task(stop.wait())
        try:
            await asyncio.wait(
                {consume_task, stop_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(proc.pid, signal.SIGTERM)
            try:
                await asyncio.wait_for(proc.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.killpg(proc.pid, signal.SIGKILL)
                await proc.wait()
            await _release_sensors()
            for t in (consume_task, stderr_task, stop_task):
                if not t.done():
                    t.cancel()
            for t in (consume_task, stderr_task, stop_task):
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await t

        if stop.is_set():
            return
        log.warning("termux-sensor stream ended (rc=%s); restarting", proc.returncode)
        await asyncio.sleep(0.5)


def _ingestion_to_legacy(ingestion: IngestionPayload) -> Payload | None:
    """Convert a canonical IngestionPayload to the legacy Payload shape."""
    json_str = ingestion.to_json()
    if json_str is None:
        return None
    body = json.loads(json_str)
    body["node"] = ingestion.node_id
    body["schema"] = ingestion.schema_version
    body["timestamps"] = {
        "wall_ns": int(ingestion.timestamp_utc * 1e9),
        "monotonic_ns": ingestion.ingest_monotonic_ns,
    }
    coherence = score_mobile_payload(ingestion)
    if coherence is not None:
        body["r_local"] = coherence.r_local
        body["r_smooth"] = coherence.r_smooth
        body["r_global"] = coherence.r_global
    body["route"] = route_packet(body)
    canonical = {k: v for k, v in body.items() if k != "sha256"}
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    body["sha256"] = digest
    # HMAC authentication (SPEC-008)
    if DEFAULT_HMAC_SECRET:
        body["hmac"] = _sign_payload(raw, DEFAULT_HMAC_SECRET)
    return Payload(body=body, raw=raw, digest=digest)


# ---------------------------------------------------------------------------
# HDF5 sink
# ---------------------------------------------------------------------------

class HDF5Sink:
    """Append-only, resizable HDF5 dataset of JSON-encoded payloads + digests."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._file: h5py.File | None = None
        self._dset: h5py.Dataset | None = None
        self._lock = asyncio.Lock()

    def open(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = h5py.File(self._path, "a", libver="latest")
        if HDF5_DATASET in self._file:
            self._dset = self._file[HDF5_DATASET]
        else:
            dtype = np.dtype([
                ("wall_ns", "<u8"),
                ("sha256", "S64"),
                ("payload", h5py.vlen_dtype(bytes)),
            ])
            self._dset = self._file.create_dataset(
                HDF5_DATASET,
                shape=(0,),
                maxshape=(None,),
                chunks=(HDF5_CHUNK,),
                dtype=dtype,
            )
        with contextlib.suppress(Exception):
            self._file.swmr_mode = True

    def close(self) -> None:
        if self._file is not None:
            with contextlib.suppress(Exception):
                self._file.flush()
            self._file.close()
            self._file = None
            self._dset = None

    async def append(self, p: Payload) -> None:
        if self._dset is None:
            return
        route = p.body.get("route", {})
        if route.get("stream") != "PRIMARY":
            return
        async with self._lock:
            await asyncio.to_thread(self._append_sync, p)

    def _append_sync(self, p: Payload) -> None:
        assert self._dset is not None and self._file is not None
        n = self._dset.shape[0]
        self._dset.resize((n + 1,))
        self._dset[n] = (
            int(p.body["timestamps"]["wall_ns"]),
            p.digest.encode("ascii"),
            p.raw,
        )
        self._file.flush()


# ---------------------------------------------------------------------------
# Fallback JSONL log
# ---------------------------------------------------------------------------

class FallbackLog:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()

    def prepare(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    async def write(self, p: Payload) -> None:
        async with self._lock:
            await asyncio.to_thread(self._write_sync, p)

    def _write_sync(self, p: Payload) -> None:
        full_raw = json.dumps(p.body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        with self._path.open("ab") as fh:
            fh.write(full_raw)
            fh.write(b"\n")


# ---------------------------------------------------------------------------
# SQLite Cache (for Web Server)
# ---------------------------------------------------------------------------

class SQLiteCache:
    """Lightweight, WAL-mode cache for the latest sensor state."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._conn: sqlite3.Connection | None = None

    def open(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS latest_state ("
            "  id INTEGER PRIMARY KEY CHECK (id = 1),"
            "  wall_ns INTEGER,"
            "  payload TEXT"
            ")"
        )
        self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    async def update(self, p: Payload) -> None:
        if self._conn:
            await asyncio.to_thread(self._update_sync, p)

    def _update_sync(self, p: Payload) -> None:
        assert self._conn is not None
        self._conn.execute(
            "INSERT OR REPLACE INTO latest_state (id, wall_ns, payload) "
            "VALUES (1, ?, ?)",
            (int(p.body["timestamps"]["wall_ns"]), json.dumps(p.body))
        )
        self._conn.commit()


# ---------------------------------------------------------------------------
# Hardened WSS transport with circuit-breaker backoff
# ---------------------------------------------------------------------------

class WSSTransport:
    """Maintains a single WSS connection with jittered exponential backoff
    and circuit-breaker silent failover.
    """

    CIRCUIT_OPEN_THRESHOLD = 5          # consecutive failures before opening
    CIRCUIT_OPEN_COOLDOWN_S = 30.0      # seconds to stay open before half-open

    def __init__(
        self,
        uri: str,
        ca_bundle: str | None,
        fallback: FallbackLog,
        token: str,
        aesgcm: AESGCM | None,
    ) -> None:
        self._uri = uri
        self._ssl_ctx = self._build_ssl_ctx(ca_bundle)
        self._fallback = fallback
        self._token = token
        self._aesgcm = aesgcm
        self._ws: ClientConnection | None = None
        self._connect_lock = asyncio.Lock()
        self._consecutive_failures = 0
        self._circuit_open_until: float = 0.0

    @property
    def connected(self) -> bool:
        return self._ws is not None and self._ws.state.name == "OPEN"

    def _build_ssl_ctx(self, ca_bundle: str | None) -> ssl.SSLContext | None:
        if self._uri.startswith("ws://"):
            return None
        ctx = ssl.create_default_context()
        if ca_bundle:
            ctx.load_verify_locations(cafile=ca_bundle)
        return ctx

    def _circuit_open(self) -> bool:
        return time.monotonic() < self._circuit_open_until

    async def _ensure_connection(self) -> bool:
        if self._ws is not None and self._ws.state.name == "OPEN":
            return True
        if self._circuit_open():
            return False
        async with self._connect_lock:
            if self._ws is not None and self._ws.state.name == "OPEN":
                return True
            if self._circuit_open():
                return False
            try:
                extra_headers = {}
                if self._token:
                    extra_headers["Authorization"] = f"Bearer {self._token}"
                is_secure = self._uri.startswith("wss://")
                self._ws = await asyncio.wait_for(
                    websockets.connect(
                        self._uri,
                        ssl=self._ssl_ctx if is_secure else None,
                        ping_interval=20,
                        ping_timeout=10,
                        close_timeout=2,
                        max_size=2**20,
                        additional_headers=extra_headers,
                    ),
                    timeout=5.0,
                )
                log.info("WSS connected: %s", self._uri)
                self._consecutive_failures = 0
                return True
            except (OSError, asyncio.TimeoutError, InvalidHandshake, WebSocketException) as exc:
                log.debug("WSS connect failed: %s", exc)
                self._consecutive_failures += 1
                if self._consecutive_failures >= self.CIRCUIT_OPEN_THRESHOLD:
                    self._circuit_open_until = time.monotonic() + self.CIRCUIT_OPEN_COOLDOWN_S
                    log.warning("WSS circuit breaker OPEN for %.0fs after %d failures", self.CIRCUIT_OPEN_COOLDOWN_S, self._consecutive_failures)
                self._ws = None
                return False

    async def send(self, p: Payload) -> None:
        if await self._ensure_connection():
            try:
                assert self._ws is not None
                full_raw = json.dumps(p.body, sort_keys=True, separators=(",", ":")).encode("utf-8")
                # Optional payload-level encryption (SPEC-008)
                if self._aesgcm is not None:
                    envelope = _encrypt_payload(self._aesgcm, full_raw)
                    wire_raw = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
                else:
                    wire_raw = full_raw
                await self._ws.send(wire_raw)
                return
            except (ConnectionClosed, WebSocketException, OSError) as exc:
                log.debug("WSS send failed, will fail over: %s", exc)
                with contextlib.suppress(Exception):
                    await self._ws.close()
                self._ws = None
        # Silent failover
        await self._fallback.write(p)

    async def aclose(self) -> None:
        if self._ws is not None:
            with contextlib.suppress(Exception):
                await self._ws.close()
            self._ws = None


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

async def _storage_consumer(
    queue: asyncio.Queue[Payload],
    sink: HDF5Sink,
    stop: asyncio.Event,
) -> None:
    while not (stop.is_set() and queue.empty()):
        try:
            p = await asyncio.wait_for(queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            continue
        try:
            await sink.append(p)
        except Exception as exc:
            log.exception("HDF5 append failed: %s", exc)


async def _cache_consumer(
    queue: asyncio.Queue[Payload],
    cache: SQLiteCache,
    stop: asyncio.Event,
) -> None:
    while not (stop.is_set() and queue.empty()):
        try:
            p = await asyncio.wait_for(queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            continue
        try:
            await cache.update(p)
        except Exception as exc:
            log.exception("SQLite cache update failed: %s", exc)


async def _transport_consumer(
    queue: asyncio.Queue[Payload],
    transport: WSSTransport,
    secondary: SecondaryLog,
    stop: asyncio.Event,
) -> None:
    while not (stop.is_set() and queue.empty()):
        try:
            p = await asyncio.wait_for(queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            continue
        try:
            await secondary.write(p)
        except Exception as exc:
            log.exception("secondary log write failed: %s", exc)
        try:
            await transport.send(p)
        except Exception as exc:
            log.exception("transport send failed unexpectedly: %s", exc)


async def _health_watchdog(
    path: Path,
    queues: tuple[asyncio.Queue[Payload], ...],
    transport: WSSTransport,
    gps_poller: GPSPoller,
    stop: asyncio.Event,
) -> None:
    """Write health heartbeat every 30s; supervisor checks staleness."""
    path.parent.mkdir(parents=True, exist_ok=True)
    prev_sample_count = _stream_sample_count
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=30.0)
            return
        except asyncio.TimeoutError:
            pass
        current_count = _stream_sample_count
        sensor_alive = current_count > prev_sample_count
        prev_sample_count = current_count
        loc = await gps_poller.get_latest()
        record = {
            "ts_utc": time.time(),
            "pid": os.getpid(),
            "sensor_alive": sensor_alive,
            "queue_depths": [q.qsize() for q in queues],
            "wss_connected": transport.connected,
            "wss_circuit_open": transport._circuit_open(),
            "gps_fix": loc.to_dict() if loc else None,
        }
        try:
            with path.open("a") as fh:
                fh.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
                fh.write("\n")
        except Exception as exc:
            log.debug("health write failed: %s", exc)


async def main() -> int:
    logging.basicConfig(
        level=os.environ.get("ZPDI_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    aesgcm = _load_aes_key()
    if aesgcm:
        log.info("AES-256-GCM payload encryption ENABLED")
    if DEFAULT_HMAC_SECRET:
        log.info("HMAC-SHA256 payload signing ENABLED")
    if DEFAULT_WSS_TOKEN:
        log.info("WSS Bearer token authentication ENABLED")

    hdf5_sink = HDF5Sink(DEFAULT_HDF5_PATH)
    hdf5_sink.open()
    cache = SQLiteCache(DEFAULT_SQLITE_PATH)
    cache.open()
    fallback = FallbackLog(DEFAULT_FALLBACK_LOG)
    fallback.prepare()
    secondary = SecondaryLog(DEFAULT_FALLBACK_LOG)
    secondary.prepare()
    transport = WSSTransport(DEFAULT_WSS_URI, DEFAULT_CA_BUNDLE, fallback, DEFAULT_WSS_TOKEN, aesgcm)
    gps_poller = GPSPoller()

    storage_q: asyncio.Queue[Payload] = asyncio.Queue(maxsize=QUEUE_MAX)
    cache_q: asyncio.Queue[Payload] = asyncio.Queue(maxsize=QUEUE_MAX)
    transport_q: asyncio.Queue[Payload] = asyncio.Queue(maxsize=QUEUE_MAX)
    stop = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)

    tasks = [
        asyncio.create_task(_stream((storage_q, cache_q, transport_q), stop, gps_poller), name="stream"),
        asyncio.create_task(gps_poller.run(), name="gps"),
        asyncio.create_task(_storage_consumer(storage_q, hdf5_sink, stop), name="storage"),
        asyncio.create_task(_cache_consumer(cache_q, cache, stop), name="cache"),
        asyncio.create_task(_transport_consumer(transport_q, transport, secondary, stop), name="transport"),
        asyncio.create_task(_health_watchdog(DEFAULT_HEALTH_LOG, (storage_q, cache_q, transport_q), transport, gps_poller, stop), name="health"),
    ]

    log.info("zpdi node up — delay=%dms sensors=%d node=%s", DEFAULT_STREAM_DELAY_MS, len(SENSORS), DEFAULT_NODE_ID)
    try:
        await stop.wait()
    finally:
        log.info("shutdown signal received — draining")
        gps_poller.stop()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await transport.aclose()
        hdf5_sink.close()
        cache.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
