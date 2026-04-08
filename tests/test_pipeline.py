import sys, os, json, math, uuid, time, cmath, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.layer1_ingestion.payload import IngestionPayload, SensorModality
from src.layer2_core.coherence import CoherenceScorer, CoherencePacket
from src.layer2_core.wiring import wire_to_coherence
from src.layer3_telemetry.router import DualStreamRouter

def test_quarantine_vs_kill():
    p = IngestionPayload(node_id="TEST-01", sensor_id="SDR-01", modality="rf_sdr", payload_uuid=str(uuid.uuid4()), timestamp_utc=time.time(), gps_locked=False)
    state, reason = p.validate()
    assert state == "SECONDARY_QUARANTINED"
    
    p2 = IngestionPayload(node_id="TEST-01", sensor_id="SDR-01", modality="rf_sdr", payload_uuid=str(uuid.uuid4()), timestamp_utc=time.time(), gps_locked=True, pps_jitter_ns=15_000.0)
    state2, _ = p2.validate()
    assert state2 == "SECONDARY_QUARANTINED"
    
    p3 = IngestionPayload(payload_uuid=str(uuid.uuid4()))
    state3, _ = p3.validate()
    assert state3 == "KILLED"
    
    p4 = IngestionPayload(node_id="TEST-01", sensor_id="SDR-01", modality="rf_sdr", payload_uuid=str(uuid.uuid4()), timestamp_utc=time.time(), gps_locked=True, pps_jitter_ns=500.0)
    state4, reason4 = p4.validate()
    assert state4 == "ASSEMBLED"
    print("  TEST 1 PASS: Quarantine vs Kill (SPEC-003) ✅")

def test_serialization_roundtrip():
    p = IngestionPayload(node_id="CM5-ALPHA", sensor_id="RTLSDR-01", modality=SensorModality.RF_SDR.value, payload_uuid=str(uuid.uuid4()), timestamp_utc=time.time(), gps_locked=True, pps_jitter_ns=200.0, extracted_phases=[0.1, 0.2, 0.3])
    json_str = p.to_json()
    assert json_str is not None
    d = json.loads(json_str)
    assert d['modality'] == 'rf_sdr'
    assert d['extracted_phases'] == [0.1, 0.2, 0.3]
    rehydrated = SensorModality(d['modality'])
    assert rehydrated == SensorModality.RF_SDR
    print("  TEST 2 PASS: Serialization Roundtrip ✅")

def test_state_machine_enforcement():
    p = IngestionPayload(node_id="CM5-ALPHA", sensor_id="RTLSDR-01", modality=SensorModality.RF_SDR.value, payload_uuid=str(uuid.uuid4()), timestamp_utc=time.time(), gps_locked=False, extracted_phases=[0.1, 0.2])
    json_str = p.to_json()
    assert wire_to_coherence(json_str) is None
    d = json.loads(json_str)
    d['trust_state'] = 'ASSEMBLED'
    assert wire_to_coherence(json.dumps(d)) is None
    print("  TEST 3 PASS: State Machine Enforcement ✅")

def test_full_pipeline():
    phases = [0.1 + 0.01 * i for i in range(50)]
    p = IngestionPayload(node_id="CM5-ALPHA", sensor_id="RTLSDR-01", modality=SensorModality.RF_SDR.value, payload_uuid=str(uuid.uuid4()), timestamp_utc=time.time(), gps_locked=True, pps_jitter_ns=200.0, calibration_valid=True, extracted_phases=phases)
    d = json.loads(p.to_json())
    d['trust_state'] = 'CAL_TRUSTED'
    decision = DualStreamRouter().route(json.dumps(d, default=str))
    assert decision.packet is not None
    assert decision.stream in ["PRIMARY", "SECONDARY", "PRIMARY_CANDIDATE"]
    print(f"  TEST 4 PASS: Full Pipeline (stream={decision.stream}) ✅")

def test_coherence_math():
    scorer = CoherenceScorer()
    assert abs(scorer.compute_local_r([0.0, 0.0, 0.0, 0.0]) - 1.0) < 0.001
    random.seed(42)
    assert scorer.compute_local_r([random.uniform(0, 2 * math.pi) for _ in range(1000)]) < 0.15
    assert scorer.compute_local_r([]) == 0.0
    print("  TEST 5 PASS: Coherence Math ✅")

def test_global_R_weighting():
    scorer = CoherenceScorer()
    for i in range(2): scorer.fleet_state[f"RF-{i}"] = {"r_smooth": 0.8, "mean_phase": 0.1, "modality": "rf_sdr", "ts": time.time()}
    for i in range(2): scorer.fleet_state[f"THERM-{i}"] = {"r_smooth": 0.2, "mean_phase": 0.1, "modality": "thermal", "ts": time.time()}
    R = scorer.compute_global_R()
    assert 0.5 < R < 0.8
    print(f"  TEST 6 PASS: Global R(t) Weighting (R={R:.4f}) ✅")

def test_killed_packet_no_json():
    assert IngestionPayload().to_json() is None
    print("  TEST 7 PASS: KILLED Packet → No JSON ✅")

def main():
    print("=" * 60 + "\nDSLV-ZPDI Rev 3.1 — Pipeline Integration Tests\n" + "=" * 60)
    tests = [test_quarantine_vs_kill, test_serialization_roundtrip, test_state_machine_enforcement, test_full_pipeline, test_coherence_math, test_global_R_weighting, test_killed_packet_no_json]
    passed = failed = 0
    for test in tests:
        try: test(); passed += 1
        except Exception as e: print(f"  FAIL: {test.__name__} — {e}"); failed += 1
    print("=" * 60)
    print(f"ALL {passed} TESTS PASSED ✅" if failed == 0 else f"FAILED: {failed}/{passed + failed}")
    sys.exit(1 if failed > 0 else 0)

if __name__ == "__main__":
    main()
