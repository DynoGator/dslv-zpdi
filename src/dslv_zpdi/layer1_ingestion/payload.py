"""
SPEC-005A | Trust Tier: Ingested (Layer 1 Payload Contract)
Hardware-anchored ingestion payload with full SHA-256 attestation.
"""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


from dslv_zpdi.core.states import TrustState


class SensorModality(Enum):
    """SPEC-005A.1 — Authorized sensor modalities per Section 5.3."""

    RF_SDR = "rf_sdr"
    GPS_PPS = "gps_pps"
    THERMAL = "thermal"
    ACOUSTIC = "acoustic"
    MAGNETOMETER = "magnetometer"
    INERTIAL = "inertial"


# pylint: disable=too-many-instance-attributes
@dataclass
class IngestionPayload:
    """SPEC-005A.2 — Canonical ingestion payload structure."""

    payload_uuid: str
    node_id: str
    sensor_id: str
    modality: str
    timestamp_utc: float
    ingest_monotonic_ns: int = 0
    raw_value: Dict[str, Any] = field(default_factory=dict)
    extracted_phases: List[float] = field(default_factory=list)
    gps_locked: bool = False
    pps_jitter_ns: float = 0.0
    calibration_valid: bool = False
    calibration_age_s: float = 0.0
    drift_percent: float = 0.0
    source_path: str = ""
    hardware_tier: int = 1
    trust_state: str = TrustState.ASSEMBLED.value
    quarantine_reason: Optional[str] = None
    schema_version: str = "3.1"
    payload_checksum: str = ""
    checksum_algo: str = "sha256"  # SPEC-005A.2a: Full checksum metadata

    def validate(self) -> tuple[str, Optional[str]]:
        """SPEC-003 / SPEC-005A.3 — Validate packet trust state."""
        if not all([self.node_id, self.sensor_id, self.modality]):
            return TrustState.KILLED.value, "missing_identity"

        try:
            SensorModality(self.modality)
        except ValueError:
            return TrustState.KILLED.value, "invalid_modality"

        if self.schema_version != "3.1":
            return TrustState.SECONDARY_QUARANTINED.value, "schema_version_mismatch"

        if not isinstance(self.raw_value, dict):
            return TrustState.KILLED.value, "malformed_raw_value"

        if self.extracted_phases is not None:
            if not isinstance(self.extracted_phases, list):
                return TrustState.KILLED.value, "malformed_extracted_phases"
            for ph in self.extracted_phases:
                if not isinstance(ph, (int, float)):
                    return TrustState.KILLED.value, "non_numeric_phase"
                if not -10 <= ph <= 10:
                    return TrustState.SECONDARY_QUARANTINED.value, "phase_out_of_bounds"

        if not self.gps_locked:
            return TrustState.SECONDARY_QUARANTINED.value, "gps_unlocked"

        if self.pps_jitter_ns > 10000.0:
            return TrustState.SECONDARY_QUARANTINED.value, "high_pps_jitter"

        # Tier 1 RF payloads require external clock source
        if self.modality == SensorModality.RF_SDR.value:
            clock_source = self.raw_value.get("clock_source", "unknown")
            if clock_source != "external":
                return TrustState.SECONDARY_QUARANTINED.value, "rf_clock_not_external"

        return TrustState.ASSEMBLED.value, None

    def to_json(self) -> str:
        """SPEC-005A.5 — Serialize to JSON with immutable digest handling."""
        # Create shallow copy to avoid mutating original state
        raw_copy = self.raw_value.copy() if isinstance(self.raw_value, dict) else {}

        # Digest IQ samples if present (always digest; full IQ stays binary/HDF5 only)
        if "iq_samples" in raw_copy:
            iq = raw_copy["iq_samples"]
            if isinstance(iq, list):
                iq_bytes = json.dumps(iq).encode()
                raw_copy["iq_digest"] = hashlib.sha256(iq_bytes).hexdigest()
                raw_copy["iq_preview"] = iq[:64]
                del raw_copy["iq_samples"]

        # Build dict with digested copy
        d = asdict(self)
        d["raw_value"] = raw_copy
        d["payload_checksum"] = ""

        clean_json = json.dumps(d, sort_keys=True)
        self.payload_checksum = hashlib.sha256(clean_json.encode()).hexdigest()
        d["payload_checksum"] = self.payload_checksum

        return json.dumps(d, sort_keys=True)
