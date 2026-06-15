"""
SPEC-004A.QUAL — Capability-based Tier-1 hardware qualification engine.

A candidate SDR is not qualified by vendor name. It must produce evidence that
meets or exceeds the production floor across every mandatory dimension.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from dslv_zpdi.layer1_ingestion.sdr.capture_result import CaptureResult, SdrHealth
from dslv_zpdi.layer1_ingestion.timing.attestation import TimingAttestation


class QualificationState(str, Enum):
    """SPEC-004A.QUAL — Qualification verdict states."""

    PASS = "PASS"
    FAIL = "FAIL"
    UNVERIFIED = "UNVERIFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    DEGRADED = "DEGRADED"


@dataclass(frozen=True)
class DimensionResult:
    """SPEC-004A.QUAL — Result for one qualification dimension."""

    name: str
    state: QualificationState
    mandatory: bool
    message: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class QualificationResult:
    """SPEC-004A.QUAL — Aggregate qualification result."""

    overall: QualificationState
    candidate_backend: str
    dimensions: tuple[DimensionResult, ...]
    warnings: tuple[str, ...] = ()

    def summary(self) -> dict[str, Any]:
        return {
            "overall": self.overall.value,
            "candidate_backend": self.candidate_backend,
            "dimensions": [
                {
                    "name": d.name,
                    "state": d.state.value,
                    "mandatory": d.mandatory,
                    "message": d.message,
                }
                for d in self.dimensions
            ],
            "warnings": list(self.warnings),
        }


class Tier1QualificationPolicy:
    """
    SPEC-004A.QUAL — Evaluate SDR evidence against the Tier-1 contract.

    Args:
        gps_fix_required: Require current GPS fix.
        pps_required: Require PPS present and healthy.
        external_reference_evidence_required: Require proof the SDR consumes the reference.
        calibration_manifest_required: Require valid converter calibration.
        production_hmac_key_required: Require production key loaded.
        no_unaccounted_sample_loss: Require capture sample accounting to match.
        allow_simulator: If False, simulated backends are rejected.
    """

    def __init__(
        self,
        gps_fix_required: bool = True,
        pps_required: bool = True,
        pps_kill_ns: float = 10_000.0,
        external_reference_evidence_required: bool = True,
        calibration_manifest_required: bool = True,
        production_hmac_key_required: bool = True,
        no_unaccounted_sample_loss: bool = True,
        allow_simulator: bool = False,
    ) -> None:
        self.gps_fix_required = gps_fix_required
        self.pps_required = pps_required
        self.pps_kill_ns = pps_kill_ns
        self.external_reference_evidence_required = external_reference_evidence_required
        self.calibration_manifest_required = calibration_manifest_required
        self.production_hmac_key_required = production_hmac_key_required
        self.no_unaccounted_sample_loss = no_unaccounted_sample_loss
        self.allow_simulator = allow_simulator

    def evaluate(
        self,
        backend_name: str,
        timing: TimingAttestation,
        health: SdrHealth,
        capture: CaptureResult,
        calibration_valid: bool = True,
        hmac_key_loaded: bool = False,
    ) -> QualificationResult:
        """SPEC-004A.QUAL — Evaluate all mandatory and optional dimensions."""
        dims: list[DimensionResult] = []
        warnings: list[str] = []

        # GPS fix
        if self.gps_fix_required:
            state = QualificationState.PASS if timing.gps_fix_valid else QualificationState.FAIL
            dims.append(DimensionResult(
                "gps_fix", state, True,
                "GPS fix valid" if timing.gps_fix_valid else "GPS fix invalid or stale"
            ))
        else:
            dims.append(DimensionResult("gps_fix", QualificationState.NOT_APPLICABLE, False))

        # PPS
        if self.pps_required:
            if not timing.pps_present:
                state = QualificationState.FAIL
                msg = "PPS not present"
            elif timing.pps_rms_jitter_ns > self.pps_kill_ns:
                state = QualificationState.FAIL
                msg = f"PPS jitter {timing.pps_rms_jitter_ns:.0f} ns exceeds kill threshold"
            else:
                state = QualificationState.PASS
                msg = f"PPS present, jitter {timing.pps_rms_jitter_ns:.0f} ns"
            dims.append(DimensionResult("pps_health", state, True, msg))
        else:
            dims.append(DimensionResult("pps_health", QualificationState.NOT_APPLICABLE, False))

        # External reference evidence
        if self.external_reference_evidence_required:
            detected = timing.external_reference_detected is True and health.backend_name != "simulated"
            state = QualificationState.PASS if detected else QualificationState.UNVERIFIED
            msg = (
                "External reference detected by SDR"
                if detected else
                "External reference configured but not software-detectable (UNVERIFIED_PHYSICAL_PROPERTY)"
            )
            dims.append(DimensionResult("external_reference_evidence", state, True, msg))
        else:
            dims.append(DimensionResult(
                "external_reference_evidence", QualificationState.NOT_APPLICABLE, False
            ))

        # Calibration manifest
        if self.calibration_manifest_required:
            state = QualificationState.PASS if calibration_valid else QualificationState.FAIL
            dims.append(DimensionResult(
                "calibration_manifest", state, True,
                "Calibration manifest valid" if calibration_valid else "Calibration manifest missing or invalid"
            ))
        else:
            dims.append(DimensionResult("calibration_manifest", QualificationState.NOT_APPLICABLE, False))

        # HMAC key
        if self.production_hmac_key_required:
            state = QualificationState.PASS if hmac_key_loaded else QualificationState.FAIL
            dims.append(DimensionResult(
                "production_hmac_key", state, True,
                "Production HMAC key loaded" if hmac_key_loaded else "Production HMAC key not loaded"
            ))
        else:
            dims.append(DimensionResult("production_hmac_key", QualificationState.NOT_APPLICABLE, False))

        # Sample loss
        if self.no_unaccounted_sample_loss:
            state = QualificationState.PASS if not capture.has_unaccounted_loss else QualificationState.FAIL
            dims.append(DimensionResult(
                "sample_accounting", state, True,
                f"Requested {capture.samples_requested}, received {capture.samples_received}"
            ))
        else:
            dims.append(DimensionResult("sample_accounting", QualificationState.NOT_APPLICABLE, False))

        # Simulator rejection
        if not self.allow_simulator and backend_name == "simulated":
            dims.append(DimensionResult(
                "simulator_rejection", QualificationState.FAIL, True,
                "Simulated backend rejected in field mode"
            ))
        else:
            dims.append(DimensionResult(
                "simulator_rejection", QualificationState.NOT_APPLICABLE, False
            ))

        # Overall verdict: any mandatory UNVERIFIED or FAIL -> not PASS
        if any(d.mandatory and d.state == QualificationState.FAIL for d in dims):
            overall = QualificationState.FAIL
        elif any(d.mandatory and d.state == QualificationState.UNVERIFIED for d in dims):
            overall = QualificationState.UNVERIFIED
        elif any(d.state == QualificationState.DEGRADED for d in dims):
            overall = QualificationState.DEGRADED
        else:
            overall = QualificationState.PASS

        warnings.extend(timing.warnings)
        if capture.has_unaccounted_loss:
            warnings.append(f"Capture sample loss: {capture.sample_loss}")

        return QualificationResult(
            overall=overall,
            candidate_backend=backend_name,
            dimensions=tuple(dims),
            warnings=tuple(warnings),
        )
