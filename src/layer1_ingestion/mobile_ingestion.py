"""
SPEC-005A.4 — Mobile Layer 1 Ingestion Driver (Rev 3.1)

Wraps termux-sensor streaming output and produces canonical
IngestionPayload objects for the three-layer pipeline.

Phase extraction (Hilbert transform) is performed HERE in Layer 1
per SPEC-005.  Mobile has no GPS/PPS hardware, so all packets are
inherently SECONDARY_QUARANTINED at trust-state validation.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

import numpy as np

from src.layer2_core.coherence import CoherenceScorer, CoherencePacket

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
)

# Sensor name → canonical modality string
SENSOR_MODALITY_MAP = {
    "ICM45631 Accelerometer": "accel",
    "MMC5616 Magnetometer": "magnetometer",
    "ICP20100 Pressure Sensor": "barometer",
}

# Rolling window size for Hilbert phase extraction
PHASE_WINDOW = 32


# ---------------------------------------------------------------------------
# Lightweight Hilbert transform (numpy-only, no scipy dependency)
# ---------------------------------------------------------------------------
def _hilbert_phases(signal: np.ndarray) -> List[float]:
    """Return instantaneous phases of the analytic signal via FFT."""
    if len(signal) < 4:
        return []
    n = len(signal)
    # Pad to next power of two for cleaner FFT
    fft_size = 1 << (n - 1).bit_length()
    padded = np.zeros(fft_size, dtype=np.float64)
    padded[:n] = signal
    spec = np.fft.fft(padded)
    # Zero negative frequencies, double positive
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
class _PhaseBuffers:
    def __init__(self, window: int = PHASE_WINDOW):
        self._bufs: dict[str, List[float]] = {}
        self._window = window

    def push(self, sensor: str, value: float) -> List[float]:
        buf = self._bufs.setdefault(sensor, [])
        buf.append(value)
        if len(buf) > self._window:
            buf.pop(0)
        return _hilbert_phases(np.array(buf, dtype=np.float64))


_PHASE_BUFFERS = _PhaseBuffers()


# ---------------------------------------------------------------------------
# Payload construction helpers
# ---------------------------------------------------------------------------
def _extract_magnitude(reading: dict[str, Any]) -> float:
    """Compute vector magnitude for accelerometer / magnetometer samples."""
    x = reading.get("x", 0.0)
    y = reading.get("y", 0.0)
    z = reading.get("z", 0.0)
    return math.sqrt(x * x + y * y + z * z)


def _build_extracted_phases(sensor_name: str, reading: dict[str, Any]) -> List[float]:
    """Layer 1 phase extraction per SPEC-005.

    * Accelerometer  → magnitude vector → Hilbert → phases
    * Magnetometer   → magnitude vector → Hilbert → phases
    * Pressure       → reference-only  → [] (no phase vector)
    """
    modality = SENSOR_MODALITY_MAP.get(sensor_name, "unknown")
    if modality in ("accel", "magnetometer"):
        mag = _extract_magnitude(reading)
        return _PHASE_BUFFERS.push(sensor_name, mag)
    # barometer / unknown → no phase vector
    return []


# ---------------------------------------------------------------------------
# Hardened IngestionPayload — SPEC-005A.1b (Rev 3.1)
# ---------------------------------------------------------------------------
@dataclass
class IngestionPayload:
    """SPEC-005A.1b — Hardened Universal Payload (Rev 3.1)"""
    spec_id: str = "SPEC-005A.1b"
    schema_version: str = "3.1"
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

    def validate(self) -> Tuple[str, Optional[str]]:
        """SPEC-005A.2 — Payload Self-Validation (Rev 3.1)

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
        """SPEC-005A.3 — Serialization Gate (Rev 3.1)

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


def build_mobile_payload(sensor_name: str, reading: dict[str, Any]) -> IngestionPayload:
    """Translate a single termux-sensor reading into a canonical IngestionPayload.

    Mobile nodes are Tier-2; gps_locked is always False and pps_jitter_ns is
    infinite, so validate() will always route to SECONDARY_QUARANTINED unless
    the packet is structurally corrupt (KILLED).
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
    return payload


def score_mobile_payload(payload: IngestionPayload) -> CoherencePacket | None:
    """SPEC-006.5 — Mobile wiring: compute coherence scores for Tier-2 packets.

    Pre-extracted phases from Layer 1 are fed directly into the
    CoherenceScorer.  r_global will be zero for a single-node deployment.
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
    return _coherence_engine.update(payload.__dict__, payload.extracted_phases)
