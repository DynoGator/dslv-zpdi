"""
SPEC-005A | Trust Tier: Measured (Tier 1 Raw) — Rev 3.1
"""
import json
import time
import uuid
import hashlib
from dataclasses import dataclass
from typing import Optional, Any, List
from enum import Enum

class SensorModality(Enum):
    """SPEC-005A.1a — Sensor Type Registry"""
    RF_SDR = "rf_sdr"
    GPS_PPS = "gps_pps"
    THERMAL = "thermal"
    ACOUSTIC = "acoustic"

@dataclass
class IngestionPayload:
    """SPEC-005A.1b — Hardened Universal Payload (Rev 3.1)"""
    spec_id: str = "SPEC-005A.1b"
    schema_version: str = "3.1"
    payload_uuid: str = ""
    node_id: str = ""
    sensor_id: str = ""
    modality: str = "" 
    timestamp_utc: float = 0.0
    ingest_monotonic_ns: int = 0
    raw_value: Any = None
    extracted_phases: List[float] = None  
    gps_locked: bool = False
    pps_jitter_ns: float = 0.0
    calibration_valid: bool = False
    calibration_age_s: float = 0.0
    drift_percent: float = 0.0
    source_path: str = ""
    trust_state: str = "ASSEMBLED"
    quarantine_reason: Optional[str] = None
    env_class: Optional[str] = None
    event_window_id: Optional[str] = None
    parent_trigger_id: Optional[str] = None
    payload_checksum: str = ""
    hardware_tier: int = 1

    def validate(self) -> tuple:
        """SPEC-005A.2 — Payload Self-Validation (Rev 3.1)"""
        if not self.node_id or not self.sensor_id or not self.modality:
            return "KILLED", "Missing routing identity"
        if self.payload_uuid == "":
            return "KILLED", "Missing payload_uuid"
        if self.timestamp_utc == 0.0 or not self.gps_locked:
            return "SECONDARY_QUARANTINED", "GPS untrusted — exploratory only"
        if self.pps_jitter_ns > 10_000.0:
            return "SECONDARY_QUARANTINED", "PPS jitter exceeds Tier 1 threshold (10us)"
        return "ASSEMBLED", None

    def to_json(self) -> Optional[str]:
        """SPEC-005A.3 — Serialization Gate (Rev 3.1)"""
        state, reason = self.validate()
        self.trust_state = state
        if reason:
            self.quarantine_reason = reason
        if state == "KILLED":
            return None  
        d = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        d['modality'] = self.modality 
        raw_json = json.dumps(d, sort_keys=True, default=str)
        d['payload_checksum'] = hashlib.sha256(raw_json.encode()).hexdigest()[:16]
        return json.dumps(d, default=str)
