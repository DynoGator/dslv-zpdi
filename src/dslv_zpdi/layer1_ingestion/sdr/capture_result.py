"""
SPEC-004A | Capture result and SDR health data structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from dslv_zpdi.layer1_ingestion.timing.attestation import ClockAttestation


@dataclass(frozen=True)
class SdrHealth:
    """SPEC-004A.HEALTH — SDR runtime health snapshot."""

    backend_name: str
    uri: str
    reachable: bool
    rx_enabled: bool
    tx_enabled: bool
    temperature_c: float | None = None
    overflow_count: int = 0
    underflow_count: int = 0
    transport_errors: int = 0
    lost_context_count: int = 0
    short_read_count: int = 0
    warnings: tuple[str, ...] = ()

    def summary(self) -> dict[str, Any]:
        return {
            "backend_name": self.backend_name,
            "uri": self.uri,
            "reachable": self.reachable,
            "rx_enabled": self.rx_enabled,
            "tx_enabled": self.tx_enabled,
            "temperature_c": self.temperature_c,
            "overflow_count": self.overflow_count,
            "underflow_count": self.underflow_count,
            "transport_errors": self.transport_errors,
            "lost_context_count": self.lost_context_count,
            "short_read_count": self.short_read_count,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class CaptureResult:
    """
    SPEC-004A.RESULT — Complete capture result with sample accounting.

    IQ samples are stored as a complex64 numpy array. The caller is responsible
    for persisting them; this dataclass carries the raw array plus all metadata.
    """

    samples: np.ndarray
    host_monotonic_start_ns: int
    host_utc_start: float
    host_monotonic_end_ns: int
    host_utc_end: float
    samples_requested: int
    samples_received: int
    sequence_or_buffer_counters: tuple[int, ...] = ()
    overflow_indicators: tuple[bool, ...] = ()
    underflow_indicators: tuple[bool, ...] = ()
    transport_errors: tuple[str, ...] = ()
    capture_duration_s: float = 0.0
    effective_sample_rate_sps: float = 0.0
    center_frequency_hz: int = 0
    rf_bandwidth_hz: int = 0
    gain_settings_db: tuple[float, ...] = ()
    device_temperature_c: float | None = None
    clock_attestation: ClockAttestation | None = None
    configuration_hash: str = ""
    backend_name: str = ""
    uri: str = ""

    @property
    def sample_loss(self) -> int:
        """Return unaccounted missing samples (negative if extra)."""
        return self.samples_requested - self.samples_received

    @property
    def has_unaccounted_loss(self) -> bool:
        """Return True if any samples are missing."""
        return self.sample_loss > 0

    def summary(self) -> dict[str, Any]:
        return {
            "samples_shape": list(self.samples.shape),
            "samples_dtype": str(self.samples.dtype),
            "host_monotonic_start_ns": self.host_monotonic_start_ns,
            "host_utc_start": self.host_utc_start,
            "host_monotonic_end_ns": self.host_monotonic_end_ns,
            "host_utc_end": self.host_utc_end,
            "samples_requested": self.samples_requested,
            "samples_received": self.samples_received,
            "sample_loss": self.sample_loss,
            "sequence_or_buffer_counters": list(self.sequence_or_buffer_counters),
            "overflow_indicators": list(self.overflow_indicators),
            "underflow_indicators": list(self.underflow_indicators),
            "transport_errors": list(self.transport_errors),
            "capture_duration_s": self.capture_duration_s,
            "effective_sample_rate_sps": self.effective_sample_rate_sps,
            "center_frequency_hz": self.center_frequency_hz,
            "rf_bandwidth_hz": self.rf_bandwidth_hz,
            "gain_settings_db": list(self.gain_settings_db),
            "device_temperature_c": self.device_temperature_c,
            "clock_attestation": self.clock_attestation.summary() if self.clock_attestation else None,
            "configuration_hash": self.configuration_hash,
            "backend_name": self.backend_name,
            "uri": self.uri,
        }
