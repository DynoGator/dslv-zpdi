#!/usr/bin/env python3
"""Mobile node compliance test suite — SPEC-005/006/007 validation."""

from __future__ import annotations
from src.dslv_zpdi.layer3_telemetry.mobile_router import route_packet
from src.dslv_zpdi.layer2_core.wiring import wire_mobile_to_coherence
from src.dslv_zpdi.layer2_core.coherence import CoherenceScorer
from src.dslv_zpdi.layer1_ingestion.payload import SensorModality
from src.dslv_zpdi.layer1_ingestion.mobile_ingestion import (
    SENSORS,
    IngestionPayload,
    build_mobile_payload,
    score_mobile_payload,
)

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

# Ensure src/ is on the path when running from tests/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Core payload tests (ported from Rev 3.4 regression suite)
# ---------------------------------------------------------------------------


def test_quarantine_vs_kill():
    """SPEC-003: GPS-untrusted → SECONDARY_QUARANTINED; missing identity → KILLED."""
    p = IngestionPayload(
        node_id="TEST",
        sensor_id="SDR",
        modality="rf_sdr",
        payload_uuid=str(uuid.uuid4()),
        timestamp_utc=time.time(),
        gps_locked=False,
    )
    state, _ = p.validate()
    assert state == "SECONDARY_QUARANTINED"

    p2 = IngestionPayload(payload_uuid=str(uuid.uuid4()))
    state2, _ = p2.validate()
    assert state2 == "KILLED"


def test_serialization_roundtrip():
    """SPEC-005A.3: JSON serialization preserves modality and checksum."""
    p = IngestionPayload(
        node_id="MOBILE",
        sensor_id="ACCEL",
        modality=SensorModality.ACCEL.value,
        payload_uuid=str(uuid.uuid4()),
        timestamp_utc=time.time(),
        gps_locked=True,  # Force ASSEMBLED to allow serialization
        extracted_phases=[0.1],
    )
    raw = p.to_json()
    assert raw is not None
    d = json.loads(raw)
    assert d["modality"] == SensorModality.ACCEL.value
    assert d["payload_checksum"] != ""
    assert len(d["payload_checksum"]) == 16


def test_state_machine_enforcement():
    """SPEC-006.5: SECONDARY_QUARANTINED packets bypassed by mobile wiring."""
    p = IngestionPayload(
        node_id="MOBILE",
        sensor_id="ACCEL",
        modality=SensorModality.ACCEL.value,
        payload_uuid=str(uuid.uuid4()),
        timestamp_utc=time.time(),
        gps_locked=False,
        extracted_phases=[0.1] * 50,
    )
    json_payload = p.to_json()
    # wire_to_coherence (canonical) blocks SECONDARY_QUARANTINED
    from src.dslv_zpdi.layer2_core.wiring import wire_to_coherence
    assert wire_to_coherence(json_payload) is None
    # mobile wiring allows it
    assert wire_mobile_to_coherence(json.loads(json_payload)) is not None


def test_full_pipeline():
    """End-to-end: payload → coherence → router → secondary stream."""
    p = IngestionPayload(
        node_id="MOBILE",
        sensor_id="ACCEL",
        modality=SensorModality.ACCEL.value,
        payload_uuid=str(uuid.uuid4()),
        timestamp_utc=time.time(),
        gps_locked=False,
        extracted_phases=[0.1] * 50,
    )
    d = json.loads(p.to_json())
    d["trust_state"] = "SECONDARY_QUARANTINED"
    coherence = wire_mobile_to_coherence(d)
    assert coherence is not None
    decision = route_packet({**d, "r_smooth": coherence.r_smooth})
    assert decision["stream"] == "SECONDARY"
    assert decision["trust_state"] == "SECONDARY_QUARANTINED"


def test_coherence_math():
    """SPEC-006.2: Perfect phase lock → r_local ≈ 1.0."""
    scorer = CoherenceScorer()
    assert abs(scorer.compute_local_r([0.0, 0.0]) - 1.0) < 0.001


