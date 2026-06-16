"""
SPEC-005A.HAL — Composed HardwareHAL for Tier-1 RF metrology.

The HAL is no longer a monolithic driver wrapper. It composes:
  - TimingAuthority (e.g. LBE1421TimingAuthority)
  - SdrBackend (e.g. PlutoIioBackend)
  - FrequencyTranslationStage
  - Tier1QualificationPolicy

This design allows future SDRs to qualify without invasive rewrites.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import numpy as np

from dslv_zpdi.config_models import NodeProfile
from dslv_zpdi.core.exceptions import (
    QualificationError,
)
from dslv_zpdi.core.key_provider import KeyProvider
from dslv_zpdi.layer1_ingestion.frequency_translation.mapper import FrequencyMapper
from dslv_zpdi.layer1_ingestion.frequency_translation.model import FrequencyTranslationStage
from dslv_zpdi.layer1_ingestion.hal_base import BaseHAL
from dslv_zpdi.layer1_ingestion.payload import IngestionPayload, SensorModality
from dslv_zpdi.layer1_ingestion.sdr.base import SdrBackend
from dslv_zpdi.layer1_ingestion.sdr.capabilities import CaptureProfile
from dslv_zpdi.layer1_ingestion.sdr.qualification import (
    QualificationState,
    Tier1QualificationPolicy,
)
from dslv_zpdi.layer1_ingestion.timing.base import TimingAuthority


class HardwareHAL(BaseHAL):
    """
    SPEC-005A.HAL — Composed production HAL.

    Args:
        timing_authority: Source of PPS/GPS/chrony evidence.
        sdr_backend: SDR backend implementing SdrBackend.
        frequency_translation: Optional converter stage (direct-RF default).
        qualification_policy: Policy for Tier-1 qualification.
        fail_closed: If True, qualification failure raises QualificationError.
        key_provider: Optional key provider for HMAC key loaded check.
    """

    def __init__(
        self,
        timing_authority: TimingAuthority,
        sdr_backend: SdrBackend,
        frequency_translation: FrequencyTranslationStage | None = None,
        qualification_policy: Tier1QualificationPolicy | None = None,
        fail_closed: bool = True,
        key_provider: KeyProvider | None = None,
        profile: NodeProfile | None = None,
    ) -> None:
        self.timing_authority = timing_authority
        self.sdr_backend = sdr_backend
        self.frequency_translation = frequency_translation or FrequencyMapper.build_direct_rf_stage(
            100_000_000
        )
        self.qualification_policy = qualification_policy or Tier1QualificationPolicy()
        self.fail_closed = fail_closed
        self.key_provider = key_provider
        self._profile = profile
        self._key_loaded = self._check_key_loaded()

    def _check_key_loaded(self) -> bool:
        """SPEC-005A.HAL — Determine whether a production HMAC key is available."""
        if self.key_provider is None:
            return False
        try:
            self.key_provider.get_key()
            return True
        except Exception:  # pylint: disable=broad-except
            return False

    def _qualify(
        self,
        timing: Any,
        capture: Any,
        calibration_valid: bool = True,
    ) -> QualificationState:
        """Run qualification policy and return state or raise if fail-closed."""
        health = self.sdr_backend.health()
        result = self.qualification_policy.evaluate(
            backend_name=self.sdr_backend.backend_name,
            timing=timing,
            health=health,
            capture=capture,
            calibration_valid=calibration_valid,
            hmac_key_loaded=self._key_loaded,
        )
        if self.fail_closed and result.overall in (QualificationState.FAIL,):
            raise QualificationError(
                f"Tier-1 qualification failed for {result.candidate_backend}: "
                + "; ".join(
                    f"{d.name}={d.state.value}({d.message})"
                    for d in result.dimensions
                    if d.state != QualificationState.PASS
                )
            )
        return result.overall

    def ingest_gps_pps(
        self,
        pps_device: str = "/dev/pps0",
        node_id: str = "PI5-ALPHA",
        sensor_id: str = "GPSDO-01",
        pps_jitter_threshold_ns: float = 10_000.0,
    ) -> IngestionPayload:
        """SPEC-005A.4a — GPS/PPS live ingestion with structured timing attestation."""
        mono_ns = time.monotonic_ns()
        timing = self.timing_authority.attest()

        pps_offset_ns = float("inf")
        nearest_pps_ns = 0
        if timing.evidence.get("pps_snapshot", {}).get("history"):
            mono_edge_ns, kernel_pps_ns = timing.evidence["pps_snapshot"]["history"][-1]
            nearest_pps_ns = kernel_pps_ns
            raw_delta = mono_ns - mono_edge_ns
            pps_offset_ns = float(((raw_delta + 500_000_000) % 1_000_000_000) - 500_000_000)

        calibration_valid = (
            timing.pps_present
            and timing.pps_rms_jitter_ns <= pps_jitter_threshold_ns
            and timing.gps_fix_valid
        )

        raw_value: dict[str, Any] = {
            "pps_time_ns": nearest_pps_ns,
            "pps_offset_ns": pps_offset_ns,
            "source": "gpsdo_leo_bodnar_lbe1421",
            "pps_device": pps_device,
            "nmea_telemetry": timing.evidence.get("nmea_fix", {}),
            "timing_attestation": timing.summary(),
            "timestamp_method": "kernel_pps_plus_host_capture",
        }

        payload = IngestionPayload(
            payload_uuid=str(uuid.uuid4()),
            node_id=node_id,
            sensor_id=sensor_id,
            modality=SensorModality.GPS_PPS.value,
            timestamp_utc=time.time(),
            ingest_monotonic_ns=mono_ns,
            raw_value=raw_value,
            extracted_phases=[],
            gps_locked=timing.gps_fix_valid and timing.pps_present,
            pps_jitter_ns=timing.pps_rms_jitter_ns,
            calibration_valid=calibration_valid,
            calibration_age_s=0.0,
            drift_percent=0.0,
            source_path=pps_device,
            trust_state="ASSEMBLED",
            hardware_tier=1,
        )

        state, reason = payload.validate()
        payload.trust_state = state
        if reason:
            payload.quarantine_reason = reason
        if state == "ASSEMBLED" and timing.gps_fix_valid and timing.pps_present:
            payload.trust_state = "TIME_TRUSTED"
            if calibration_valid:
                payload.trust_state = "CAL_TRUSTED"

        return payload

    def ingest_sdr(
        self,
        center_freq: float | None = None,
        sample_rate: float | None = None,
        num_samples: int | None = None,
        node_id: str = "PI5-ALPHA",
        sensor_id: str = "PLUTO-01",
        gps_locked: bool = True,
        pps_jitter_ns: float = 500.0,
        calibration_valid: bool = True,
    ) -> IngestionPayload:
        """SPEC-005A.4b — SDR IQ live ingestion with sample accounting."""
        timing = self.timing_authority.attest()

        profile_cfg = self._profile
        center_freq = center_freq if center_freq is not None else (
            profile_cfg.rf.center_frequency_hz if profile_cfg else 100e6
        )
        sample_rate = sample_rate if sample_rate is not None else (
            profile_cfg.rf.sample_rate_hz if profile_cfg else 10e6
        )
        num_samples = num_samples if num_samples is not None else (
            profile_cfg.sdr.buffer_samples if profile_cfg else 16384
        )
        gain_db = profile_cfg.rf.gain_db if profile_cfg else 62.0

        profile = CaptureProfile(
            center_frequency_hz=int(center_freq),
            sample_rate_sps=int(sample_rate),
            bandwidth_hz=int(sample_rate),
            gain_db=gain_db,
            gain_mode=profile_cfg.rf.gain_mode if profile_cfg else "manual",
            receive_channels=(0,),
            transmit_enabled=False,
            buffer_samples=num_samples,
            num_samples=num_samples,
            external_clock_configured=self.frequency_translation.lo_source != "direct_rf"
            or timing.external_reference_configured,
        )

        result = self.sdr_backend.capture(profile)

        # Run qualification (raises in fail-closed mode on FAIL)
        _ = self._qualify(timing, result, calibration_valid=calibration_valid)

        phases = np.angle(result.samples).tolist()[:64]
        clock_att = result.clock_attestation
        clock_source = (
            "external" if clock_att and clock_att.external_reference_configured else "internal"
        )

        raw_value: dict[str, Any] = {
            "iq_samples": [[float(x.real), float(x.imag)] for x in result.samples[:64]],
            "iq_digest": _sha256_samples(result.samples[:64]),
            "iq_preview_count": min(64, len(result.samples)),
            "center_freq": result.center_frequency_hz,
            "sample_rate": result.effective_sample_rate_sps,
            "bandwidth_mhz": result.rf_bandwidth_hz / 1e6,
            "clock_source": clock_source,
            "clock_attestation": clock_att.summary() if clock_att else None,
            "timing_attestation": timing.summary(),
            "sample_loss": result.sample_loss,
            "capture_duration_s": result.capture_duration_s,
            "backend_name": result.backend_name,
            "uri": result.uri,
            "configuration_hash": result.configuration_hash,
            "frequency_translation": self.frequency_translation.summary(),
            "timestamp_method": "iio_hardware_timestamp"
            if result.backend_name == "pluto_iio"
            else "simulated",
        }

        payload = IngestionPayload(
            payload_uuid=str(uuid.uuid4()),
            node_id=node_id,
            sensor_id=sensor_id,
            modality=SensorModality.RF_SDR.value,
            timestamp_utc=time.time(),
            ingest_monotonic_ns=result.host_monotonic_start_ns,
            raw_value=raw_value,
            extracted_phases=phases,
            gps_locked=timing.gps_fix_valid,
            pps_jitter_ns=timing.pps_rms_jitter_ns,
            calibration_valid=calibration_valid and not result.has_unaccounted_loss,
            calibration_age_s=0.0,
            drift_percent=0.0,
            source_path=result.uri,
            trust_state="ASSEMBLED",
            hardware_tier=1,
        )

        state, reason = payload.validate()
        payload.trust_state = state
        if reason:
            payload.quarantine_reason = reason
        if state == "ASSEMBLED" and clock_source == "external":
            payload.trust_state = "TIME_TRUSTED"
            if payload.calibration_valid:
                payload.trust_state = "CAL_TRUSTED"

        return payload

    def wait_for_pps_edge(self, pps_device: str = "/dev/pps0", timeout_s: float = 2.0) -> bool:
        """SPEC-005A.SYNC — Block until next host PPS edge."""
        return self.timing_authority._pps.wait_for_edge(timeout_s=timeout_s)  # type: ignore[attr-defined]

    def verify_gpsdo_lock(self, device_index: int = 0) -> dict[str, Any]:
        """SPEC-005A.LOCK — Return GPSDO + SDR lock evidence."""
        timing = self.timing_authority.attest()
        health = self.sdr_backend.health()
        caps = self.sdr_backend.discover()
        return {
            "timing_attestation": timing.summary(),
            "sdr_health": health.summary(),
            "sdr_capabilities": caps.summary(),
            "frequency_translation": self.frequency_translation.summary(),
            "backend_name": self.sdr_backend.backend_name,
        }

    def verify_tier1_phase_lock(self) -> dict[str, Any]:
        """
        SPEC-005A.LOCK — Backward-compatible diagnostic entry point.

        Returns structured timing evidence; does not collapse it into a single
        misleading Boolean.
        """
        timing = self.timing_authority.attest()
        health = self.sdr_backend.health()
        return {
            "phase_lock_verified": False,  # deprecated: kept for API compat only
            "frequency_disciplined": timing.frequency_disciplined,
            "utc_epoch_disciplined": timing.utc_epoch_disciplined,
            "sample_epoch_synchronized": timing.sample_epoch_synchronized,
            "external_reference_configured": timing.external_reference_configured,
            "external_reference_detected": timing.external_reference_detected,
            "baseband_pll_locked": timing.baseband_pll_locked,
            "rf_pll_locked": timing.rx_rf_pll_locked,
            "sdr_reachable": health.reachable,
            "warnings": list(timing.warnings),
        }

    def close(self) -> None:
        """SPEC-005A.HAL — Release timing authority and SDR backend."""
        self.timing_authority.close()
        self.sdr_backend.close()


def _sha256_samples(samples: np.ndarray) -> str:
    """SPEC-005A.HAL — Return SHA-256 hex digest of a complex64 sample array."""
    import hashlib

    return hashlib.sha256(samples.tobytes()).hexdigest()
