import time
import uuid
import json
from dslv_zpdi.layer1_ingestion.payload import IngestionPayload, SensorModality
from dslv_zpdi.layer3_telemetry.router import DualStreamRouter


def run_gps_fault_injection():
    print("--- INITIATING FAULT INJECTION: GPS LOCK LOSS ---")
    router = DualStreamRouter()

    print("[*] Generating payload with gps_locked=False and pps_jitter_ns=50000.0...")
    faulty_payload = IngestionPayload(
        payload_uuid=str(uuid.uuid4()),
        node_id="PI5-ALPHA-TEST",
        sensor_id="GPSDO-01",
        modality=SensorModality.RF_SDR.value,
        timestamp_utc=time.time(),
        gps_locked=False,
        pps_jitter_ns=50000.0,
        calibration_valid=True,
        extracted_phases=[0.1, 0.2, 0.3, 0.4] * 10,
    )

    json_payload = faulty_payload.to_json()
    if not json_payload:
        print("[!] ERROR: Payload failed structural serialization (KILLED).")
        return False

    packet_dict = json.loads(json_payload)
    print(f"[*] Layer 1 Trust State emitted as: {packet_dict.get('trust_state')}")

    decision = router.route(json_payload)

    print(f"Target Stream: {decision.stream}")
    print(f"Final Trust State: {decision.trust_state}")

    if (
        decision.stream == "SECONDARY"
        and decision.trust_state == "SECONDARY_QUARANTINED"
    ):
        print("\n[SUCCESS] SPEC-003 Enforced. Untrusted data correctly quarantined.")
        return True
    else:
        print("\n[FAILURE] Routing logic breached.")
        return False


if __name__ == "__main__":
    success = run_gps_fault_injection()
    exit(0 if success else 1)