def test_global_r_weighting():
    """SPEC-006.2b: Single-node fleet → r_global equals that node's r_smooth."""
    scorer = CoherenceScorer()
    scorer.fleet_state["RF"] = {
        "r_smooth": 0.8,
        "mean_phase": 0.1,
        "modality": "rf_sdr",
        "ts": time.time(),
    }
    assert abs(scorer.compute_global_r() - 0.8) < 0.001


def test_killed_packet_no_json():
    """SPEC-005A.3: KILLED packets must not serialize."""
    assert IngestionPayload().to_json() is None


# ---------------------------------------------------------------------------
# Mobile-specific tests (mandated by execution directive)
# ---------------------------------------------------------------------------

def test_mobile_payload_has_hardware_tier_2():
    """All mobile payloads must self-declare as Tier-2."""
    p = build_mobile_payload("ICM45631 Accelerometer", {"x": 1, "y": 0, "z": 0})
    assert p.hardware_tier == 2


def test_mobile_node_produces_only_secondary_stream():
    """Router must never assign PRIMARY to a Tier-2 packet."""
    for r_smooth in (0.05, 0.25, 0.55):
        d = {
            "hardware_tier": 2,
            "trust_state": "SECONDARY_QUARANTINED",
            "r_smooth": r_smooth,
        }
        decision = route_packet(d)
        assert decision["stream"] == "SECONDARY"
        assert decision["trust_state"] == "SECONDARY_QUARANTINED"


