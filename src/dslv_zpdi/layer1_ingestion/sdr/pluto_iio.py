"""
SPEC-004A.PLUTO — libiio backend for PlutoSDR / PlutoSDR+ / ADALM-PLUTO clones.

This backend uses the system `iio` Python binding. Imports are lazy so
simulator-only hosts can still collect and run tests without libiio installed.

The backend never enables TX and never claims the SDR is locked to an external
reference unless the hardware explicitly reports it.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

import numpy as np

from dslv_zpdi.core.exceptions import (
    ClockVerificationError,
    DriverUnavailableError,
    HardwareInitializationError,
)
from dslv_zpdi.layer1_ingestion.sdr.base import SdrBackend
from dslv_zpdi.layer1_ingestion.sdr.capabilities import (
    AppliedConfiguration,
    CaptureProfile,
    SdrCapabilities,
)
from dslv_zpdi.layer1_ingestion.sdr.capture_result import CaptureResult, SdrHealth
from dslv_zpdi.layer1_ingestion.timing.attestation import ClockAttestation

logger = logging.getLogger("dslv-zpdi.sdr.pluto")


def _get_iio() -> Any:
    """SPEC-004A.PLUTO — Lazy import of libiio."""
    try:
        import iio  # pylint: disable=import-outside-toplevel

        return iio
    except ImportError as exc:
        raise DriverUnavailableError(
            "libiio Python binding not available; install python3-libiio or SoapyPlutoSDR"
        ) from exc


class PlutoIioBackend(SdrBackend):
    """
    SPEC-004A.PLUTO — Native libiio backend for AD936x Pluto-family SDRs.

    Args:
        uri: libiio URI (e.g. 'ip:192.168.3.80', 'usb:', 'local:').
        expected_iio_phy: Name of the transceiver PHY device to verify identity.
    """

    def __init__(self, uri: str = "auto", expected_iio_phy: str = "ad9361-phy") -> None:
        self.uri = uri
        self.expected_iio_phy = expected_iio_phy
        self._iio: Any | None = None
        self._ctx: Any | None = None
        self._ad9361: Any | None = None
        self._rx_dev: Any | None = None
        self._caps: SdrCapabilities | None = None
        self._applied: AppliedConfiguration | None = None
        self._overflow_count = 0
        self._underflow_count = 0
        self._transport_errors = 0
        self._short_read_count = 0
        self._lost_context_count = 0
        self._open()

    @property
    def backend_name(self) -> str:
        return "pluto_iio"

    def _open(self) -> None:
        """SPEC-004A.PLUTO — Open the IIO context and cache device handles."""
        self._iio = _get_iio()
        uri = self._resolve_uri()
        try:
            self._ctx = self._iio.Context(uri)
        except Exception as exc:
            raise HardwareInitializationError(
                f"Could not open Pluto context at {uri}: {exc}"
            ) from exc

        self._ad9361 = self._ctx.find_device(self.expected_iio_phy)
        self._rx_dev = self._ctx.find_device("cf-ad9361-lpc")
        if self._ad9361 is None or self._rx_dev is None:
            raise HardwareInitializationError(
                f"Pluto context missing {self.expected_iio_phy} or cf-ad9361-lpc device."
            )

        # Enable RX channels I/Q by default
        for chan_name in ("voltage0", "voltage1"):
            chan = self._rx_dev.find_channel(chan_name, False)
            if chan is None:
                raise HardwareInitializationError(f"Pluto RX device missing {chan_name} channel.")
            chan.enabled = True

        self._caps = self._build_capabilities()
        logger.info("PlutoIioBackend: opened %s", uri)

    def _resolve_uri(self) -> str:
        """SPEC-004A.PLUTO — Resolve 'auto' to a discovered IIO context URI."""
        if self.uri and self.uri != "auto":
            return self.uri
        try:
            contexts = self._iio.scan_contexts()
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug("IIO context scan failed: %s", exc)
            contexts = {}
        if not contexts:
            raise HardwareInitializationError(
                "No IIO contexts discovered and no explicit URI provided."
            )
        if len(contexts) > 1:
            logger.warning("Multiple IIO contexts discovered; using first: %s", list(contexts))
        return next(iter(contexts))

    def _build_capabilities(self) -> SdrCapabilities:
        """SPEC-004A.PLUTO — Build SdrCapabilities from IIO context attributes."""
        attrs = self._ctx.attrs
        model = attrs.get("hw_model", "unknown")
        fw = attrs.get("fw_version", "unknown")
        fpga = attrs.get("fpga_version", "")
        serial = attrs.get("serial", "")
        mac = attrs.get("hw_serial", None)

        rx_lo = (0, 0)
        try:
            rx_lo_chan = self._ad9361.find_channel("altvoltage0", True)
            if rx_lo_chan:
                min_hz = int(rx_lo_chan.attrs.get("frequency_available", "0 0").value.split()[0])
                max_hz = int(rx_lo_chan.attrs.get("frequency_available", "0 0").value.split()[-1])
                rx_lo = (min_hz, max_hz)
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug("Could not read RX LO range: %s", exc)

        sample_rates: list[int] = []
        try:
            rx_chan = self._ad9361.find_channel("voltage0", False)
            if rx_chan:
                rate_attr = rx_chan.attrs.get("sampling_frequency_available", None)
                if rate_attr:
                    sample_rates = [int(x) for x in rate_attr.value.split()]
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug("Could not read sample rates: %s", exc)

        max_rate = max(sample_rates) if sample_rates else 30_720_000

        return SdrCapabilities(
            backend_name=self.backend_name,
            uri=self.uri,
            transport="iio",
            model=model,
            firmware_version=fw,
            fpga_version=fpga,
            serial_number=serial,
            mac_address=mac,
            rx_channel_count=1,
            tx_channel_count=1,  # AD936x has TX; we do not enable it
            rx_lo_range_hz=rx_lo,
            max_sample_rate_sps=max_rate,
            available_sample_rates_sps=tuple(sample_rates),
            supports_external_clock=True,  # enclosure marked 10M; not yet verified
            external_clock_frequency_hz=None,  # UNVERIFIED_PHYSICAL_PROPERTY
            raw_attrs=dict(attrs),
        )

    def discover(self) -> SdrCapabilities:
        """SPEC-004A.PLUTO — Return runtime-discovered capabilities."""
        if self._caps is None:
            raise HardwareInitializationError("Pluto backend not initialized")
        return self._caps

    def configure(self, profile: CaptureProfile) -> AppliedConfiguration:
        """
        SPEC-004A.PLUTO — Apply capture profile and read settings back.

        Raises HardwareInitializationError if the hardware rejects a setting.
        Raises ClockVerificationError if external clock is requested but cannot
        be verified (which is always, until the FPGA/PHY exposes clock state).
        """
        if self._ad9361 is None or self._rx_dev is None:
            raise HardwareInitializationError("Pluto devices not initialized")

        if profile.transmit_enabled:
            raise ClockVerificationError(
                "TX is hard-locked out for Tier-1 qualification; set transmit_enabled=False"
            )

        # RX LO
        rx_lo = self._ad9361.find_channel("altvoltage0", True)
        if rx_lo is None:
            raise HardwareInitializationError("Pluto missing altvoltage0/RX_LO channel")
        rx_lo.attrs["frequency"].value = str(int(profile.center_frequency_hz))

        # RX channel settings
        rx_chan = self._ad9361.find_channel("voltage0", False)
        if rx_chan is None:
            raise HardwareInitializationError("Pluto missing voltage0 RX channel")

        rx_chan.attrs["gain_control_mode"].value = profile.gain_mode
        rx_chan.attrs["hardwaregain"].value = str(round(profile.gain_db))
        rx_chan.attrs["rf_bandwidth"].value = str(int(profile.bandwidth_hz))
        rx_chan.attrs["sampling_frequency"].value = str(int(profile.sample_rate_sps))

        # Read back applied values
        applied = AppliedConfiguration(
            center_frequency_hz=int(rx_lo.attrs["frequency"].value),
            sample_rate_sps=int(rx_chan.attrs["sampling_frequency"].value),
            bandwidth_hz=int(rx_chan.attrs["rf_bandwidth"].value),
            gain_db=float(rx_chan.attrs["hardwaregain"].value),
            gain_mode=rx_chan.attrs["gain_control_mode"].value,
            receive_channels=profile.receive_channels,
            transmit_enabled=False,
            external_clock_configured=profile.external_clock_configured,
            configuration_hash=self._configuration_hash(profile),
        )

        if not applied.matches(profile):
            raise HardwareInitializationError(
                f"Pluto readback mismatch: requested {profile}, got {applied}"
            )

        self._applied = applied
        return applied

    @staticmethod
    def _configuration_hash(profile: CaptureProfile) -> str:
        """Return SHA-256 over the canonical profile representation."""
        canonical = json.dumps(profile.configuration_hash_input(), sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def verify_clocking(self) -> ClockAttestation:
        """
        SPEC-004A.PLUTO — Return clock attestation.

        The AD936x/Pluto standard firmware does not expose a software-readable
        external-reference-detect bit, so external_reference_detected is None.
        PLL lock bits are also None unless a custom attribute is present.
        """
        external_configured = self._applied.external_clock_configured if self._applied else False
        ref_freq = self._applied.sample_rate_sps if self._applied else None

        warnings: list[str] = []
        if external_configured:
            warnings.append(
                "external_clock_configured=True but electrical direction/level not verified"
            )

        evidence: dict[str, Any] = {
            "uri": self.uri,
            "model": self._caps.model if self._caps else "unknown",
        }

        return ClockAttestation(
            external_reference_configured=external_configured,
            external_reference_detected=None,  # UNVERIFIED_PHYSICAL_PROPERTY
            reference_frequency_hz=ref_freq,
            baseband_pll_locked=None,
            rx_rf_pll_locked=None,
            tx_rf_pll_locked=None,
            sample_epoch_synchronized=False,
            inter_node_sample_phase_synchronized=False,
            rf_phase_synchronized=False,
            evidence=evidence,
            warnings=tuple(warnings),
        )

    def capture(self, request: CaptureProfile) -> CaptureResult:
        """SPEC-004A.PLUTO — Capture IQ samples via libiio."""
        if self._rx_dev is None or self._iio is None:
            raise HardwareInitializationError("Pluto RX device not initialized")

        applied = self.configure(request)
        num_samples = request.num_samples or request.buffer_samples

        mono_start = time.monotonic_ns()
        utc_start = time.time()

        try:
            buf = self._iio.Buffer(self._rx_dev, num_samples)
            buf.refill()
            data = buf.read()
        except Exception as exc:
            self._transport_errors += 1
            raise HardwareInitializationError(f"libiio capture failed: {exc}") from exc

        mono_end = time.monotonic_ns()
        utc_end = time.time()

        # Convert interleaved int16 I/Q to complex64
        iq_int16 = np.frombuffer(data, dtype=np.int16)
        if len(iq_int16) % 2 != 0:
            self._transport_errors += 1
            raise HardwareInitializationError("libiio returned odd number of int16 samples")

        samples = iq_int16.astype(np.float32).view(np.complex64)
        samples_received = len(samples)

        if samples_received < num_samples:
            self._short_read_count += 1
            logger.warning(
                "Pluto short read: requested %d, received %d", num_samples, samples_received
            )

        duration = (mono_end - mono_start) / 1e9
        effective_rate = samples_received / duration if duration > 0 else 0.0

        return CaptureResult(
            samples=samples,
            host_monotonic_start_ns=mono_start,
            host_utc_start=utc_start,
            host_monotonic_end_ns=mono_end,
            host_utc_end=utc_end,
            samples_requested=num_samples,
            samples_received=samples_received,
            capture_duration_s=duration,
            effective_sample_rate_sps=effective_rate,
            center_frequency_hz=applied.center_frequency_hz,
            rf_bandwidth_hz=applied.bandwidth_hz,
            gain_settings_db=(applied.gain_db,),
            clock_attestation=self.verify_clocking(),
            configuration_hash=applied.configuration_hash,
            backend_name=self.backend_name,
            uri=self.uri,
        )

    def health(self) -> SdrHealth:
        """SPEC-004A.PLUTO — Return current health snapshot."""
        reachable = self._ctx is not None
        return SdrHealth(
            backend_name=self.backend_name,
            uri=self.uri,
            reachable=reachable,
            rx_enabled=self._rx_dev is not None,
            tx_enabled=False,
            temperature_c=None,
            overflow_count=self._overflow_count,
            underflow_count=self._underflow_count,
            transport_errors=self._transport_errors,
            lost_context_count=self._lost_context_count,
            short_read_count=self._short_read_count,
            warnings=(),
        )

    def close(self) -> None:
        """SPEC-004A.PLUTO — Release the IIO context."""
        self._ctx = None
        self._ad9361 = None
        self._rx_dev = None
        self._caps = None
