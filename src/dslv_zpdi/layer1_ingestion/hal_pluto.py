"""
SPEC-004A.5 | PlutoSDR+ HAL (Rev 4.8.1)
Hardware Abstraction Layer for Analog Devices PlutoSDR / PlutoSDR+ clones.

The PlutoSDR+ integrates an AD936x transceiver and a Zynq-7000 SoC. It can
operate as a Tier 1 source when its external clock input is wired to a
GPS-disciplined 10 MHz reference and its PPS input (or the host PPS via GPIO)
is used for UTC epoch anchoring. Standalone operation with the internal 40 MHz
DCXO is permitted but payloads are quarantined to the secondary stream per
SPEC-005A.
"""

# pylint: disable=duplicate-code

from __future__ import annotations

import time
import uuid

import numpy as np

from dslv_zpdi.core.exceptions import (
    ClockVerificationError,
    DriverUnavailableError,
    HardwareInitializationError,
)

from .hal_base import BaseHAL
from .nmea_stream import NmeaStream
from .payload import IngestionPayload, SensorModality
from .pps_listener import PpsListener

try:
    import iio

    IIO_AVAILABLE = True
except ImportError:
    IIO_AVAILABLE = False


try:
    import SoapySDR

    SOAPYSDR_AVAILABLE = True
except ImportError:
    SOAPYSDR_AVAILABLE = False


