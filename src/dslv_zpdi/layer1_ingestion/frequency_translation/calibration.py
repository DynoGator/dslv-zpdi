"""
SPEC-004A.FREQ-CAL — Converter calibration manifest.

Calibration artifacts are canonicalized and hash-verified. Every capture that
uses a converter must reference the calibration manifest by SHA-256.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConverterCalibrationManifest:
    """
    SPEC-004A.FREQ-CAL — Canonical converter calibration record.

    Fields:
        schema_version: Manifest schema version.
        device_serial: Serial number of the converter.
        operator_id: Person or process that performed calibration.
        calibrated_at_utc: ISO-8601 timestamp.
        calibration_method: Description of method and source instrument.
        frequency_response_hz: List of calibration frequency points.
        gain_db: Gain per frequency point.
        phase_deg: Phase offset per frequency point.
        temperature_c: Optional calibration temperature.
    """

    schema_version: str
    device_serial: str
    operator_id: str
    calibrated_at_utc: str
    calibration_method: str
    frequency_response_hz: tuple[int, ...]
    gain_db: tuple[float, ...]
    phase_deg: tuple[float, ...]
    temperature_c: float | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def canonical_dict(self) -> dict[str, Any]:
        """Return a canonical dict for hashing."""
        return {
            "schema_version": self.schema_version,
            "device_serial": self.device_serial,
            "operator_id": self.operator_id,
            "calibrated_at_utc": self.calibrated_at_utc,
            "calibration_method": self.calibration_method,
            "frequency_response_hz": list(self.frequency_response_hz),
            "gain_db": list(self.gain_db),
            "phase_deg": list(self.phase_deg),
            "temperature_c": self.temperature_c,
            "evidence": self.evidence,
        }

    @property
    def sha256(self) -> str:
        """Return SHA-256 of the canonical JSON representation."""
        canonical = json.dumps(self.canonical_dict(), sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def summary(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "device_serial": self.device_serial,
            "operator_id": self.operator_id,
            "calibrated_at_utc": self.calibrated_at_utc,
            "calibration_method": self.calibration_method,
            "sha256": self.sha256,
            "point_count": len(self.frequency_response_hz),
        }
