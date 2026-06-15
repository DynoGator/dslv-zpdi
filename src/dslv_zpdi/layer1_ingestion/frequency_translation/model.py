"""
SPEC-004A.FREQ — Frequency-translation stage model.

Represents a mixer/upconverter/downconverter between the SDR native IF and the
RF frequency of interest. Preserves both native and translated frequencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FrequencyTranslationStage:
    """
    SPEC-004A.FREQ — Mixer translation stage.

    rf_frequency_hz = lo_frequency_hz + sideband_sign * if_frequency_hz

    sideband_sign = +1 → upper sideband (no inversion)
    sideband_sign = -1 → lower sideband (spectral inversion present)
    """

    native_if_center_hz: int
    lo_frequency_hz: int
    lo_source: str
    sideband_sign: int
    converter_model: str
    converter_serial: str
    converter_gain_db: float = 0.0
    converter_loss_db: float = 0.0
    filter_low_hz: int | None = None
    filter_high_hz: int | None = None
    calibration_manifest_sha256: str = ""
    calibration_timestamp: str = ""
    calibration_temperature_c: float | None = None
    frequency_uncertainty_hz: float = 0.0
    amplitude_uncertainty_db: float = 0.0
    phase_uncertainty_deg: float = 0.0
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def translated_rf_center_hz(self) -> int:
        """Return the RF frequency represented by the IF + LO translation."""
        return self.lo_frequency_hz + self.sideband_sign * self.native_if_center_hz

    @property
    def spectral_inversion(self) -> bool:
        """Return True if the lower sideband is used (spectral inversion)."""
        return self.sideband_sign == -1

    def summary(self) -> dict[str, Any]:
        return {
            "native_if_center_hz": self.native_if_center_hz,
            "translated_rf_center_hz": self.translated_rf_center_hz,
            "lo_frequency_hz": self.lo_frequency_hz,
            "lo_source": self.lo_source,
            "sideband_sign": self.sideband_sign,
            "spectral_inversion": self.spectral_inversion,
            "converter_model": self.converter_model,
            "converter_serial": self.converter_serial,
            "converter_gain_db": self.converter_gain_db,
            "converter_loss_db": self.converter_loss_db,
            "filter_low_hz": self.filter_low_hz,
            "filter_high_hz": self.filter_high_hz,
            "calibration_manifest_sha256": self.calibration_manifest_sha256,
            "calibration_timestamp": self.calibration_timestamp,
            "calibration_temperature_c": self.calibration_temperature_c,
            "frequency_uncertainty_hz": self.frequency_uncertainty_hz,
            "amplitude_uncertainty_db": self.amplitude_uncertainty_db,
            "phase_uncertainty_deg": self.phase_uncertainty_deg,
        }