class PlutoHAL(BaseHAL):
    """
    SPEC-004A.5.HAL — PlutoSDR+ ingestion logic.

    Hardware Requirements:
    - PlutoSDR or PlutoSDR+ clone (AD9363A/AD9361/AD9364)
    - libiio or SoapyPlutoSDR driver installed on host
    - For Tier 1 trust: GPSDO 10 MHz → Pluto CLKIN, GPSDO 1 PPS → host GPIO
      (or Pluto PPS input if wired and exposed by firmware)

    The AD9363A on the reference PlutoSDR Rev.C supports:
      - RX: 325 MHz – 3.8 GHz
      - TX: 325 MHz – 3.8 GHz
      - Sample rate up to ~30.72 MSPS
    """

    def __init__(
        self,
        uri: str = "ip:192.168.2.1",
        pps_device: str = "/dev/pps0",
        nmea_port: str = "/dev/ttyACM0",
        external_clock: bool = False,
        gain: int = 64,
    ):
        """
        SPEC-004A.5.HAL.INIT — Initialize Pluto HAL.

        Args:
            uri: libiio URI for the Pluto (e.g. ip:192.168.2.1, usb:3.15.5).
            pps_device: Host PPS device for UTC epoch anchoring.
            nmea_port: GPSDO NMEA telemetry port (used when external_clock=True).
            external_clock: Assert that the Pluto is GPSDO-referenced.
                When True, the HAL still cannot read the clock state in software,
                so this is a user assertion backed by wiring and PPS/NMEA checks.
            gain: RX gain in dB (AD9361 manual gain range).
        """
        if not IIO_AVAILABLE and not SOAPYSDR_AVAILABLE:
            raise DriverUnavailableError(
                "No Pluto driver available. Install python3-libiio or SoapyPlutoSDR."
            )

        self.uri = uri
        self.external_clock = external_clock
        self.gain = gain
        self._ctx: iio.Context | None = None
        self._rx_dev: iio.Device | None = None
        self._ad9361: iio.Device | None = None
        self._clock_verified = False

        # Background listeners — shared timing infrastructure with HardwareHAL.
        self._pps = PpsListener(device=pps_device)
        self._pps.start()
        self._nmea = NmeaStream(port=nmea_port)
        self._nmea.start()

        self._init_pluto()

    def _init_pluto(self):
        """
        SPEC-004A.5.HAL.INIT — Open the Pluto context and cache device handles.
        """
        if IIO_AVAILABLE:
            try:
                self._ctx = iio.Context(self.uri)
            except Exception as exc:
                raise HardwareInitializationError(
                    f"Could not open Pluto context at {self.uri}: {exc}"
                ) from exc

            self._ad9361 = self._ctx.find_device("ad9361-phy")
            self._rx_dev = self._ctx.find_device("cf-ad9361-lpc")
            if self._ad9361 is None or self._rx_dev is None:
                raise HardwareInitializationError(
                    "Pluto context missing ad9361-phy or cf-ad9361-lpc device."
                )

            # Enable RX channels I/Q
            chan_i = self._rx_dev.find_channel("voltage0")
            chan_q = self._rx_dev.find_channel("voltage1")
            if chan_i is None or chan_q is None:
                raise HardwareInitializationError(
                    "Pluto RX device missing voltage0/voltage1 channels."
                )
            chan_i.enabled = True
            chan_q.enabled = True

        elif SOAPYSDR_AVAILABLE:
            # Soapy fallback — just verify enumeration; stream opened per-ingest
            try:
                devices = SoapySDR.Device.enumerate("driver=plutosdr")
                if not devices:
                    raise HardwareInitializationError("No PlutoSDR found via SoapySDR.")
            except Exception as exc:
                raise HardwareInitializationError(
                    f"SoapySDR Pluto enumeration failed: {exc}"
                ) from exc

        # If user asserts external clock, verify host-side PPS/NMEA are alive.
        if self.external_clock:
            lock_status = self.verify_tier1_phase_lock()
            if not lock_status["phase_lock_verified"]:
                raise ClockVerificationError(
                    "Pluto external_clock=True but host PPS/NMEA lock not verified. "
                    "Verify GPSDO 10 MHz → Pluto CLKIN and 1 PPS → host GPIO."
                )
            self._clock_verified = True

        print("[+] PlutoHAL initialized.")
        if self.external_clock:
            print("[+] External GPSDO clock asserted. Tier 1 trust path active.")
        else:
            print("[!] Pluto running on internal DCXO. RF payloads will be quarantined.")

    def _apply_rx_params(self, center_freq: float, sample_rate: float):
        """Configure AD9361 RX LO, sample rate, bandwidth, and manual gain."""
        if self._ad9361 is None:
            return

        rx_lo = self._ad9361.find_channel("altvoltage0", True)
        if rx_lo is None:
            raise HardwareInitializationError("Pluto missing altvoltage0/RX_LO channel.")

        rx_lo.attrs["frequency"].value = str(int(center_freq))

        # Set RX channel gain and bandwidth
        rx_chan = self._ad9361.find_channel("voltage0")
        if rx_chan is not None:
            rx_chan.attrs["gain_control_mode"].value = "manual"
            rx_chan.attrs["hardwaregain"].value = str(int(self.gain))
            rx_chan.attrs["rf_bandwidth"].value = str(int(sample_rate * 0.8))
            rx_chan.attrs["sampling_frequency"].value = str(int(sample_rate))

    def verify_tier1_phase_lock(self) -> dict:
        """
        SPEC-004A.5 — Verify host-side GPSDO lock used for Pluto epoch anchoring.

        Returns:
            Dict with lock status, PPS jitter, GPS fix quality, and warnings.
        """
        result: dict = {
            "phase_lock_verified": False,
            "clock_source": "external_wired" if self.external_clock else "internal",
            "driver": "libiio" if IIO_AVAILABLE else ("SoapySDR" if SOAPYSDR_AVAILABLE else "none"),
            "pps_rms_jitter_ns": float("inf"),
            "pps_history_len": 0,
            "gps_fix": False,
            "satellites_used": 0,
            "hdop": 99.9,
            "warnings": [],
        }

        pps_snap = self._pps.snapshot()
        result["pps_rms_jitter_ns"] = pps_snap["rms_jitter_ns"]
        result["pps_history_len"] = pps_snap["history_len"]
        if pps_snap["history_len"] < 2:
            result["warnings"].append(
                f"PPS ring buffer has {pps_snap['history_len']} sample(s) — need ≥2"
            )

        fix = self._nmea.latest()
        result["gps_fix"] = fix["gps_fix"]
        result["satellites_used"] = fix.get("satellites_used", 0)
        result["hdop"] = fix.get("hdop", 99.9)
        if not fix["gps_fix"]:
            result["warnings"].append("NMEA: no GPS fix — GPSDO still acquiring")
        fix_age = time.time() - fix.get("ts", 0.0)
        if fix["ts"] > 0 and fix_age > 10.0:
            result["warnings"].append(f"NMEA fix data is {fix_age:.0f} s stale")

        jitter_ok = result["pps_history_len"] >= 2 and result["pps_rms_jitter_ns"] < 1_000_000.0
        result["phase_lock_verified"] = jitter_ok and result["gps_fix"]
        return result

    def ingest_gps_pps(
        self,
        pps_device: str = "/dev/pps0",
        node_id: str = "PI5-ALPHA",
        sensor_id: str = "GPSDO-01",
        pps_jitter_threshold_ns: float = 10_000.0,
    ) -> IngestionPayload:
        """
        SPEC-005A.4a — GPS/PPS Live Ingestion for Pluto anchor node.

        Reuses the host PPS listener and NMEA stream; the Pluto itself does not
        supply PPS through libiio in standard firmware.
        """
        mono_ns = time.monotonic_ns()
        pps_snap = self._pps.snapshot()
        pps_jitter_ns = pps_snap["rms_jitter_ns"]
        history = pps_snap["history"]

        if history:
            mono_edge_ns, pps_time_ns = history[-1]
            mono_now_ns = time.monotonic_ns()
            raw_delta = mono_now_ns - mono_edge_ns
            pps_offset_ns = float(((raw_delta + 500_000_000) % 1_000_000_000) - 500_000_000)
        else:
            pps_time_ns = 0
            pps_offset_ns = float("inf")

        gps_locked = pps_snap["history_len"] >= 2 and pps_jitter_ns < 1_000_000_000.0
        nmea = self._nmea.latest()
        gps_locked = gps_locked and nmea.get("gps_fix", False)

        payload = IngestionPayload(
            payload_uuid=str(uuid.uuid4()),
            node_id=node_id,
            sensor_id=sensor_id,
            modality=SensorModality.GPS_PPS.value,
            timestamp_utc=time.time(),
            ingest_monotonic_ns=mono_ns,
            raw_value={
                "pps_time_ns": pps_time_ns,
                "pps_offset_ns": pps_offset_ns,
                "source": "gpsdo_leo_bodnar_lbe1421",
                "pps_device": pps_device,
                "lbe1421_native_3v3": True,
                "nmea_telemetry": nmea,
                "sdr_platform": "plutosdr_plus",
            },
            extracted_phases=[],
            gps_locked=gps_locked,
            pps_jitter_ns=pps_jitter_ns,
            calibration_valid=gps_locked and pps_jitter_ns < pps_jitter_threshold_ns,
            calibration_age_s=0.0,
            drift_percent=0.0,
            source_path=pps_device,
            trust_state="ASSEMBLED",
            hardware_tier=1,
        )

        state, reason = payload.validate()
        payload.trust_state = state
        if reason:
            payload.quarantine_reason = reason
        if state == "ASSEMBLED" and gps_locked:
            payload.trust_state = "TIME_TRUSTED"
            if payload.calibration_valid:
                payload.trust_state = "CAL_TRUSTED"

        return payload

    def wait_for_pps_edge(self, pps_device: str = "/dev/pps0", timeout_s: float = 2.0) -> bool:
        """SPEC-004A.4-SYNC — Block until next host PPS edge."""
        return self._pps.wait_for_edge(timeout_s=timeout_s)

    def ingest_sdr(
        self,
        center_freq: float = 100e6,
        sample_rate: float = 2e6,
        num_samples: int = 16384,
        node_id: str = "PI5-ALPHA",
        sensor_id: str = "PLUTO-01",
        gps_locked: bool = True,
        pps_jitter_ns: float = 500.0,
        calibration_valid: bool = True,
    ) -> IngestionPayload:
        """
        SPEC-005A.4b — SDR IQ Live Ingestion for PlutoSDR+.

        Captures IQ samples via libiio. The trust state depends on whether
        external_clock was asserted:
          - external_clock=True  → clock_source="external" → eligible for primary
          - external_clock=False → clock_source="internal" → secondary quarantine
        """
        mono_ns = time.monotonic_ns()
        phases: list[float] = []
        raw_val = {}

        if self.external_clock and not self._clock_verified:
            lock_status = self.verify_tier1_phase_lock()
            if not lock_status["phase_lock_verified"]:
                raise ClockVerificationError(
                    "Cannot ingest: Pluto external clock asserted but PPS/NMEA lock lost."
                )

        if IIO_AVAILABLE and self._ctx is not None:
            raw_val = self._ingest_iio(center_freq, sample_rate, num_samples)
        elif SOAPYSDR_AVAILABLE:
            raw_val = self._ingest_soapy(center_freq, sample_rate, num_samples)
        else:
            raw_val = {
                "error": "No Pluto driver available.",
                "clock_source": "external" if self.external_clock else "internal",
            }

        phases = raw_val.get("phases", [])

        payload = IngestionPayload(
            payload_uuid=str(uuid.uuid4()),
            node_id=node_id,
            sensor_id=sensor_id,
            modality=SensorModality.RF_SDR.value,
            timestamp_utc=time.time(),
            ingest_monotonic_ns=mono_ns,
            raw_value=raw_val,
            extracted_phases=phases,
            gps_locked=gps_locked,
            pps_jitter_ns=pps_jitter_ns,
            calibration_valid=calibration_valid and "error" not in raw_val,
            calibration_age_s=0.0,
            drift_percent=0.0,
            source_path=self.uri,
            trust_state="ASSEMBLED",
            hardware_tier=1,
        )

        state, reason = payload.validate()
        payload.trust_state = state
        if reason:
            payload.quarantine_reason = reason
        if state == "ASSEMBLED" and "error" not in raw_val:
            payload.trust_state = "TIME_TRUSTED"
            if payload.calibration_valid:
                payload.trust_state = "CAL_TRUSTED"

        return payload

    def _ingest_iio(self, center_freq: float, sample_rate: float, num_samples: int) -> dict:
        """libiio-based Pluto ingestion."""
        try:
            self._apply_rx_params(center_freq, sample_rate)
            if self._rx_dev is None:
                raise HardwareInitializationError("Pluto RX device not initialized.")

            buf = iio.Buffer(self._rx_dev, num_samples)
            buf.refill()
            data = buf.read()
            samples = np.frombuffer(data, dtype=np.int16).astype(np.float32).view(np.complex64)

            phases = np.angle(samples).tolist()[:64]

            return {
                "iq_samples": [[float(x.real), float(x.imag)] for x in samples[:64]],
                "center_freq": center_freq,
                "sample_rate": sample_rate,
                "clock_source": "external" if self.external_clock else "internal",
                "clock_locked_to_gpsdo": self.external_clock,
                "bandwidth_mhz": sample_rate / 1e6,
                "phases": phases,
                "driver": "libiio",
                "uri": self.uri,
            }
        except Exception as e:
            return {
                "error": f"libiio acquisition failed: {str(e)}",
                "clock_source": "external" if self.external_clock else "internal",
                "driver": "libiio",
                "uri": self.uri,
            }

    def _ingest_soapy(self, center_freq: float, sample_rate: float, num_samples: int) -> dict:
        """SoapySDR fallback ingestion for Pluto."""
        try:
            sdr = SoapySDR.Device(f"driver=plutosdr,uri={self.uri}")
            sdr.setSampleRate(SoapySDR.SOAPY_SDR_RX, 0, sample_rate)
            sdr.setFrequency(SoapySDR.SOAPY_SDR_RX, 0, center_freq)
            sdr.setGain(SoapySDR.SOAPY_SDR_RX, 0, self.gain)

            rx_stream = sdr.setupStream(SoapySDR.SOAPY_SDR_RX, SoapySDR.SOAPY_SDR_CF32)
            sdr.activateStream(rx_stream)

            buff = np.empty(num_samples, np.complex64)
            sr = sdr.readStream(rx_stream, [buff], num_samples)
            if sr.ret < 0:
                raise RuntimeError(f"SoapySDR readStream error: {SoapySDR.errToStr(sr.ret)}")
            actual = sr.ret
            if actual < num_samples:
                buff = buff[:actual]

            sdr.deactivateStream(rx_stream)
            sdr.closeStream(rx_stream)

            phases = np.angle(buff).tolist()[:64]
            return {
                "iq_samples": [[float(x.real), float(x.imag)] for x in buff[:64]],
                "center_freq": center_freq,
                "sample_rate": sample_rate,
                "clock_source": "external" if self.external_clock else "internal",
                "clock_locked_to_gpsdo": self.external_clock,
                "bandwidth_mhz": sample_rate / 1e6,
                "phases": phases,
                "driver": "SoapySDR",
                "uri": self.uri,
            }
        except Exception as e:
            return {
                "error": f"SoapySDR acquisition failed: {str(e)}",
                "clock_source": "external" if self.external_clock else "internal",
                "driver": "SoapySDR",
                "uri": self.uri,
            }

    def verify_gpsdo_lock(self, device_index: int = 0) -> dict:
        """
        SPEC-004A.3 — Verify Pluto and host GPSDO lock status.

        Args:
            device_index: Ignored; kept for API compatibility with HardwareHAL.

        Returns:
            Dict with lock status and diagnostic information.
        """
        info = {
            "iio_available": IIO_AVAILABLE,
            "soapy_available": SOAPYSDR_AVAILABLE,
            "driver_used": "libiio"
            if IIO_AVAILABLE
            else ("SoapySDR" if SOAPYSDR_AVAILABLE else "none"),
            "phase_lock_verified": False,
            "clock_source": "external" if self.external_clock else "internal",
            "uri": self.uri,
        }

        if IIO_AVAILABLE and self._ctx is not None:
            try:
                info["hw_model"] = self._ctx.attrs.get("hw_model", "unknown")
                info["fw_version"] = self._ctx.attrs.get("fw_version", "unknown")
                info["ad9361_model"] = self._ctx.attrs.get("ad9361-phy,model", "unknown")
                info["pluto_detected"] = True
            except Exception as exc:
                info["pluto_detected"] = False
                info["error"] = str(exc)
        elif SOAPYSDR_AVAILABLE:
            try:
                devices = SoapySDR.Device.enumerate("driver=plutosdr")
                info["pluto_detected"] = len(devices) > 0
                info["devices_found"] = len(devices)
            except Exception as exc:
                info["pluto_detected"] = False
                info["error"] = str(exc)
        else:
            info["pluto_detected"] = False
            info["error"] = "No Pluto driver available."

        lock = self.verify_tier1_phase_lock()
        info.update(lock)
        return info

    def shutdown(self) -> None:
        """Stop background PpsListener and NmeaStream daemon threads."""
        self._pps.stop()
        self._nmea.stop()

    def close(self) -> None:
        """SPEC-005A.HAL — Release timing resources."""
        self.shutdown()
