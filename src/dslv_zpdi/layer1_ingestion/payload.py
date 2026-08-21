"""
SPEC-005A | Trust Tier: Ingested (Layer 1 Payload Contract)
Hardware-anchored ingestion payload with full SHA-256 attestation.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from dslv_zpdi.core.states import TrustState


class SensorModality(Enum):
    """SPEC-005A.1 — Authorized sensor modalities per Section 5.3."""

    RF_SDR = "rf_sdr"
    GPS_PPS = "gps_pps"
    THERMAL = "thermal"
    ACOUSTIC = "acoustic"
    MAGNETOMETER = "magnetometer"
    INERTIAL = "inertial"
    RADON = "radon"
    ACCEL = "accel"
    BAROMETER = "barometer"
    GYROSCOPE = "gyroscope"
    ROTATION_VECTOR = "rotation_vector"
    GEOMAGNETIC_ROTATION = "geomagnetic_rotation"
    GRAVITY = "gravity"


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
    raw_value: dict[str, Any] = field(default_factory=dict)
    extracted_phases: list[float] = field(default_factory=list)
    gps_locked: bool = False
    pps_jitter_ns: float = 0.0
    calibration_valid: bool = False
    calibration_age_s: float = 0.0
    drift_percent: float = 0.0
    source_path: str = ""
    hardware_tier: int = 1
    trust_state: str = TrustState.ASSEMBLED.value
    quarantine_reason: str | None = None
    schema_version: str = "4.0"
    payload_checksum: str = ""
    checksum_algo: str = "blake2b"

    # Define binary struct format for zero-copy routing
    # d: timestamp_utc
    # Q: ingest_monotonic_ns
    # d: pps_jitter_ns
    # d: calibration_age_s
    # d: drift_percent
    # 32s: payload_uuid
    # 16s: node_id
    # 16s: sensor_id
    # 16s: modality
    # B: flags
    _STRUCT_FMT = "<d Q d d d 32s 16s 16s 16s B"
    _struct = struct.Struct(_STRUCT_FMT)

    def validate(self) -> tuple[str, str | None]:
        """SPEC-003 / SPEC-005A.3 — Validate packet trust state."""
        if not all([self.node_id, self.sensor_id, self.modality]):
            return TrustState.KILLED.value, "missing_identity"

        try:
            SensorModality(self.modality)
        except ValueError:
            return TrustState.KILLED.value, "invalid_modality"

        if self.schema_version not in ("3.1", "3.2", "4.0"):
            return TrustState.SECONDARY_QUARANTINED.value, "schema_version_mismatch"

        if self.schema_version != "4.0" and not isinstance(self.raw_value, dict):
            return TrustState.SECONDARY_QUARANTINED.value, "raw_value_not_dict"

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

    def to_binary(self) -> bytes:
        """SPEC-005A.5 — Pack core telemetry into fixed binary struct and append IQ buffer."""
        flags = 0
        if self.gps_locked:
            flags |= 1 << 0
        if self.calibration_valid:
            flags |= 1 << 1

        # Pack structured header
        header = self._struct.pack(
            self.timestamp_utc,
            self.ingest_monotonic_ns,
            self.pps_jitter_ns,
            self.calibration_age_s,
            self.drift_percent,
            self.payload_uuid.encode()[:32].ljust(32, b"\0"),
            self.node_id.encode()[:16].ljust(16, b"\0"),
            self.sensor_id.encode()[:16].ljust(16, b"\0"),
            self.modality.encode()[:16].ljust(16, b"\0"),
            flags,
        )

        iq_bytes = b""
        if isinstance(self.raw_value, dict) and "iq_samples" in self.raw_value:
            # We assume iq_samples could already be bytes or numpy arrays in the future,
            # but for now if it's a list, we pack it fast or leave it as bytes
            iq = self.raw_value["iq_samples"]
            if isinstance(iq, list):
                # Flatten the list of complex floats
                import itertools

                flat = list(itertools.chain.from_iterable(iq))
                iq_bytes = struct.pack(f"<{len(flat)}f", *flat)
            elif isinstance(iq, bytes):
                iq_bytes = iq
            # Remove IQ from raw_value for downstream if it is a list
            # We don't deep copy the whole thing, just store the checksum.
            self.raw_value["iq_digest"] = hashlib.blake2b(iq_bytes, digest_size=32).hexdigest()
            # Retain a small preview for debug
            if isinstance(iq, list):
                self.raw_value["iq_preview"] = iq[:32]
            del self.raw_value["iq_samples"]

        # Append IQ payload to the header
        full_payload = header + iq_bytes
        self.payload_checksum = hashlib.blake2b(full_payload, digest_size=32).hexdigest()

        return full_payload
