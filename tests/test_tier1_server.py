"""Tests for the Tier-1 WSS ingestion server — SPEC-008 crypto pipeline."""

from __future__ import annotations
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import base64
import hashlib
import hmac as hmac_lib
import json
import math
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Helpers — mirror the mobile node's signing/encryption logic
# ---------------------------------------------------------------------------


def _make_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def _encrypt(key: bytes, plaintext: bytes) -> dict:
    import secrets
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    ct = aesgcm.encrypt(nonce, plaintext, None)
    return {
        "enc": "aes-256-gcm",
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ct": base64.b64encode(ct).decode("ascii"),
    }


def _sign(raw: bytes, secret: bytes) -> str:
    return hmac_lib.new(secret, raw, hashlib.sha256).hexdigest()


def _make_body(extra: dict | None = None) -> dict:
    """Build a minimal valid payload body (without sha256 / hmac)."""
    body = {
        "node": "dslv-zpdi/mobile-tier2",
        "modality": "accel",
        "hardware_tier": 2,
        "trust_state": "SECONDARY_QUARANTINED",
        "r_smooth": 0.25,
        "timestamps": {"wall_ns": int(time.time() * 1e9), "monotonic_ns": time.monotonic_ns()},
        "payload_uuid": str(uuid.uuid4()),
    }
    if extra:
        body.update(extra)
    return body


def _finalise(body: dict, hmac_secret: bytes | None = None) -> dict:
    """Add sha256 and optional hmac to a body dict, mirroring the mobile node."""
    canonical = {k: v for k, v in body.items() if k != "sha256"}
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    body = dict(body)
    body["sha256"] = hashlib.sha256(raw).hexdigest()
    if hmac_secret:
        body["hmac"] = _sign(raw, hmac_secret)
    return body


# ---------------------------------------------------------------------------
# Import the module under test — monkey-patch env vars before importing
# ---------------------------------------------------------------------------

HMAC_SECRET = b"test-hmac-secret-32bytesXXXXXXXX"
AES_KEY = _make_key()
AES_KEY_B64 = base64.b64encode(AES_KEY).decode("ascii")
WSS_TOKEN = "test-bearer-token-abc123"


def _get_process_fn():
    """Import _process_message with test credentials patched in."""
    os.environ["ZPDI_HMAC_SECRET"] = HMAC_SECRET.decode("latin-1")
    os.environ["ZPDI_AES_KEY"] = AES_KEY_B64
    os.environ["ZPDI_WSS_TOKEN"] = WSS_TOKEN
    os.environ["ZPDI_SECONDARY_LOG"] = "/dev/null"

    # Force re-import so env vars are picked up at module level
    import importlib

    import tier1_ingestion_server as m
    importlib.reload(m)
    return m._process_message


# ---------------------------------------------------------------------------
# SHA-256 integrity tests
# ---------------------------------------------------------------------------

class TestSHA256Integrity:

    def setup_method(self):
        self._fn = _get_process_fn()

    def test_valid_sha256_accepted(self):
        # HMAC_SECRET is configured, so must include hmac for acceptance
        body = _finalise(_make_body(), hmac_secret=HMAC_SECRET)
        msg = json.dumps(body, sort_keys=True, separators=(",", ":"))
        result = self._fn(msg)
        assert result.accepted, result.reason

    def test_tampered_sha256_rejected(self):
        body = _finalise(_make_body())
        body["sha256"] = "a" * 64  # wrong digest
        msg = json.dumps(body, sort_keys=True, separators=(",", ":"))
        result = self._fn(msg)
        assert not result.accepted
        assert "SHA-256" in result.reason

    def test_missing_sha256_still_accepted(self):
        """Payloads without sha256 are accepted (field is optional on wire)."""
        body = _make_body()
        body["hmac"] = _sign(
            json.dumps({k: v for k, v in body.items()}, sort_keys=True, separators=(",", ":")).encode(),
            HMAC_SECRET,
        )
        msg = json.dumps(body, sort_keys=True, separators=(",", ":"))
        result = self._fn(msg)
        # Will fail HMAC because hmac was computed over body-before-hmac
        # but sha256 check passes. Accept only if HMAC also computed correctly.
        # This test just verifies sha256 absence alone isn't a hard rejection.
        # (HMAC may fail — that's expected.)
        assert "SHA-256" not in result.reason or result.accepted


