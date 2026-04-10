"""
SPEC-005A | Trust Tier: Ingested (Layer 1 Payload Contract)
Hardware-anchored ingestion payload with full SHA-256 attestation.
"""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SensorModality(Enum):
    """SPEC-005A.1 — Authorized sensor modalities."""

    RF_SDR = "rf_sdr"
    GPS_PPS = "gps_pps"
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
    trust_state: str = "ASSEMBLED"
    quarantine_reason: Optional[str] = None
    schema_version: str = "3.1"
    payload_checksum: str = ""
    checksum_algo: str = "sha256"  # SPEC-005A.2a: Full checksum metadata

    def validate(self) -> tuple[str, Optional[str]]:
        """SPEC-003 / SPEC-005A.3 — Validate packet trust state."""
        if not all([self.node_id, self.sensor_id, self.modality]):
            return "KILLED", "missing_identity"

        if not self.gps_locked:
            return "SECONDARY_QUARANTINED", "gps_unlocked"

        if self.pps_jitter_ns > 10000.0:
            return "SECONDARY_QUARANTINED", "high_pps_jitter"

        return "ASSEMBLED", None

    def to_json(self) -> str:
        """SPEC-005A.5 — Serialize to JSON with immutable digest handling."""
        # Create shallow copy to avoid mutating original state
        raw_copy = self.raw_value.copy() if isinstance(self.raw_value, dict) else {}

        # Digest IQ samples if present
        if "iq_samples" in raw_copy:
            iq = raw_copy["iq_samples"]
            if isinstance(iq, list) and len(iq) > 512:
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
