"""
SPEC-004A.SIM — Simulated SDR backend for CI and development.

This backend does not require any hardware drivers. It is deterministic and
supports configurable fault injection for unit tests. It must be explicitly
selected; it is never used as a silent fallback in field mode.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable

import numpy as np

from dslv_zpdi.layer1_ingestion.sdr.base import SdrBackend
from dslv_zpdi.layer1_ingestion.sdr.capture_result import CaptureResult, SdrHealth
from dslv_zpdi.layer1_ingestion.sdr.capabilities import (
    AppliedConfiguration,
    CaptureProfile,
    SdrCapabilities,
)
from dslv_zpdi.layer1_ingestion.timing.attestation import ClockAttestation


class SimulatedSdrBackend(SdrBackend):
    """
    SPEC-004A.SIM — Deterministic simulated SDR backend.

    Args:
        seed: Deterministic seed for sample generation.
        sample_loss_hook: Optional callable(profile) -> int to simulate short reads.
        fault_hook: Optional callable(profile) -> Exception to raise during capture.
    """

    def __init__(
        self,
        seed: int = 42,
        sample_loss_hook: Callable[[CaptureProfile], int] | None = None,
        fault_hook: Callable[[CaptureProfile], Exception] | None = None,
    ) -> None:
        self.seed = seed
        self._rng = np.random.default_rng(seed)
        self._sample_loss_hook = sample_loss_hook
        self._fault_hook = fault_hook
        self._caps = SdrCapabilities(
            backend_name="simulated",
            uri="sim:",
            transport="simulated",
            model="Simulated AD9363",
            firmware_version="sim",
            rx_channel_count=1,
            tx_channel_count=0,
            rx_lo_range_hz=(70_000_000, 6_000_000_000),
            max_sample_rate_sps=30_720_000,
            available_sample_rates_sps=(2_000_000, 5_000_000, 10_000_000, 20_000_000),
            supports_external_clock=True,
            external_clock_frequency_hz=10_000_000,
        )
        self._applied: AppliedConfiguration | None = None
        self._capture_count = 0

    @property
    def backend_name(self) -> str:
        return "simulated"

    def discover(self) -> SdrCapabilities:
        """SPEC-004A.SIM — Return simulated capabilities."""
        return self._caps

    def configure(self, profile: CaptureProfile) -> AppliedConfiguration:
        """SPEC-004A.SIM — Accept the requested profile."""
        applied = AppliedConfiguration(
            center_frequency_hz=profile.center_frequency_hz,
            sample_rate_sps=profile.sample_rate_sps,
            bandwidth_hz=profile.bandwidth_hz,
            gain_db=profile.gain_db,
            gain_mode=profile.gain_mode,
            receive_channels=profile.receive_channels,
            transmit_enabled=False,
            external_clock_configured=profile.external_clock_configured,
            configuration_hash=self._configuration_hash(profile),
        )
        self._applied = applied
        return applied

    @staticmethod
    def _configuration_hash(profile: CaptureProfile) -> str:
        canonical = json.dumps(profile.configuration_hash_input(), sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def verify_clocking(self) -> ClockAttestation:
        """SPEC-004A.SIM — Return simulated clock attestation."""
        configured = self._applied.external_clock_configured if self._applied else False
        return ClockAttestation(
            external_reference_configured=configured,
            external_reference_detected=configured,
            reference_frequency_hz=10_000_000 if configured else None,
            baseband_pll_locked=configured,
            rx_rf_pll_locked=configured,
            tx_rf_pll_locked=None,
            sample_epoch_synchronized=configured,
            inter_node_sample_phase_synchronized=False,
            rf_phase_synchronized=False,
            evidence={"simulated": True},
            warnings=("Simulated backend: not institutional field data",),
        )

    def capture(self, request: CaptureProfile) -> CaptureResult:
        """SPEC-004A.SIM — Generate deterministic complex baseband samples."""
        if self._fault_hook is not None:
            raise_exc = self._fault_hook(request)
            if raise_exc is not None:
                raise raise_exc

        applied = self.configure(request)
        num_samples = request.num_samples or request.buffer_samples

        # Simulate a tone + noise
        t = np.arange(num_samples) / request.sample_rate_sps
        tone = np.exp(2j * np.pi * 100_000 * t).astype(np.complex64)
        noise = (self._rng.normal(0, 0.01, num_samples) +
                 1j * self._rng.normal(0, 0.01, num_samples)).astype(np.complex64)
        samples = tone + noise

        sample_loss = 0
        if self._sample_loss_hook is not None:
            sample_loss = self._sample_loss_hook(request)
        if sample_loss > 0:
            samples = samples[:-sample_loss]

        self._capture_count += 1
        mono_start = time.monotonic_ns()
        utc_start = time.time()
        mono_end = time.monotonic_ns()
        utc_end = time.time()

        return CaptureResult(
            samples=samples,
            host_monotonic_start_ns=mono_start,
            host_utc_start=utc_start,
            host_monotonic_end_ns=mono_end,
            host_utc_end=utc_end,
            samples_requested=num_samples,
            samples_received=len(samples),
            capture_duration_s=(mono_end - mono_start) / 1e9,
            effective_sample_rate_sps=request.sample_rate_sps,
            center_frequency_hz=applied.center_frequency_hz,
            rf_bandwidth_hz=applied.bandwidth_hz,
            gain_settings_db=(applied.gain_db,),
            clock_attestation=self.verify_clocking(),
            configuration_hash=applied.configuration_hash,
            backend_name=self.backend_name,
            uri="sim:",
        )

    def health(self) -> SdrHealth:
        """SPEC-004A.SIM — Return simulated health."""
        return SdrHealth(
            backend_name=self.backend_name,
            uri="sim:",
            reachable=True,
            rx_enabled=True,
            tx_enabled=False,
            warnings=("simulated",),
        )

    def close(self) -> None:
        """SPEC-004A.SIM — No-op close."""
        pass