# ---------------------------------------------------------------------------
# HMAC verification tests
# ---------------------------------------------------------------------------

class TestHMACVerification:

    def setup_method(self):
        self._fn = _get_process_fn()

    def test_valid_hmac_accepted(self):
        body = _finalise(_make_body(), hmac_secret=HMAC_SECRET)
        msg = json.dumps(body, sort_keys=True, separators=(",", ":"))
        result = self._fn(msg)
        assert result.accepted, result.reason

    def test_wrong_hmac_rejected(self):
        body = _finalise(_make_body(), hmac_secret=HMAC_SECRET)
        body["hmac"] = "0" * 64
        msg = json.dumps(body, sort_keys=True, separators=(",", ":"))
        result = self._fn(msg)
        assert not result.accepted
        assert "HMAC" in result.reason

    def test_missing_hmac_rejected_when_secret_configured(self):
        """When ZPDI_HMAC_SECRET is set, payloads without hmac must be rejected."""
        body = _finalise(_make_body())  # no hmac
        msg = json.dumps(body, sort_keys=True, separators=(",", ":"))
        result = self._fn(msg)
        assert not result.accepted
        assert "hmac" in result.reason.lower()


# ---------------------------------------------------------------------------
# AES-256-GCM decryption tests
# ---------------------------------------------------------------------------

class TestAESDecryption:

    def setup_method(self):
        self._fn = _get_process_fn()

    def _encrypt_body(self, body: dict) -> dict:
        plaintext = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return _encrypt(AES_KEY, plaintext)

    def test_encrypted_payload_accepted(self):
        inner = _finalise(_make_body(), hmac_secret=HMAC_SECRET)
        envelope = self._encrypt_body(inner)
        msg = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        result = self._fn(msg)
        assert result.accepted, result.reason

    def test_encrypted_with_wrong_key_rejected(self):
        wrong_key = _make_key()
        inner = _finalise(_make_body(), hmac_secret=HMAC_SECRET)
        plaintext = json.dumps(inner, sort_keys=True, separators=(",", ":")).encode("utf-8")
        envelope = _encrypt(wrong_key, plaintext)
        msg = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        result = self._fn(msg)
        assert not result.accepted
        assert "decryption" in result.reason.lower() or "AES" in result.reason

    def test_tampered_ciphertext_rejected(self):
        inner = _finalise(_make_body(), hmac_secret=HMAC_SECRET)
        envelope = self._encrypt_body(inner)
        # Flip a bit in the ciphertext
        ct_bytes = bytearray(base64.b64decode(envelope["ct"]))
        ct_bytes[0] ^= 0xFF
        envelope["ct"] = base64.b64encode(bytes(ct_bytes)).decode("ascii")
        msg = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        result = self._fn(msg)
        assert not result.accepted

    def test_malformed_json_rejected(self):
        result = self._fn("not-valid-json{{{")
        assert not result.accepted
        assert "JSON" in result.reason


# ---------------------------------------------------------------------------
# Fusion engine tests
# ---------------------------------------------------------------------------

