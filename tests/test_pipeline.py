#!/usr/bin/env python3
import json
import math
import uuid
import time

from dslv_zpdi.core.states import TrustState, RouteStream
from dslv_zpdi.layer1_ingestion.payload import IngestionPayload, SensorModality
from dslv_zpdi.layer2_core.coherence import CoherenceScorer
from dslv_zpdi.layer2_core.wiring import wire_to_coherence
from dslv_zpdi.layer3_telemetry.router import DualStreamRouter


def test_quarantine_vs_kill():
    # GPS-untrusted → SECONDARY_QUARANTINED
    p = IngestionPayload(
        node_id="T",
        sensor_id="S",
        modality="rf_sdr",
        payload_uuid=str(uuid.uuid4()),
        timestamp_utc=time.time(),
        gps_locked=False,
    )
    state, _ = p.validate()
    assert state == TrustState.SECONDARY_QUARANTINED.value

    # Missing identity → KILLED
    p2 = IngestionPayload(
        node_id="",
        sensor_id="",
        modality="",
        payload_uuid=str(uuid.uuid4()),
        timestamp_utc=time.time(),
    )
    state2, _ = p2.validate()
    assert state2 == TrustState.KILLED.value
    print("  TEST 1 PASS: Quarantine vs Kill ✅")


def test_serialization_roundtrip():
    p = IngestionPayload(
        node_id="C",
        sensor_id="S",
        modality=SensorModality.RF_SDR.value,
        payload_uuid=str(uuid.uuid4()),
        timestamp_utc=time.time(),
        gps_locked=True,
        extracted_phases=[0.1],
    )
    d = json.loads(p.to_json())
    assert SensorModality(d["modality"]) == SensorModality.RF_SDR
    print("  TEST 2 PASS: Serialization ✅")


def test_state_machine():
    p = IngestionPayload(
        node_id="C",
        sensor_id="S",
        modality=SensorModality.RF_SDR.value,
        payload_uuid=str(uuid.uuid4()),
        timestamp_utc=time.time(),
        gps_locked=False,
    )
    assert wire_to_coherence(p.to_json()) is None
    print("  TEST 3 PASS: State Machine ✅")


def test_full_pipeline():
    p = IngestionPayload(
        node_id="C",
        sensor_id="S",
        modality=SensorModality.RF_SDR.value,
        payload_uuid=str(uuid.uuid4()),
        timestamp_utc=time.time(),
        gps_locked=True,
        extracted_phases=[0.1] * 50,
    )
    d = json.loads(p.to_json())
    d["trust_state"] = TrustState.CAL_TRUSTED.value
    assert DualStreamRouter().route(json.dumps(d)).packet is not None
    print("  TEST 4 PASS: Full Pipeline ✅")


def test_coherence_math():
    scorer = CoherenceScorer()
    assert abs(scorer.compute_local_r([0.0, 0.0]) - 1.0) < 0.001
    print("  TEST 5 PASS: Coherence Math ✅")


def test_global_R():
    scorer = CoherenceScorer()
    scorer.fleet_state["RF"] = {
        "r_smooth": 0.8,
        "mean_phase": 0.1,
        "modality": "rf_sdr",
        "ts": time.time(),
    }
    # Weighted global R(t) per Section 5.5.2 — single node yields r_smooth * w / w
    assert abs(scorer.compute_global_r() - 0.8) < 0.001
    print("  TEST 6 PASS: Global R(t) ✅")


def test_killed_packet():
    p = IngestionPayload(
        node_id="", sensor_id="", modality="", payload_uuid="u", timestamp_utc=0.0
    )
    state, reason = p.validate()
    assert state == TrustState.KILLED.value
    print("  TEST 7 PASS: KILLED Packet ✅")


def test_attestation():
    import hmac, hashlib
    from dslv_zpdi.layer3_telemetry.hdf5_writer import HDF5Writer

    w = HDF5Writer(hardware_enclave_key=b"key")
    tp = json.dumps({"t": "d"}).encode()
    assert (
        hmac.new(b"key", tp, hashlib.sha256).hexdigest()
        == hmac.new(w.key, tp, hashlib.sha256).hexdigest()
    )
    print("  TEST 8 PASS: Cryptography ✅")


def test_rotation():
    from dslv_zpdi.layer3_telemetry.hdf5_writer import HDF5Writer

    assert HDF5Writer()._file_size_exceeded() is True

    print("  TEST 9 PASS: File Rotation ✅")


def test_baseline():
    scorer = CoherenceScorer()
    scorer.baseline_learning_mode = True
    scorer.baseline_samples = [0.1, 0.12, 0.11, 0.13, 0.1, 0.11]
    scorer.finalize_baseline(force=True)
    assert not scorer.baseline_learning_mode
    assert 0.24 < scorer.dynamic_threshold < 0.26
    print("  TEST 10 PASS: Adaptive Baseline ✅")


def main():
    print("=" * 40 + "\nDSLV-ZPDI Rev 4.0.2.4 Tests\n" + "=" * 40)
    for t in [
        test_quarantine_vs_kill,
        test_serialization_roundtrip,
        test_state_machine,
        test_full_pipeline,
        test_coherence_math,
        test_global_R,
        test_killed_packet,
        test_attestation,
        test_rotation,
        test_baseline,
    ]:
        t()
    print("ALL 10 TESTS PASSED ✅")


if __name__ == "__main__":
    main()
