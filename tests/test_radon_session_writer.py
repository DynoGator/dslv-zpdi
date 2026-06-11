"""
SPEC-018.10 — Radon session writer integration tests.

Writes a full mock 48-hour envelope and validates every checksum round-trips.
"""

import tempfile
import time
from pathlib import Path

import numpy as np

from dslv_zpdi.layer3_telemetry.radon_session_writer import (
    AtmosphereRecord,
    CertifiedCRMRecord,
    MobileNodeRecord,
    RadonSessionWriter,
    SpaceWeatherRecord,
    ValidationIndexRecord,
)


class TestRadonSessionWriter:
    def test_create_and_close(self):
        with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
            path = tmp.name
        try:
            writer = RadonSessionWriter(path, operator_id="TEST-OP")
            assert Path(path).exists()
            writer.close()
        finally:
            Path(path).unlink(missing_ok=True)

    def test_write_all_branches(self):
        with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
            path = tmp.name
        try:
            with RadonSessionWriter(path, operator_id="TEST-OP") as writer:
                writer.write_certified_crm(
                    CertifiedCRMRecord(
                        timestamp_utc=time.time(),
                        radon_pCiL=4.0,
                        radon_Bqm3=148.0,
                        device_serial="RE200-ABC123",
                    )
                )
                writer.write_macro_atmosphere(
                    AtmosphereRecord(
                        timestamp_utc=time.time(),
                        pressure_hPa=1013.25,
                        dp_dt_hPa_h=-0.5,
                        relative_humidity_pct=65.0,
                    )
                )
                writer.write_space_weather(
                    SpaceWeatherRecord(
                        timestamp_utc=time.time(),
                        kp_index=3.0,
                        imf_bz_nt=-2.5,
                    )
                )
                writer.write_mobile_node(
                    MobileNodeRecord(
                        timestamp_utc=time.time(),
                        magnetometer_ut=[30.0, 10.0, 40.0],
                        gps_lat=40.7128,
                        gps_lon=-74.0060,
                        camera_frame_hash="a1b2c3d4",
                        trust_score=0.85,
                    )
                )
                writer.write_validation_index(
                    ValidationIndexRecord(
                        timestamp_utc=time.time(),
                        chi_tau=0.72,
                        review_flag=True,
                        review_reason="pilot_threshold_exceeded",
                    )
                )

                manifest = writer.write_manifest()
                assert manifest["manifest_version"] == "1.0"
                assert manifest["operator_id"] == "TEST-OP"
                assert manifest["analysis_hash"] != ""
                assert "hmac_sha256" in manifest

                for branch in (
                    "certified_crm",
                    "macro_atmosphere",
                    "space_weather",
                    "mobile_node_tier2",
                    "validation_index",
                ):
                    assert branch in manifest["branches"]
                    assert manifest["branches"][branch]["record_count"] == 1

                assert writer.verify_manifest() is True
        finally:
            Path(path).unlink(missing_ok=True)

    def test_manifest_checksum_roundtrip(self):
        with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
            path = tmp.name
        try:
            with RadonSessionWriter(path, operator_id="TEST-OP") as writer:
                for i in range(10):
                    writer.write_certified_crm(
                        CertifiedCRMRecord(
                            timestamp_utc=1749000000.0 + i * 600,
                            radon_pCiL=3.5 + i * 0.1,
                            radon_Bqm3=130.0 + i * 3.7,
                            device_serial="RE200-ABC123",
                        )
                    )
                writer.write_manifest()
                assert writer.verify_manifest() is True
        finally:
            Path(path).unlink(missing_ok=True)

    def test_certified_report_archive(self):
        with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
            path = tmp.name
        try:
            with RadonSessionWriter(path) as writer:
                report = b"This is the native certified report PDF bytes."
                ds_path = writer.archive_certified_report(report, "report_2026-06-05.pdf")
                assert "report_2026-06-05.pdf" in ds_path
        finally:
            Path(path).unlink(missing_ok=True)

    def test_additive_existing_file(self):
        with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
            path = tmp.name
        try:
            with RadonSessionWriter(path) as w1:
                w1.write_certified_crm(
                    CertifiedCRMRecord(
                        timestamp_utc=1749000000.0,
                        radon_pCiL=4.0,
                        radon_Bqm3=148.0,
                        device_serial="RE200-ABC123",
                    )
                )

            # Re-open and append (additive)
            with RadonSessionWriter(path) as w2:
                w2.write_certified_crm(
                    CertifiedCRMRecord(
                        timestamp_utc=1749000600.0,
                        radon_pCiL=4.1,
                        radon_Bqm3=151.7,
                        device_serial="RE200-ABC123",
                    )
                )
                manifest = w2.write_manifest()
                assert manifest["branches"]["certified_crm"]["record_count"] == 2
                assert w2.verify_manifest() is True
        finally:
            Path(path).unlink(missing_ok=True)

    def test_48_hour_mock_envelope(self):
        """Write a realistic 48-hour mock session and verify integrity."""
        with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
            path = tmp.name
        try:
            with RadonSessionWriter(path, operator_id="KIMI-PHASE2B") as writer:
                base_time = 1749000000.0
                hours = 48
                samples_per_hour = 6  # Every 10 minutes for radon

                for i in range(hours * samples_per_hour):
                    ts = base_time + i * 600
                    writer.write_certified_crm(
                        CertifiedCRMRecord(
                            timestamp_utc=ts,
                            radon_pCiL=4.0 + (i % 5) * 0.1,
                            radon_Bqm3=148.0 + (i % 5) * 3.7,
                            device_serial="RE200-ABC123",
                        )
                    )

                for i in range(hours):
                    ts = base_time + i * 3600
                    writer.write_macro_atmosphere(
                        AtmosphereRecord(
                            timestamp_utc=ts,
                            pressure_hPa=1013.0 + np.sin(i * np.pi / 12) * 5,
                            dp_dt_hPa_h=-0.3,
                            relative_humidity_pct=60.0 + (i % 10),
                            wind_speed_ms=3.5,
                            local_temp_c=22.0,
                        )
                    )

                for i in range(hours // 3):
                    ts = base_time + i * 3 * 3600
                    writer.write_space_weather(
                        SpaceWeatherRecord(
                            timestamp_utc=ts,
                            kp_index=2.0 + (i % 4),
                            imf_bz_nt=-1.0,
                            solar_wind_speed_kms=400.0,
                        )
                    )

                for i in range(hours * 2):
                    ts = base_time + i * 1800
                    writer.write_mobile_node(
                        MobileNodeRecord(
                            timestamp_utc=ts,
                            magnetometer_ut=[30.0, 10.0, 40.0],
                            gps_lat=40.7128,
                            gps_lon=-74.0060,
                            gps_accuracy=8.0,
                            camera_frame_hash=f"hash_{i:04d}",
                            trust_score=0.9,
                        )
                    )

                for i in range(hours):
                    ts = base_time + i * 3600
                    writer.write_validation_index(
                        ValidationIndexRecord(
                            timestamp_utc=ts,
                            chi_tau=0.55 + (i % 10) * 0.02,
                            pilot_threshold=0.65,
                            review_flag=(i % 10) > 7,
                        )
                    )

                manifest = writer.write_manifest()
                assert manifest["branches"]["certified_crm"]["record_count"] == hours * samples_per_hour
                assert manifest["branches"]["macro_atmosphere"]["record_count"] == hours
                assert manifest["branches"]["space_weather"]["record_count"] == hours // 3
                assert manifest["branches"]["mobile_node_tier2"]["record_count"] == hours * 2
                assert manifest["branches"]["validation_index"]["record_count"] == hours
                assert writer.verify_manifest() is True
        finally:
            Path(path).unlink(missing_ok=True)