def test_primary_hdf5_is_empty_after_mobile_run():
    """Live integration: 10-second mobile run → zero HDF5 rows, non-zero JSONL.

    Skipped automatically if a production daemon is already running,
    because termux-sensor allows only one streaming instance at a time.
    """
    if not Path("/data/data/com.termux/files/usr/bin/termux-sensor").exists():
        pytest.skip("termux-sensor not found, skipping mobile live integration test")
    # Detect running production daemon
    try:
        result = subprocess.run(
            ["pgrep", "-f", "zpdi_mobile_node.py"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            pytest.skip("Production daemon already running — termux-sensor singleton prevents parallel streaming")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    hdf5_path = Path("./data/zpdi_test_primary.h5")
    jsonl_path = Path("./logs/zpdi_test_secondary.jsonl")
    hdf5_path.unlink(missing_ok=True)
    jsonl_path.unlink(missing_ok=True)

    env = {
        **os.environ,
        "ZPDI_HDF5_PATH": str(hdf5_path),
        "ZPDI_FALLBACK_LOG": str(jsonl_path),
    }
    proc = subprocess.Popen(
        [sys.executable, "zpdi_mobile_node.py"],
        cwd=str(Path(__file__).parent.parent),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(12)
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    import h5py
    with h5py.File(hdf5_path, "r", swmr=True) as f:
        dset = f["payloads"]
        assert dset.shape[0] == 0, "Primary HDF5 must be empty for Tier-2"

    assert jsonl_path.exists(), "Secondary JSONL must exist"
    lines = jsonl_path.read_text().strip().split("\n")
    assert len(lines) > 0, "Secondary JSONL must have rows"
    for line in lines:
        obj = json.loads(line)
        assert obj["trust_state"] == "SECONDARY_QUARANTINED"
        assert obj["hardware_tier"] == 2

    hdf5_path.unlink(missing_ok=True)
    jsonl_path.unlink(missing_ok=True)


def test_all_mobile_packets_have_infinite_pps_jitter():
    """Mobile has no PPS hardware — pps_jitter_ns must be infinite."""
    p = build_mobile_payload("ICM45631 Accelerometer", {"x": 1, "y": 0, "z": 0})
    assert p.pps_jitter_ns == float("inf")


def test_quarantine_reason_present_on_all_packets():
    """Every secondary packet must carry an explicit quarantine reason."""
    p = build_mobile_payload("ICM45631 Accelerometer", {"x": 1, "y": 0, "z": 0})
    json_str = p.to_json()
    assert json_str is not None
    d = json.loads(json_str)
    assert d["quarantine_reason"] is not None
    assert d["quarantine_reason"] != ""


# ---------------------------------------------------------------------------
# Layer 2 wiring / coherence mobile tests
# ---------------------------------------------------------------------------

def test_mobile_phase_extraction_in_layer1():
    """SPEC-005: Phase extraction must happen in Layer 1, not Layer 2."""
    # Feed a short sequence to fill the phase buffer
    for i in range(8):
        reading = {"x": float(i), "y": 0.0, "z": 9.8}
        p = build_mobile_payload("ICM45631 Accelerometer", reading)
    assert len(p.extracted_phases) > 0
    # Layer 2 must accept pre-extracted phases without performing Hilbert
    d = json.loads(p.to_json())
    packet = wire_mobile_to_coherence(d)
    assert packet is not None


def test_mobile_coherence_scoring():
    """Coherence scores must be present on scored mobile payloads."""
    for i in range(8):
        reading = {"x": float(i), "y": 0.0, "z": 9.8}
        p = build_mobile_payload("ICM45631 Accelerometer", reading)
    scores = score_mobile_payload(p)
    assert scores is not None
    assert hasattr(scores, "r_local")
    assert hasattr(scores, "r_smooth")
    assert hasattr(scores, "r_global")


# ---------------------------------------------------------------------------
# Hardening regression tests (Rev 3.5)
# ---------------------------------------------------------------------------

def test_hmac_signing_when_secret_set():
    """SPEC-008: HMAC-SHA256 must be present when ZPDI_HMAC_SECRET is set."""
    import os
    old_secret = os.environ.get("ZPDI_HMAC_SECRET")
    os.environ["ZPDI_HMAC_SECRET"] = "test-secret-key"
    try:
        # Re-import to pick up the new secret
        import importlib

        import zpdi_mobile_node
        importlib.reload(zpdi_mobile_node)
        raw = b'{"test":1}'
        sig = zpdi_mobile_node._sign_payload(raw, b"test-secret-key")
        assert sig != ""
        assert len(sig) == 64  # hex SHA-256
    finally:
        if old_secret is None:
            os.environ.pop("ZPDI_HMAC_SECRET", None)
        else:
            os.environ["ZPDI_HMAC_SECRET"] = old_secret


def test_gps_enrichment_in_payload():
    """GPS poller metadata must appear in the serialized payload."""
    from src.dslv_zpdi.layer1_ingestion.mobile_ingestion import build_mobile_payload
    loc = {
        "latitude": 33.4484,
        "longitude": -112.0740,
        "altitude": 331.0,
        "accuracy": 12.5,
        "provider": "gps",
        "ts": time.time(),
    }
    p = build_mobile_payload("ICM45631 Accelerometer", {"x": 1, "y": 0, "z": 0}, loc)
    json_str = p.to_json()
    assert json_str is not None
    d = json.loads(json_str)
    assert d["latitude"] == 33.4484
    assert d["longitude"] == -112.0740
    assert d["altitude"] == 331.0
    assert d["accuracy"] == 12.5
    assert d["location_provider"] == "gps"


def test_aes_encryption_envelope():
    """SPEC-008: AES-256-GCM envelope must contain nonce, ct, and enc label."""
    import base64

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = AESGCM.generate_key(bit_length=256)
    aesgcm = AESGCM(key)
    plaintext = b'{"sensor":"magnetometer"}'
    import zpdi_mobile_node
    env = zpdi_mobile_node._encrypt_payload(aesgcm, plaintext)
    assert env["enc"] == "aes-256-gcm"
    assert "nonce" in env
    assert "ct" in env
    # Verify round-trip
    nonce = base64.b64decode(env["nonce"])
    ct = base64.b64decode(env["ct"])
    decrypted = aesgcm.decrypt(nonce, ct, None)
    assert decrypted == plaintext


def test_expanded_sensor_modalities():
    """Rev 3.5 expanded sensor list must map to canonical modalities."""
    from src.dslv_zpdi.layer1_ingestion.mobile_ingestion import SENSOR_MODALITY_MAP
    for s in SENSORS:
        assert s in SENSOR_MODALITY_MAP, f"{s} missing from modality map"
        assert SENSOR_MODALITY_MAP[s] != "unknown"


def test_gyroscope_phase_extraction():
    """Gyroscope magnitude must produce non-empty phases after window fill."""
    from src.dslv_zpdi.layer1_ingestion.mobile_ingestion import build_mobile_payload
    for i in range(8):
        reading = {"x": float(i), "y": 0.0, "z": 0.5}
        p = build_mobile_payload("ICM45631 Gyroscope", reading)
    assert len(p.extracted_phases) > 0


# ---------------------------------------------------------------------------
# Fusion engine integration tests (SPEC-006.6)
# ---------------------------------------------------------------------------

def test_rotation_vector_updates_orientation_tracker():
    """Rotation-vector readings must feed the module-level OrientationTracker."""
    from src.dslv_zpdi.layer1_ingestion import mobile_ingestion as mi
    mi._ORIENTATION.reset()
    # Feed two rotation-vector readings
    mi._build_extracted_phases("Rotation Vector Sensor", {"x": 0.0, "y": 0.0, "z": 0.0, "cos_value": 1.0})
    mi._build_extracted_phases("Rotation Vector Sensor", {"x": 0.0, "y": 0.0, "z": 0.0, "cos_value": 1.0})
    # Stability must be computed (two samples in buffer)
    assert mi._ORIENTATION.stability() <= 1.0


def test_fusion_weight_applied_to_scores():
    """apply_orientation_weight must scale r_local and r_smooth by stability."""
    import math

    from src.dslv_zpdi.layer2_core.fusion_engine import OrientationTracker, apply_orientation_weight
    s45 = math.sqrt(2) / 2
    t = OrientationTracker()
    # identity → 90° rotation: dot = cos(45°) = s45
    t.push({"x": 0.0, "y": 0.0, "z": 0.0, "cos_value": 1.0})
    t.push({"x": 0.0, "y": 0.0, "z": s45, "cos_value": s45})
    r_in, rs_in = 0.8, 0.5
    r_out, rs_out, w = apply_orientation_weight(r_in, rs_in, t)
    assert abs(w - s45) < 0.01, f"stability={w} expected≈{s45}"
    assert abs(r_out - r_in * w) < 1e-9
    assert abs(rs_out - rs_in * w) < 1e-9
    assert r_out < r_in  # rotation penalty reduces the score


def test_new_sensor_modalities_in_enum():
    """All 7 Pixel 9 Pro XL sensor modalities must be in SensorModality enum."""
    from src.dslv_zpdi.layer1_ingestion.payload import SensorModality
    required = {"gyroscope", "rotation_vector", "geomagnetic_rotation", "gravity"}
    enum_values = {m.value for m in SensorModality}
    for mod in required:
        assert mod in enum_values, f"SensorModality missing: {mod}"


def test_wiring_accepts_all_mobile_modalities():
    """wire_mobile_to_coherence must not silently kill gyro/rotation/gravity."""
    from src.dslv_zpdi.layer2_core.wiring import wire_mobile_to_coherence
    mobile_modalities = ("gyroscope", "rotation_vector", "geomagnetic_rotation", "gravity")
    for mod in mobile_modalities:
        payload_dict = {
            "node_id": "test",
            "modality": mod,
            "trust_state": "SECONDARY_QUARANTINED",
            "extracted_phases": [0.1, 0.2, 0.3],
            "payload_uuid": "test-uuid",
            "timestamp_utc": 0.0,
        }
        result = wire_mobile_to_coherence(payload_dict)
        assert result is not None, f"wire_mobile_to_coherence returned None for modality={mod}"
