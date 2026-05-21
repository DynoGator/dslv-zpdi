#!/usr/bin/env python3
"""Mobile node compliance test suite — SPEC-005/006/007 validation."""

from __future__ import annotations

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

from src.layer1_ingestion.mobile_ingestion import (
    IngestionPayload,
    build_mobile_payload,
    score_mobile_payload,
    SENSORS,
    TERMUX_SENSOR_BIN,
)
from src.layer1_ingestion.payload import SensorModality
from src.layer2_core.coherence import CoherenceScorer, CoherencePacket
from src.layer2_core.wiring import wire_mobile_to_coherence
from src.layer3_telemetry.mobile_router import route_packet, SecondaryLog


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
    from src.layer2_core.wiring import wire_to_coherence
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
    assert abs(scorer.compute_global_R() - 0.8) < 0.001


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
    """Live integration: 10-second mobile run → zero HDF5 rows, non-zero JSONL."""
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
    with h5py.File(hdf5_path, "r") as f:
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
