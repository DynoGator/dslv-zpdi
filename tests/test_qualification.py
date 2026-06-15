"""Tests for capability-based Tier-1 qualification engine (SPEC-004A.QUAL)."""

from __future__ import annotations

import numpy as np

from dslv_zpdi.layer1_ingestion.sdr.capture_result import CaptureResult, SdrHealth
from dslv_zpdi.layer1_ingestion.sdr.qualification import (
    QualificationState,
    Tier1QualificationPolicy,
)
from dslv_zpdi.layer1_ingestion.timing.attestation import TimingAttestation


def _good_timing() -> TimingAttestation:
    return TimingAttestation(
        gps_fix_valid=True,
        gps_fix_age_seconds=0.5,
        satellites_used=12,
        hdop=0.8,
        pps_present=True,
        pps_history_samples=10,
        pps_rms_jitter_ns=500.0,
        chrony_synchronized=True,
        chrony_reference_id="PPS",
        chrony_system_offset_ns=20.0,
        external_reference_configured=True,
        external_reference_detected=True,
        reference_frequency_hz=10_000_000,
        baseband_pll_locked=True,
        rx_rf_pll_locked=True,
        tx_rf_pll_locked=None,
        frequency_disciplined=True,
        utc_epoch_disciplined=True,
        sample_epoch_synchronized=False,
        inter_node_sample_phase_synchronized=False,
        rf_phase_synchronized=False,
    )


def _good_capture() -> CaptureResult:
    return CaptureResult(
        samples=np.zeros(1024, dtype=np.complex64),
        host_monotonic_start_ns=0,
        host_utc_start=0.0,
        host_monotonic_end_ns=1_000_000_000,
        host_utc_end=1.0,
        samples_requested=1024,
        samples_received=1024,
    )


def _health(backend: str = "pluto_iio") -> SdrHealth:
    return SdrHealth(
        backend_name=backend,
        uri="test",
        reachable=True,
        rx_enabled=True,
        tx_enabled=False,
    )


class TestTier1QualificationPolicy:
    def test_pass_with_full_evidence(self):
        policy = Tier1QualificationPolicy()
        result = policy.evaluate(
            backend_name="pluto_iio",
            timing=_good_timing(),
            health=_health(),
            capture=_good_capture(),
            calibration_valid=True,
            hmac_key_loaded=True,
        )
        assert result.overall == QualificationState.PASS

    def test_fail_missing_gps(self):
        timing = _good_timing()
        timing = TimingAttestation(
            **{**timing.__dict__, "gps_fix_valid": False, "pps_present": True}
        )
        policy = Tier1QualificationPolicy()
        result = policy.evaluate(
            backend_name="pluto_iio",
            timing=timing,
            health=_health(),
            capture=_good_capture(),
            calibration_valid=True,
            hmac_key_loaded=True,
        )
        assert result.overall == QualificationState.FAIL

    def test_unverified_external_reference(self):
        timing = _good_timing()
        timing = TimingAttestation(**{**timing.__dict__, "external_reference_detected": None})
        policy = Tier1QualificationPolicy()
        result = policy.evaluate(
            backend_name="pluto_iio",
            timing=timing,
            health=_health(),
            capture=_good_capture(),
            calibration_valid=True,
            hmac_key_loaded=True,
        )
        assert result.overall == QualificationState.UNVERIFIED

    def test_rejects_simulator_in_field_mode(self):
        policy = Tier1QualificationPolicy(allow_simulator=False)
        result = policy.evaluate(
            backend_name="simulated",
            timing=_good_timing(),
            health=_health("simulated"),
            capture=_good_capture(),
            calibration_valid=True,
            hmac_key_loaded=True,
        )
        assert result.overall == QualificationState.FAIL
        dim = next(d for d in result.dimensions if d.name == "simulator_rejection")
        assert dim.state == QualificationState.FAIL

    def test_sample_loss_fails(self):
        capture = CaptureResult(
            samples=np.zeros(100, dtype=np.complex64),
            host_monotonic_start_ns=0,
            host_utc_start=0.0,
            host_monotonic_end_ns=1_000_000_000,
            host_utc_end=1.0,
            samples_requested=1024,
            samples_received=100,
        )
        policy = Tier1QualificationPolicy()
        result = policy.evaluate(
            backend_name="pluto_iio",
            timing=_good_timing(),
            health=_health(),
            capture=capture,
            calibration_valid=True,
            hmac_key_loaded=True,
        )
        assert result.overall == QualificationState.FAIL
