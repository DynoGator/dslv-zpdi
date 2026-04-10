"""Unit tests for IngestionPayload contract."""

import json
import hashlib
from layer1_ingestion.payload import IngestionPayload


def test_payload_validation():
    # Valid payload
    p = IngestionPayload(
        "uuid", "node", "sensor", "modality", 123.4, gps_locked=True, pps_jitter_ns=50.0
    )
    state, reason = p.validate()
    assert state == "ASSEMBLED"
    assert reason is None

    # Missing identity
    p2 = IngestionPayload("", "", "", "u", 0.0)
    state, reason = p2.validate()
    assert state == "KILLED"

    # GPS unlocked
    p3 = IngestionPayload("uuid", "node", "sensor", "modality", 123.4, gps_locked=False)
    state, reason = p3.validate()
    assert state == "SECONDARY_QUARANTINED"
    assert reason == "gps_unlocked"


def test_payload_to_json_harden():
    # Large IQ array
    iq = [0.1] * 1000
    p = IngestionPayload(
        "uuid", "node", "sensor", "modality", 123.4, raw_value={"iq_samples": iq}
    )
    json_str = p.to_json()
    data = json.loads(json_str)

    assert "iq_samples" not in data["raw_value"]
    assert "iq_digest" in data["raw_value"]
    assert len(data["raw_value"]["iq_preview"]) == 64
    assert data["payload_checksum"] != ""
    assert data["checksum_algo"] == "sha256"


if __name__ == "__main__":
    test_payload_validation()
    test_payload_to_json_harden()
    print("Payload tests passed.")