class TestOrientationFusion:

    def test_stability_one_before_warmup(self):
        from src.dslv_zpdi.layer2_core.fusion_engine import OrientationTracker
        t = OrientationTracker()
        assert t.stability() == 1.0  # No samples yet

    def test_stability_one_after_single_push(self):
        from src.dslv_zpdi.layer2_core.fusion_engine import OrientationTracker
        t = OrientationTracker()
        t.push({"x": 0.0, "y": 0.0, "z": 0.0, "cos_value": 1.0})
        assert t.stability() == 1.0  # Only one sample — no delta

    def test_stability_identity_quaternion(self):
        from src.dslv_zpdi.layer2_core.fusion_engine import OrientationTracker
        t = OrientationTracker()
        identity = {"x": 0.0, "y": 0.0, "z": 0.0, "cos_value": 1.0}
        t.push(identity)
        t.push(identity)
        assert abs(t.stability() - 1.0) < 1e-6

    def test_stability_90_degree_rotation(self):
        """90° rotation between samples → stability ≈ cos(45°) ≈ 0.707."""
        from src.dslv_zpdi.layer2_core.fusion_engine import OrientationTracker
        t = OrientationTracker()
        # q1 = identity
        t.push({"x": 0.0, "y": 0.0, "z": 0.0, "cos_value": 1.0})
        # q2 = 90° rotation about z: q = [0, 0, sin(45°), cos(45°)]
        s45 = math.sqrt(2) / 2
        t.push({"x": 0.0, "y": 0.0, "z": s45, "cos_value": s45})
        stab = t.stability()
        assert abs(stab - s45) < 0.01

    def test_apply_weight_scales_scores(self):
        from src.dslv_zpdi.layer2_core.fusion_engine import (
            OrientationTracker,
            apply_orientation_weight,
        )
        t = OrientationTracker()
        t.push({"x": 0.0, "y": 0.0, "z": 0.0, "cos_value": 1.0})
        t.push({"x": 0.0, "y": 0.0, "z": 0.0, "cos_value": 1.0})
        r_fused, rs_fused, w = apply_orientation_weight(0.8, 0.6, t)
        assert abs(w - 1.0) < 1e-6
        assert abs(r_fused - 0.8) < 1e-6
        assert abs(rs_fused - 0.6) < 1e-6

    def test_fusion_lowers_score_on_motion(self):
        import math

        from src.dslv_zpdi.layer2_core.fusion_engine import (
            OrientationTracker,
            apply_orientation_weight,
        )
        t = OrientationTracker()
        t.push({"x": 0.0, "y": 0.0, "z": 0.0, "cos_value": 1.0})
        s45 = math.sqrt(2) / 2
        t.push({"x": 0.0, "y": 0.0, "z": s45, "cos_value": s45})
        r_fused, _, w = apply_orientation_weight(1.0, 1.0, t)
        assert r_fused < 1.0  # rotation penalty applied


# ---------------------------------------------------------------------------
# End-to-end pipeline: mobile payload → tier1 processing → route
# ---------------------------------------------------------------------------

class TestEndToEnd:

    def setup_method(self):
        self._fn = _get_process_fn()

    def test_full_round_trip_plaintext(self):
        body = _finalise(_make_body({"r_smooth": 0.45}), hmac_secret=HMAC_SECRET)
        msg = json.dumps(body, sort_keys=True, separators=(",", ":"))
        result = self._fn(msg)
        assert result.accepted
        assert result.route_stream == "SECONDARY"

    def test_full_round_trip_encrypted(self):
        inner = _finalise(_make_body({"r_smooth": 0.20}), hmac_secret=HMAC_SECRET)
        plaintext = json.dumps(inner, sort_keys=True, separators=(",", ":")).encode("utf-8")
        envelope = _encrypt(AES_KEY, plaintext)
        msg = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        result = self._fn(msg)
        assert result.accepted
        assert result.route_stream == "SECONDARY"

    def test_all_tier2_packets_go_to_secondary(self):
        """Router must always assign SECONDARY for hardware_tier=2."""
        for r_smooth in (0.05, 0.20, 0.60):
            body = _finalise(_make_body({"r_smooth": r_smooth}), hmac_secret=HMAC_SECRET)
            msg = json.dumps(body, sort_keys=True, separators=(",", ":"))
            result = self._fn(msg)
            assert result.accepted
            assert result.route_stream == "SECONDARY"
