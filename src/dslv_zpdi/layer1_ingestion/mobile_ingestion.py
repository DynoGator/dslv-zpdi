"""
SPEC-005A.4 — Mobile Layer 1 Ingestion Driver (Rev 3.5)

Wraps termux-sensor streaming output and produces canonical
IngestionPayload objects for the three-layer pipeline.

Phase extraction (Hilbert transform) is performed HERE in Layer 1
per SPEC-005.  Mobile has no GPS/PPS hardware, so all packets are
inherently SECONDARY_QUARANTINED at trust-state validation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

import numpy as np

from src.dslv_zpdi.layer2_core.coherence import CoherenceScorer, CoherencePacket
from src.dslv_zpdi.layer2_core.fusion_engine import OrientationTracker, apply_orientation_weight

log = logging.getLogger("zpdi.layer1")

_coherence_engine = CoherenceScorer()

# Absolute host path is mandatory: the Termux binary is not on $PATH inside
# the Debian proot.
TERMUX_SENSOR_BIN = "/data/data/com.termux/files/usr/bin/termux-sensor"

# Exact sensor names from `termux-sensor -l` on Pixel 9 Pro XL.
SENSORS = (
    "ICM45631 Accelerometer",
    "MMC5616 Magnetometer",
    "ICP20100 Pressure Sensor",
    "ICM45631 Gyroscope",
    "Rotation Vector Sensor",
    "Geomagnetic Rotation Vector Sensor",
    "Gravity Sensor",
)

# Sensor name → canonical modality string
SENSOR_MODALITY_MAP = {
    "ICM45631 Accelerometer": "accel",
    "MMC5616 Magnetometer": "magnetometer",
    "ICP20100 Pressure Sensor": "barometer",
    "ICM45631 Gyroscope": "gyroscope",
    "Rotation Vector Sensor": "rotation_vector",
    "Geomagnetic Rotation Vector Sensor": "geomagnetic_rotation",
    "Gravity Sensor": "gravity",
}

# Rolling window size for Hilbert phase extraction
PHASE_WINDOW = 32

# Module-level orientation tracker (SPEC-006.6)
_ORIENTATION = OrientationTracker(window=8)


# ---------------------------------------------------------------------------
# Lightweight Hilbert transform (numpy-only, no scipy dependency)
# ---------------------------------------------------------------------------
# SPEC-003A
def _hilbert_phases(signal: np.ndarray) -> List[float]:
    """Return instantaneous phases of the analytic signal via FFT."""
    if len(signal) < 4:
        return []
    n = len(signal)
    fft_size = 1 << (n - 1).bit_length()
    padded = np.zeros(fft_size, dtype=np.float64)
    padded[:n] = signal
    spec = np.fft.fft(padded)
    h = np.zeros_like(spec)
    h[0] = spec[0]
    if fft_size % 2 == 0:
        h[1 : fft_size // 2] = 2.0 * spec[1 : fft_size // 2]
        h[fft_size // 2] = spec[fft_size // 2]
    else:
        h[1 : (fft_size + 1) // 2] = 2.0 * spec[1 : (fft_size + 1) // 2]
    analytic = np.fft.ifft(h)
    phases = np.angle(analytic[:n])
    return phases.tolist()


# ---------------------------------------------------------------------------
# Rolling phase-extraction buffers (one per sensor)
# ---------------------------------------------------------------------------
# SPEC-003A
class _PhaseBuffers:
    """SPEC-003A"""
    def __init__(self, window: int = PHASE_WINDOW):
        """SPEC-003A"""
        self._bufs: dict[str, List[float]] = {}
        self._window = window

    def push(self, sensor: str, value: float) -> List[float]:
        """SPEC-003A"""
        buf = self._bufs.setdefault(sensor, [])
        buf.append(value)
        if len(buf) > self._window:
            buf.pop(0)
        return _hilbert_phases(np.array(buf, dtype=np.float64))


_PHASE_BUFFERS = _PhaseBuffers()


# ---------------------------------------------------------------------------
# Payload construction helpers
# ---------------------------------------------------------------------------
# SPEC-003A
def _extract_magnitude(reading: dict[str, Any]) -> float:
    """Compute vector magnitude for accelerometer / magnetometer / gyroscope / gravity samples."""
    x = reading.get("x", 0.0)
    y = reading.get("y", 0.0)
    z = reading.get("z", 0.0)
    return math.sqrt(x * x + y * y + z * z)


def _build_extracted_phases(sensor_name: str, reading: dict[str, Any]) -> List[float]:
    """Layer 1 phase extraction per SPEC-005.

    * Accelerometer  → magnitude vector → Hilbert → phases
    * Magnetometer   → magnitude vector → Hilbert → phases
    * Gyroscope      → magnitude vector → Hilbert → phases
    * Gravity        → magnitude vector → Hilbert → phases
    * Rotation Vector → reference-only (quaternion/orientation)
    """
    modality = SENSOR_MODALITY_MAP.get(sensor_name, "unknown")
    if modality in ("accel", "magnetometer", "gyroscope", "gravity"):
        mag = _extract_magnitude(reading)
        return _PHASE_BUFFERS.push(sensor_name, mag)
    if modality in ("rotation_vector", "geomagnetic_rotation"):
        # Feed orientation quaternion into fusion tracker (no phase vector produced)
        _ORIENTATION.push(reading)
    # barometer / rotation_vector / geomagnetic_rotation / unknown → no phase vector
    return []


# ---------------------------------------------------------------------------
# Hardened IngestionPayload — SPEC-005A.1b (Rev 3.5)
# ---------------------------------------------------------------------------
@dataclass
class IngestionPayload:
    """SPEC-005A.1b — Hardened Universal Payload (Rev 3.5)"""
    spec_id: str = "SPEC-005A.1b"
    schema_version: str = "3.5"
    payload_uuid: str = ""
    node_id: str = "dslv-zpdi/mobile-tier2"
    sensor_id: str = ""
    modality: str = ""
    timestamp_utc: float = 0.0
    ingest_monotonic_ns: int = 0
    raw_value: Any = None
    extracted_phases: List[float] = field(default_factory=list)
    gps_locked: bool = False
    pps_jitter_ns: float = float("inf")
    calibration_valid: bool = False
    calibration_age_s: float = 0.0
    drift_percent: float = 0.0
    source_path: str = TERMUX_SENSOR_BIN
    trust_state: str = "ASSEMBLED"
    quarantine_reason: Optional[str] = None
    env_class: Optional[str] = None
    event_window_id: Optional[str] = None
    parent_trigger_id: Optional[str] = None
    payload_checksum: str = ""
    hardware_tier: int = 2
    # Location enrichment (GPS / network / passive)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    accuracy: Optional[float] = None
    location_provider: Optional[str] = None
    location_timestamp: Optional[float] = None

    def validate(self) -> Tuple[str, Optional[str]]:
        """SPEC-005A.2 — Payload Self-Validation (Rev 3.5)

        Returns (trust_state, quarantine_reason).
        KILLED        = structural corruption only.
        SECONDARY_Q   = trust insufficiency (GPS, PPS, calibration).
        ASSEMBLED     = ready for trust gating.
        """
        if not self.node_id or not self.sensor_id or not self.modality:
            return "KILLED", "Missing routing identity"
        if self.payload_uuid == "":
            return "KILLED", "Missing payload_uuid"
        if self.timestamp_utc == 0.0 or not self.gps_locked:
            return "SECONDARY_QUARANTINED", "GPS untrusted — exploratory only"
        if self.pps_jitter_ns > 10_000.0:
            return "SECONDARY_QUARANTINED", "PPS jitter exceeds Tier 1 threshold (10µs)"
        return "ASSEMBLED", None

    def to_json(self) -> Optional[str]:
        """SPEC-005A.3 — Serialization Gate (Rev 3.5)

        Calls validate() first.  KILLED packets are dropped (returns None).
        Otherwise embeds a truncated SHA-256 checksum.
        """
        state, reason = self.validate()
        self.trust_state = state
        if reason:
            self.quarantine_reason = reason
        if state == "KILLED":
            return None
        d = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        raw_json = json.dumps(d, sort_keys=True, default=str)
        self.payload_checksum = hashlib.sha256(raw_json.encode()).hexdigest()[:16]
        d["payload_checksum"] = self.payload_checksum
        return json.dumps(d, default=str)


# SPEC-003A
def build_mobile_payload(sensor_name: str, reading: dict[str, Any], location: dict[str, Any] | None = None) -> IngestionPayload:
    """Translate a single termux-sensor reading into a canonical IngestionPayload.

    Mobile nodes are Tier-2; gps_locked defaults to False and pps_jitter_ns is
    infinite, so validate() will always route to SECONDARY_QUARANTINED unless
    the packet is structurally corrupt (KILLED).

    If *location* is provided and recent, it is embedded and gps_locked may be
    upgraded based on accuracy.
    """
    phases = _build_extracted_phases(sensor_name, reading)
    payload = IngestionPayload(
        payload_uuid=str(uuid.uuid4()),
        sensor_id=sensor_name,
        modality=SENSOR_MODALITY_MAP.get(sensor_name, "unknown"),
        timestamp_utc=time.time(),
        ingest_monotonic_ns=time.monotonic_ns(),
        raw_value=reading,
        extracted_phases=phases,
        source_path=TERMUX_SENSOR_BIN,
        hardware_tier=2,
    )
    if location:
        payload.latitude = location.get("latitude")
        payload.longitude = location.get("longitude")
        payload.altitude = location.get("altitude")
        payload.accuracy = location.get("accuracy")
        payload.location_provider = location.get("provider")
        payload.location_timestamp = location.get("ts")
    return payload


def score_mobile_payload(payload: IngestionPayload) -> CoherencePacket | None:
    """SPEC-006.5/6.6 — Mobile wiring: compute orientation-fused coherence scores.

    Pre-extracted phases from Layer 1 are fed into CoherenceScorer. The raw
    r_local and r_smooth are then weighted by the current orientation-stability
    score from the rotation-vector fusion engine (SPEC-006.6).  r_global is
    left unmodified because it aggregates across the fleet.
    """
    if not payload.extracted_phases:
        # Barometer / reference-only modalities → zero coherence
        return CoherencePacket(
            payload_uuid=payload.payload_uuid,
            node_id=payload.node_id,
            modality=payload.modality,
            r_local=0.0,
            r_smooth=0.0,
            r_global=0.0,
            trust_state="CORE_PROCESSED",
        )
    packet = _coherence_engine.update(payload.__dict__, payload.extracted_phases)
    r_fused, rs_fused, w_orient = apply_orientation_weight(
        packet.r_local, packet.r_smooth, _ORIENTATION
    )
    packet.r_local = r_fused
    packet.r_smooth = rs_fused
    return packet
