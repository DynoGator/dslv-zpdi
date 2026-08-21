"""Unit tests for IngestionPayload contract."""

from dslv_zpdi.layer1_ingestion.payload import IngestionPayload, SensorModality


def test_payload_validation():
    # Valid payload
    p = IngestionPayload(
        "uuid",
        "node",
        "sensor",
        SensorModality.RF_SDR.value,
        123.4,
        gps_locked=True,
        pps_jitter_ns=5.0,
        raw_value={"clock_source": "external"},
    )
    state, reason = p.validate()
    assert state == "ASSEMBLED"
    assert reason is None

    # Missing identity
    p2 = IngestionPayload("", "", "", SensorModality.RF_SDR.value, 0.0)
    state, reason = p2.validate()
    assert state == "KILLED"

    # Invalid modality
    p2b = IngestionPayload("uuid", "node", "sensor", "not_a_modality", 123.4)
    state, reason = p2b.validate()
    assert state == "KILLED"
    assert reason == "invalid_modality"

    # GPS unlocked
    p3 = IngestionPayload(
        "uuid",
        "node",
        "sensor",
        SensorModality.RF_SDR.value,
        123.4,
        gps_locked=False,
        raw_value={"clock_source": "external"},
    )
    state, reason = p3.validate()
    assert state == "SECONDARY_QUARANTINED"
    assert reason == "gps_unlocked"

    # RF clock not external
    p4 = IngestionPayload(
        "uuid",
        "node",
        "sensor",
        SensorModality.RF_SDR.value,
        123.4,
        gps_locked=True,
        pps_jitter_ns=5.0,
        raw_value={"clock_source": "internal"},
    )
    state, reason = p4.validate()
    assert state == "SECONDARY_QUARANTINED"
    assert reason == "rf_clock_not_external"


def test_payload_to_binary_harden():
    # Large IQ array
    iq = [[0.1, 0.1]] * 10
    p = IngestionPayload("uuid", "node", "sensor", "modality", 123.4, raw_value={"iq_samples": iq})
    binary_data = p.to_binary()

    assert "iq_samples" not in p.raw_value
    assert "iq_digest" in p.raw_value
    assert p.payload_checksum != ""
    assert p.checksum_algo == "blake2b"
    assert len(binary_data) > 0


if __name__ == "__main__":
    test_payload_validation()
    test_payload_to_binary_harden()
    print("Payload tests passed.")
