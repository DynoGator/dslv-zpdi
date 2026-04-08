"""
DSLV-ZPDI Layer 1 — Universal Payload Definition
SPEC-005A | Trust Tier: Measured (Tier 1 Raw)
"""
import json
from dataclasses import dataclass, asdict
from typing import Optional, Any
from enum import Enum

class SensorModality(Enum):
    """SPEC-005A.1a — Sensor Type Registry"""
    RF_SDR = "rf_sdr"
    GPS_PPS = "gps_pps"
    THERMAL = "thermal"
    ACOUSTIC = "acoustic"
    OPTICAL = "optical"

@dataclass
class IngestionPayload:
    """SPEC-005A.1b — The Universal Payload"""
    spec_id: str = "SPEC-005A.1b"
    node_id: str = ""
    sensor_id: str = ""
    modality: SensorModality = None
    timestamp_utc: float = 0.0
    raw_value: Any = None
    gps_locked: bool = False
    pps_jitter_ns: float = 0.0
    calibration_valid: bool = False
    hardware_tier: int = 1

    def validate(self) -> tuple[bool, str]:
        """SPEC-005A.2 — Payload Self-Validation"""
        if not self.node_id or not self.sensor_id or self.modality is None:
            return False, "KILL: Missing routing identity"
        if self.timestamp_utc == 0.0 or not self.gps_locked:
            return False, "KILL: GPS untrusted"
        return True, "PASS"

    def to_json(self) -> Optional[str]:
        """SPEC-005A.3 — Serialization Gate"""
        valid, _ = self.validate()
        if not valid:
            return None
        d = asdict(self)
        d['modality'] = self.modality.value
        return json.dumps(d)
