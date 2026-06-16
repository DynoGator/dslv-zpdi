"""
SPEC-004A | Typed capability and configuration models for SDR backends.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SdrCapabilities:
    """SPEC-004A.CAP — Runtime-discovered SDR capabilities."""

    backend_name: str
    uri: str
    transport: str  # 'iio', 'usb', 'ethernet', 'soapy', 'simulated'
    model: str
    firmware_version: str
    fpga_version: str = ""
    serial_number: str = ""
    mac_address: str | None = None
    rx_channel_count: int = 1
    tx_channel_count: int = 0
    rx_lo_range_hz: tuple[int, int] = (0, 0)
    tx_lo_range_hz: tuple[int, int] = (0, 0)
    max_sample_rate_sps: int = 0
    available_sample_rates_sps: tuple[int, ...] = ()
    available_bandwidths_hz: tuple[int, ...] = ()
    gain_modes: tuple[str, ...] = ()
    supports_external_clock: bool = False
    external_clock_frequency_hz: int | None = None
    raw_attrs: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "backend_name": self.backend_name,
            "uri": self.uri,
            "transport": self.transport,
            "model": self.model,
            "firmware_version": self.firmware_version,
            "fpga_version": self.fpga_version,
            "serial_number": self.serial_number,
            "mac_address": self.mac_address,
            "rx_channel_count": self.rx_channel_count,
            "tx_channel_count": self.tx_channel_count,
            "rx_lo_range_hz": self.rx_lo_range_hz,
            "tx_lo_range_hz": self.tx_lo_range_hz,
            "max_sample_rate_sps": self.max_sample_rate_sps,
            "available_sample_rates_sps": list(self.available_sample_rates_sps),
            "available_bandwidths_hz": list(self.available_bandwidths_hz),
            "gain_modes": list(self.gain_modes),
            "supports_external_clock": self.supports_external_clock,
            "external_clock_frequency_hz": self.external_clock_frequency_hz,
        }


@dataclass(frozen=True)
class CaptureProfile:
    """SPEC-004A.PROF — Canonical capture request profile."""

    center_frequency_hz: int
    sample_rate_sps: int
    bandwidth_hz: int
    gain_db: float
    gain_mode: str = "manual"
    receive_channels: tuple[int, ...] = (0,)
    transmit_enabled: bool = False
    buffer_samples: int = 262_144
    duration_seconds: float | None = None
    num_samples: int | None = None
    external_clock_configured: bool = False
    requested_reference_frequency_hz: int | None = None

    def configuration_hash_input(self) -> dict[str, Any]:
        """Return a canonical dict suitable for SHA-256 hashing."""
        return {
            "center_frequency_hz": self.center_frequency_hz,
            "sample_rate_sps": self.sample_rate_sps,
            "bandwidth_hz": self.bandwidth_hz,
            "gain_db": self.gain_db,
            "gain_mode": self.gain_mode,
            "receive_channels": list(self.receive_channels),
            "transmit_enabled": self.transmit_enabled,
            "buffer_samples": self.buffer_samples,
            "external_clock_configured": self.external_clock_configured,
            "requested_reference_frequency_hz": self.requested_reference_frequency_hz,
        }


@dataclass(frozen=True)
class AppliedConfiguration:
    """SPEC-004A.APPLIED — Settings actually applied by the hardware."""

    center_frequency_hz: int
    sample_rate_sps: int
    bandwidth_hz: int
    gain_db: float
    gain_mode: str
    receive_channels: tuple[int, ...]
    transmit_enabled: bool
    external_clock_configured: bool
    configuration_hash: str

    def matches(self, requested: CaptureProfile) -> bool:
        """Return True if applied settings match the requested profile within tolerance."""
        return (
            self.center_frequency_hz == requested.center_frequency_hz
            and self.sample_rate_sps == requested.sample_rate_sps
            and self.bandwidth_hz == requested.bandwidth_hz
            and abs(self.gain_db - requested.gain_db) < 0.5
            and self.gain_mode == requested.gain_mode
            and self.receive_channels == requested.receive_channels
            and self.transmit_enabled == requested.transmit_enabled
        )
