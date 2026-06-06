"""
SPEC-015.8 — RadonEye ingestor unit and integration tests.

All tests run without hardware (simulator-first).
"""

import json
import struct

import pytest

from dslv_zpdi.layer1_ingestion.radoneye_ingestor import (
    RadonEyeSimulator,
    RadonEyeBleTransport,
    RadonEyeHttpTransport,
    RadonEyeIngestor,
    RadonSample,
    _BQ_M3_TO_PCI_L,
)


class TestRadonEyeSimulator:
    def test_simulator_returns_positive_values(self):
        sim = RadonEyeSimulator(baseline_bq_m3=100.0, noise_sigma=0.0)
        s = sim.read()
        assert s.radon_Bqm3 > 0
        assert s.radon_pCiL > 0
        assert s.transport == "sim"
        assert s.sample_quality == "good"
        assert s.provenance["simulator"] is True

    def test_simulator_diurnal_variation(self):
        sim = RadonEyeSimulator(baseline_bq_m3=100.0, noise_sigma=0.0)
        samples = [sim.read() for _ in range(5)]
        # All samples should be within reasonable bounds
        for s in samples:
            assert 50 <= s.radon_Bqm3 <= 200

    def test_simulator_pCiL_conversion_accuracy(self):
        sim = RadonEyeSimulator(baseline_bq_m3=111.0, noise_sigma=0.0)
        s = sim.read()
        # 111 Bq/m³ ≈ 3.0 pCi/L (allow diurnal swing ±20)
        assert 2.0 <= s.radon_pCiL <= 4.5


class TestRadonBleParsing:
    def test_parse_valid_payload(self):
        transport = RadonEyeBleTransport()
        # Build a valid 20-byte response
        data = bytes([0x50, 0x10])
        data += struct.pack("<f", 148.0)   # 10-min
        data += struct.pack("<f", 152.0)   # day
        data += struct.pack("<f", 145.0)   # month
        data += struct.pack("<H", 42)      # pulse
        data += struct.pack("<H", 7)       # pulse 10min
        data += bytes(2)  # padding to 20

        sample = transport._parse_data(data)
        assert sample.radon_Bqm3 == 148.0
        assert sample.radon_pCiL == pytest.approx(148.0 * _BQ_M3_TO_PCI_L, rel=1e-4)
        assert sample.provenance["pulse_count"] == 42
        assert sample.provenance["pulse_10min"] == 7

    def test_parse_short_payload_raises(self):
        transport = RadonEyeBleTransport()
        with pytest.raises(ValueError):
            transport._parse_data(bytes([0x50, 0x10, 0x00]))

    def test_parse_unexpected_header_warns(self, caplog):
        transport = RadonEyeBleTransport()
        data = bytes([0x51, 0x10])
        data += struct.pack("<f", 100.0)
        data += struct.pack("<f", 100.0)
        data += struct.pack("<f", 100.0)
        data += struct.pack("<H", 0)
        data += struct.pack("<H", 0)
        data += bytes(2)
        with caplog.at_level("WARNING"):
            transport._parse_data(data)
        assert "unexpected response header" in caplog.text


class TestRadonHttpParsing:
    def test_parse_json_normalizes_fields(self):
        transport = RadonEyeHttpTransport()
        raw = {
            "radon_bq_m3": 74.0,
            "timestamp_utc": 1749000000.0,
            "unit_id": "RE200-ABC123",
            "firmware": "2.0.4",
        }
        sample = transport._parse_json(raw, latency_ms=45.0)
        assert sample.radon_Bqm3 == 74.0
        assert sample.device_serial == "RE200-ABC123"
        assert sample.firmware == "2.0.4"
        assert sample.transport == "http"
        assert sample.provenance["fetch_latency_ms"] == 45.0

    def test_parse_json_fallback_keys(self):
        transport = RadonEyeHttpTransport()
        raw = {
            "radon_bq_m3": 50.0,
            "serial": "RE200-DEF456",
        }
        sample = transport._parse_json(raw, latency_ms=12.0)
        assert sample.device_serial == "RE200-DEF456"


class TestRadonSampleToPayload:
    def test_payload_structure(self):
        sim = RadonEyeSimulator(baseline_bq_m3=111.0, noise_sigma=0.0)
        sample = sim.read()
        payload_dict = sample.to_ingestion_payload(node_id="TEST-NODE")
        assert payload_dict["node_id"] == "TEST-NODE"
        assert payload_dict["modality"] == "radon"
        assert payload_dict["hardware_tier"] == 2
        assert payload_dict["raw_value"]["radon_pCiL"] == sample.radon_pCiL
        assert "payload_checksum" in payload_dict

    def test_payload_checksum_present(self):
        sim = RadonEyeSimulator(baseline_bq_m3=50.0, noise_sigma=0.0)
        sample = sim.read()
        payload_dict = sample.to_ingestion_payload()
        assert payload_dict["payload_checksum"] != ""
        assert len(payload_dict["payload_checksum"]) == 64  # SHA-256 hex


class TestRadonEyeIngestorFailover:
    @pytest.mark.asyncio
    async def test_ingestor_falls_back_to_sim(self):
        ingestor = RadonEyeIngestor(
            device_address="FF:FF:FF:FF:FF:FF",  # impossible address → BLE fails fast
            http_url="http://localhost:59999",    # nothing listening → HTTP fails
            prefer_ble=True,
        )
        sample = await ingestor.read()
        assert sample.transport == "sim"
        assert sample.radon_Bqm3 > 0

    @pytest.mark.asyncio
    async def test_ingestor_http_first_then_sim(self):
        ingestor = RadonEyeIngestor(
            http_url="http://localhost:59999",
            prefer_ble=False,
        )
        sample = await ingestor.read()
        assert sample.transport == "sim"
