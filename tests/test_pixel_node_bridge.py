"""
SPEC-016.7 — Pixel 9 Pro XL mobile node bridge unit tests.

All tests run without hardware (simulator-first).
"""

import pytest

from dslv_zpdi.layer1_ingestion.pixel_node_bridge import (
    PixelHttpTransport,
    PixelNodeBridge,
    PixelSimulator,
    PixelTelemetry,
    PixelTrustScorer,
)


class TestPixelTrustScorer:
    def test_perfect_telemetry(self):
        scorer = PixelTrustScorer()
        data = {
            "timestamp_utc": 1749000000.0,
            "magnetometer_ut": [30.0, 10.0, 40.0],
            "gps": {"lat": 40.0, "lon": -74.0, "accuracy": 5.0},
            "camera_frame_hash": "a1b2c3d4",
            "pressure_hpa": 1013.0,
            "light_lux": 300.0,
        }
        score, flags = scorer.score(data, received_utc=1749000000.0)
        assert score >= 0.9
        assert flags == []

    def test_missing_gps_penalty(self):
        scorer = PixelTrustScorer()
        data = {"timestamp_utc": 1749000000.0}
        score, flags = scorer.score(data, received_utc=1749000000.0)
        assert "no_gps" in flags
        assert score < 1.0

    def test_coarse_gps_penalty(self):
        scorer = PixelTrustScorer()
        data = {"gps": {"accuracy": 100.0}, "timestamp_utc": 1749000000.0}
        score, flags = scorer.score(data, received_utc=1749000000.0)
        assert "coarse_gps" in flags

    def test_mag_anomaly(self):
        scorer = PixelTrustScorer()
        data = {
            "magnetometer_ut": [1.0, 1.0, 1.0],  # ~1.7 µT — way below Earth field
            "timestamp_utc": 1749000000.0,
        }
        score, flags = scorer.score(data, received_utc=1749000000.0)
        assert "mag_anomaly" in flags

    def test_stale_data(self):
        scorer = PixelTrustScorer(staleness_sec=10.0)
        data = {"timestamp_utc": 1749000000.0}
        score, flags = scorer.score(data, received_utc=1749000015.0)
        assert "stale_data" in flags

    def test_no_tamper_evidence(self):
        scorer = PixelTrustScorer()
        data = {"timestamp_utc": 1749000000.0, "gps": {"accuracy": 5.0}}
        score, flags = scorer.score(data, received_utc=1749000000.0)
        assert "no_tamper_evidence" in flags


class TestPixelSimulator:
    def test_simulator_returns_telemetry(self):
        sim = PixelSimulator()
        scorer = PixelTrustScorer()
        telem = sim.poll(scorer)
        assert telem.transport == "sim"
        assert telem.magnetometer_ut is not None
        assert telem.gps_lat == pytest.approx(40.7128)
        assert telem.gps_accuracy is not None
        assert telem.trust_score > 0.5

    def test_simulator_camera_hash_periodic(self):
        sim = PixelSimulator()
        scorer = PixelTrustScorer()
        hashes = [sim.poll(scorer).camera_frame_hash for _ in range(5)]
        assert any(h is not None for h in hashes)


class TestPixelHttpTransport:
    def test_unreachable_returns_stale_or_empty(self):
        # Point to a port that is definitely closed
        transport = PixelHttpTransport(host="127.0.0.1", port=59998, timeout_sec=1.0, retries=1)
        scorer = PixelTrustScorer()
        telem = transport.poll(scorer)
        assert telem.transport == "http"
        assert "unreachable" in telem.trust_flags or "hotspot_drop" in telem.trust_flags
        assert telem.trust_score < 0.5

    def test_cached_stale_on_repeated_failure(self):
        transport = PixelHttpTransport(host="127.0.0.1", port=59998, timeout_sec=1.0, retries=0)
        scorer = PixelTrustScorer()
        # First call — no cache, should get empty/unreachable
        t1 = transport.poll(scorer)
        assert "no_cache" in t1.trust_flags
        # Manually inject a fake last_good
        transport._last_good = PixelTelemetry(
            timestamp_utc=1749000000.0,
            trust_score=0.8,
            trust_flags=[],
            transport="http",
            gps_lat=40.0,
            magnetometer_ut=[30.0, 10.0, 40.0],
        )
        t2 = transport.poll(scorer)
        assert "hotspot_drop" in t2.trust_flags
        assert t2.trust_score < 0.6
        assert t2.gps_lat == 40.0


class TestPixelNodeBridge:
    def test_bridge_poll_uses_http_when_available(self, monkeypatch):
        bridge = PixelNodeBridge(host="127.0.0.1", http_port=59998, trust_threshold=0.5)
        # Monkeypatch HTTP to return a synthetic telemetry
        synthetic = PixelTelemetry(
            timestamp_utc=1749000000.0,
            trust_score=0.9,
            trust_flags=[],
            transport="http",
            magnetometer_ut=[25.0, 5.0, 35.0],
        )
        bridge.http.poll = lambda scorer: synthetic  # type: ignore[method-assign]
        result = bridge.poll()
        assert result.transport == "http"
        assert result.trust_score == 0.9

    def test_bridge_falls_back_to_sim(self):
        bridge = PixelNodeBridge(host="127.0.0.1", http_port=59998)
        result = bridge.poll()
        assert result.transport == "sim"
        assert result.trust_score > 0.0

    def test_payload_serialization(self):
        sim = PixelSimulator()
        scorer = PixelTrustScorer()
        telem = sim.poll(scorer)
        payload_dict = telem.to_ingestion_payload(node_id="TEST-PIXEL")
        assert payload_dict["node_id"] == "TEST-PIXEL"
        assert payload_dict["modality"] == "gps_pps"
        assert payload_dict["hardware_tier"] == 2
        assert payload_dict["raw_value"]["trust_score"] == telem.trust_score
        assert "payload_checksum" in payload_dict

    def test_payload_modality_mag_when_no_gps(self):
        telem = PixelTelemetry(
            timestamp_utc=1749000000.0,
            magnetometer_ut=[30.0, 10.0, 40.0],
            trust_score=0.8,
            trust_flags=[],
            transport="sim",
        )
        payload_dict = telem.to_ingestion_payload()
        assert payload_dict["modality"] == "magnetometer"
