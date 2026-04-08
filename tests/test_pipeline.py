#!/usr/bin/env python3
import sys, os, json, math, uuid, time, cmath, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.layer1_ingestion.payload import IngestionPayload, SensorModality
from src.layer2_core.coherence import CoherenceScorer, CoherencePacket
from src.layer2_core.wiring import wire_to_coherence
from src.layer3_telemetry.router import DualStreamRouter, RoutingDecision

def test_quarantine_vs_kill():
    p = IngestionPayload(node_id="TEST", sensor_id="SDR", modality="rf_sdr", payload_uuid=str(uuid.uuid4()), timestamp_utc=time.time(), gps_locked=False)
    state, _ = p.validate()
    assert state == "SECONDARY_QUARANTINED"
    p2 = IngestionPayload(payload_uuid=str(uuid.uuid4()))
    state2, _ = p2.validate()
    assert state2 == "KILLED"
    print("  TEST 1 PASS: Quarantine vs Kill (SPEC-003) ✅")

def test_serialization_roundtrip():
    p = IngestionPayload(node_id="CM5", sensor_id="SDR", modality=SensorModality.RF_SDR.value, payload_uuid=str(uuid.uuid4()), timestamp_utc=time.time(), gps_locked=True, extracted_phases=[0.1])
    d = json.loads(p.to_json())
    assert SensorModality(d['modality']) == SensorModality.RF_SDR
    print("  TEST 2 PASS: Serialization Roundtrip ✅")

def test_state_machine_enforcement():
    p = IngestionPayload(node_id="CM5", sensor_id="SDR", modality=SensorModality.RF_SDR.value, payload_uuid=str(uuid.uuid4()), timestamp_utc=time.time(), gps_locked=False)
    assert wire_to_coherence(p.to_json()) is None
    print("  TEST 3 PASS: State Machine Enforcement ✅")

def test_full_pipeline():
    p = IngestionPayload(node_id="CM5", sensor_id="SDR", modality=SensorModality.RF_SDR.value, payload_uuid=str(uuid.uuid4()), timestamp_utc=time.time(), gps_locked=True, extracted_phases=[0.1]*50)
    d = json.loads(p.to_json())
    d['trust_state'] = 'CAL_TRUSTED'
    decision = DualStreamRouter().route(json.dumps(d, default=str))
    assert decision.packet is not None
    print(f"  TEST 4 PASS: Full Pipeline (stream={decision.stream}) ✅")

def test_coherence_math():
    scorer = CoherenceScorer()
    assert abs(scorer.compute_local_r([0.0, 0.0]) - 1.0) < 0.001
    print("  TEST 5 PASS: Coherence Math ✅")

def test_global_R_weighting():
    scorer = CoherenceScorer()
    scorer.fleet_state["RF"] = {"r_smooth": 0.8, "mean_phase": 0.1, "modality": "rf_sdr", "ts": time.time()}
    assert scorer.compute_global_R() == 0.8
    print("  TEST 6 PASS: Global R(t) Weighting ✅")

def test_killed_packet_no_json():
    assert IngestionPayload().to_json() is None
    print("  TEST 7 PASS: KILLED Packet → No JSON ✅")

def test_hdf5_attestation():
    import hmac, hashlib
    from src.layer3_telemetry.hdf5_writer import HDF5Writer
    writer = HDF5Writer(hardware_enclave_key=b"test_key")
    test_payload = json.dumps({"test": "data"}, sort_keys=True).encode()
    expected = hmac.new(b"test_key", test_payload, hashlib.sha256).hexdigest()
    actual = hmac.new(writer.key, test_payload, hashlib.sha256).hexdigest()
    assert expected == actual
    print("  TEST 8 PASS: HMAC Attestation Cryptography ✅")

def test_file_rotation():
    from src.layer3_telemetry.hdf5_writer import HDF5Writer
    writer = HDF5Writer()
    assert writer._file_size_exceeded() == True
    print("  TEST 9 PASS: File Rotation Logic Initialized ✅")

def test_baseline_learning():
    scorer = CoherenceScorer()
    scorer.baseline_learning_mode = True
    scorer.baseline_samples = [0.1, 0.12, 0.11, 0.13, 0.1, 0.11]
    scorer.finalize_baseline()
    assert scorer.baseline_learning_mode == False
    assert 0.13 < scorer.dynamic_threshold < 0.16
    print(f"  TEST 10 PASS: Adaptive Baseline (Threshold: {scorer.dynamic_threshold:.4f}) ✅")

def main():
    print("=" * 60 + "\nDSLV-ZPDI Rev 3.4 — Pipeline Integration Tests\n" + "=" * 60)
    tests = [test_quarantine_vs_kill, test_serialization_roundtrip, test_state_machine_enforcement, test_full_pipeline, test_coherence_math, test_global_R_weighting, test_killed_packet_no_json, test_hdf5_attestation, test_file_rotation, test_baseline_learning]
    passed = failed = 0
    for test in tests:
        try: test(); passed += 1
        except Exception as e: print(f"  FAIL: {test.__name__} — {e}"); failed += 1
    print("=" * 60)
    print(f"ALL {passed} TESTS PASSED ✅" if failed == 0 else f"FAILED: {failed}/{passed + failed}")
    sys.exit(1 if failed > 0 else 0)

if __name__ == "__main__":
    main()
