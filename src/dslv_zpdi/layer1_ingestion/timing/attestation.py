"""
SPEC-005A | Structured timing and clock attestations.

These dataclasses keep every evidence dimension explicit. Unknown evidence is
represented as None, not silently converted to True or False.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ClockAttestation:
    """SPEC-005A.CLOCK — Evidence about the SDR clock configuration and state."""

    external_reference_configured: bool
    external_reference_detected: bool | None
    reference_frequency_hz: int | None
    baseband_pll_locked: bool | None
    rx_rf_pll_locked: bool | None
    tx_rf_pll_locked: bool | None
    sample_epoch_synchronized: bool
    inter_node_sample_phase_synchronized: bool
    rf_phase_synchronized: bool
    evidence: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def summary(self) -> dict[str, Any]:
        """Return a JSON-serializable summary dict."""
        return {
            "external_reference_configured": self.external_reference_configured,
            "external_reference_detected": self.external_reference_detected,
            "reference_frequency_hz": self.reference_frequency_hz,
            "baseband_pll_locked": self.baseband_pll_locked,
            "rx_rf_pll_locked": self.rx_rf_pll_locked,
            "tx_rf_pll_locked": self.tx_rf_pll_locked,
            "sample_epoch_synchronized": self.sample_epoch_synchronized,
            "inter_node_sample_phase_synchronized": self.inter_node_sample_phase_synchronized,
            "rf_phase_synchronized": self.rf_phase_synchronized,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class TimingAttestation:
    """
    SPEC-005A.TIMING — Host-side timing authority evidence.

    The convenience Boolean `frequency_disciplined` means the GPSDO is healthy
    and an external reference is configured. It does NOT prove that the SDR PLL
    has locked to the reference or that sample epochs are aligned.
    """

    gps_fix_valid: bool
    gps_fix_age_seconds: float
    satellites_used: int
    hdop: float | None

    pps_present: bool
    pps_history_samples: int
    pps_rms_jitter_ns: float
    chrony_synchronized: bool
    chrony_reference_id: str | None
    chrony_system_offset_ns: float | None

    external_reference_configured: bool
    external_reference_detected: bool | None
    reference_frequency_hz: int | None

    baseband_pll_locked: bool | None
    rx_rf_pll_locked: bool | None
    tx_rf_pll_locked: bool | None

    frequency_disciplined: bool
    utc_epoch_disciplined: bool
    sample_epoch_synchronized: bool
    inter_node_sample_phase_synchronized: bool
    rf_phase_synchronized: bool

    evidence: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def summary(self) -> dict[str, Any]:
        return {
            "gps_fix_valid": self.gps_fix_valid,
            "gps_fix_age_seconds": self.gps_fix_age_seconds,
            "satellites_used": self.satellites_used,
            "hdop": self.hdop,
            "pps_present": self.pps_present,
            "pps_history_samples": self.pps_history_samples,
            "pps_rms_jitter_ns": self.pps_rms_jitter_ns,
            "chrony_synchronized": self.chrony_synchronized,
            "chrony_reference_id": self.chrony_reference_id,
            "chrony_system_offset_ns": self.chrony_system_offset_ns,
            "external_reference_configured": self.external_reference_configured,
            "external_reference_detected": self.external_reference_detected,
            "reference_frequency_hz": self.reference_frequency_hz,
            "baseband_pll_locked": self.baseband_pll_locked,
            "rx_rf_pll_locked": self.rx_rf_pll_locked,
            "tx_rf_pll_locked": self.tx_rf_pll_locked,
            "frequency_disciplined": self.frequency_disciplined,
            "utc_epoch_disciplined": self.utc_epoch_disciplined,
            "sample_epoch_synchronized": self.sample_epoch_synchronized,
            "inter_node_sample_phase_synchronized": self.inter_node_sample_phase_synchronized,
            "rf_phase_synchronized": self.rf_phase_synchronized,
            "warnings": list(self.warnings),
        }
