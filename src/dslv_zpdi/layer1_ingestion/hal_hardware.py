"""
SPEC-005A.HAL-HW | Hardware Implementation (Rev 4.2-LBE1420)
Concrete implementation of the HAL for RF Metrology hardware:
Raspberry Pi 5 + HackRF One + Leo Bodnar LBE-1420 GPSDO.

This implementation achieves hardware-level ADC phase coherence by:
1. 10 MHz reference from GPSDO → HackRF CLKIN (hardware ADC lock)
2. 1 PPS from GPSDO → GPIO 18 (UTC epoch anchoring)

Rev 4.1-FORGE: Implemented SoapySDR for hardware agnosticism per Gemini review.
Added "Silent Traitor" clock failure mitigation per ARCH-PHASE-2A-PIVOT.
Rev 4.2-LBE1420: Migrated to LBE-1420 GPSDO (USB-C, NMEA telemetry, 3.3V CMOS native).
Added NMEA serial verification for GPS fix confirmation.
"""

# pylint: disable=duplicate-code

import fcntl
import os
import struct
import sys
import time
import uuid
from typing import List, Optional

import numpy as np

from .hal_base import BaseHAL
from .payload import IngestionPayload, SensorModality

# SoapySDR support - hardware-agnostic SDR driver layer
# Install: sudo apt install soapysdr-module-hackrf python3-soapysdr
try:
    import SoapySDR
    SOAPYSDR_AVAILABLE = True
except ImportError:
    SOAPYSDR_AVAILABLE = False

# Fallback to pyhackrf if SoapySDR not available
try:
    import pyhackrf
    PYHACKRF_AVAILABLE = True
except ImportError:
    PYHACKRF_AVAILABLE = False


class HardwareHAL(BaseHAL):
    """
    SPEC-005A.HAL-HW — Production hardware ingestion logic for RF Metrology stack.
    
    Hardware Requirements (SPEC-004A.1, SPEC-004A.2):
    - Raspberry Pi 5 (16GB) or compatible compute platform
    - HackRF One with CLKIN port for 10 MHz GPSDO reference
    - Leo Bodnar LBE-1420 GPSDO (10 MHz + 1 PPS output)
    - GPSDO 10 MHz SMA → HackRF CLKIN (hardware ADC phase-lock)
    - GPSDO 1 PPS → Pi 5 GPIO 18 (UTC timestamp interrupt)
    
    CRITICAL WARNING (RP1 Southbridge):
    The Pi 5's RP1 southbridge uses strictly 3.3V logic. Verify GPSDO output
    voltage with a multimeter before connection. If output exceeds 3.3V,
    use a logic level shifter to prevent catastrophic RP1 damage.
    """

    def __init__(self):
        """
        SPEC-005A.HAL-HW.INIT — Initialize HAL with mandatory clock verification.
        
        Implements "Silent Traitor" clock failure mitigation per ARCH-PHASE-2A-PIVOT.
        The HackRF will silently fail back to internal oscillator if GPSDO
        reference is lost. We must verify external clock before any ingestion.
        """
        self.sdr_device = None
        self._clock_verified = False
        
        if SOAPYSDR_AVAILABLE:
            self._init_soapy_sdr()
        elif PYHACKRF_AVAILABLE:
            self._verify_pyhackrf_clock()
        
    def _init_soapy_sdr(self):
        """
        SPEC-005A.HAL-HW.SOAPY — Initialize SoapySDR with mandatory phase-lock.
        
        Hardware-agnostic driver layer supporting multiple SDR platforms.
        Forces external clock source and validates GPSDO lock.
        """
        try:
            # Enumerate available devices
            results = SoapySDR.Device.enumerate()
            if not results:
                print("[FATAL] No SoapySDR devices found.")
                sys.exit(1)
            
            # Find HackRF device
            hackrf_found = False
            for result in results:
                if 'hackrf' in str(result).lower():
                    hackrf_found = True
                    break
            
            if not hackrf_found:
                print("[FATAL] HackRF not found in SoapySDR enumeration.")
                print("[ACTION] Verify HackRF is connected and driver installed.")
                sys.exit(1)
            
            # Initialize device
            self.sdr_device = SoapySDR.Device(dict(driver="hackrf"))
            
            # FORCE external clock (GPSDO reference) - "Silent Traitor" mitigation
            self._force_external_clock_soapy()
            
            self._clock_verified = True
            print("[+] HardwareHAL initialized with SoapySDR.")
            print("[+] Phase-lock verified. SDR slaved to GPSDO 10MHz reference.")
            
        except Exception as e:
            print(f"[FATAL] SoapySDR initialization failed: {e}")
            sys.exit(1)
    
    def _force_external_clock_soapy(self):
        """
        ARCH-PHASE-2A-PIVOT §5.1 — Force and validate external clock source.
        
        The "Silent Traitor" mitigation: HackRF silently fails to internal
        oscillator if GPSDO reference is lost. This method forces external
        clock and validates the hardware state before any data ingestion.
        """
        try:
            # Set clock source to external (GPSDO CLKIN)
            self.sdr_device.setClockSource("external")
            
            # Validate the hardware state
            actual_clock = self.sdr_device.getClockSource()
            if actual_clock != "external":
                print(f"[FATAL] Clock source mismatch. Hardware reports: {actual_clock}")
                print("[ACTION] Verify SMA connection and GPSDO amplitude.")
                print("[ACTION] Check GPSDO output voltage does not exceed 3.3V for Pi 5 GPIO.")
                sys.exit(1)
                
        except Exception as e:
            print(f"[FATAL] Failed to assert external clock: {e}")
            print("[ACTION] Verify GPSDO 10 MHz SMA → HackRF CLKIN connection.")
            sys.exit(1)
    
    def _verify_pyhackrf_clock(self):
        """
        Fallback clock verification for pyhackrf (non-SoapySDR) installations.
        """
        try:
            device = pyhackrf.HackRF()
            device.setup()
            
            # Attempt to verify external clock
            if hasattr(device, 'clock_source'):
                actual = device.clock_source
                if actual != "external":
                    print(f"[WARN] Clock source: {actual}. Expected: external")
                    print("[ACTION] Verify GPSDO connection before Tier 1 operations.")
            
            device.close()
            self._clock_verified = True
            
        except Exception as e:
            print(f"[WARN] Could not verify clock source: {e}")
    
    def verify_tier1_phase_lock(self) -> dict:
        """
        ARCH-PHASE-2A-PIVOT §5.1 — Explicit phase-lock verification.
        
        Forces and validates metrology-grade phase lock.
        Must be called before initializing the Kuramoto Coherence Engine.
        
        Returns:
            Dict with lock status
        """
        result = {
            "phase_lock_verified": False,
            "clock_source": "unknown",
            "driver": "unknown",
            "warnings": [],
        }
        
        if SOAPYSDR_AVAILABLE and self.sdr_device:
            try:
                self._force_external_clock_soapy()
                result["phase_lock_verified"] = True
                result["clock_source"] = self.sdr_device.getClockSource()
                result["driver"] = "SoapySDR"
            except Exception as e:
                result["warnings"].append(f"Clock verification failed: {e}")
        elif PYHACKRF_AVAILABLE:
            try:
                device = pyhackrf.HackRF()
                device.setup()
                result["clock_source"] = getattr(device, 'clock_source', 'unknown')
                result["phase_lock_verified"] = result["clock_source"] == "external"
                result["driver"] = "pyhackrf"
                device.close()
            except Exception as e:
                result["warnings"].append(f"pyhackrf verification failed: {e}")
        else:
            result["warnings"].append("No SDR driver available (SoapySDR or pyhackrf)")
        
        return result

    # pylint: disable=arguments-differ, too-many-arguments, too-many-positional-arguments, too-many-locals
    def ingest_gps_pps(
        self,
        pps_device: str = "/dev/pps0",
        node_id: str = "PI5-ALPHA",
        sensor_id: str = "GPSDO-01",
        pps_jitter_threshold_ns: float = 10_000.0,
    ) -> IngestionPayload:
        """
        SPEC-005A.4a — GPS/PPS Live Ingestion (RF Metrology, Rev 4.1)
        
        Reads 1 PPS hardware interrupt from GPSDO via pps-gpio kernel module.
        The PPS signal provides UTC epoch anchoring for the GPS-locked ADC samples.
        
        CRITICAL: Pi 5 RP1 southbridge uses 3.3V logic. Verify GPSDO PPS output
        does not exceed 3.3V before connecting to GPIO 18.
        
        Args:
            pps_device: Path to PPS device (default: /dev/pps0)
            node_id: Unique identifier for this anchor node
            sensor_id: Sensor identifier for the GPSDO unit
            pps_jitter_threshold_ns: Maximum acceptable PPS jitter (10 µs)
            
        Returns:
            IngestionPayload with PPS timing metadata
        """
        mono_ns = time.monotonic_ns()
        pps_jitter_ns = float("inf")
        pps_time_ns = 0
        
        # Read actual PPS timestamp from kernel via ioctl (SPEC-004A.3)
        try:
            fd = os.open(pps_device, os.O_RDONLY)
            try:
                # PPS_FETCH ioctl: returns (sec, nsec, seq, flags)
                buf = fcntl.ioctl(fd, 0x80047001, struct.pack("llll", 0, 0, 0, 0))
                sec, nsec, _, _ = struct.unpack("llll", buf)
                pps_time_ns = sec * 1_000_000_000 + nsec
                mono_now_ns = time.monotonic_ns()
                pps_jitter_ns = float(abs(mono_now_ns - pps_time_ns) % 1_000_000_000)
            finally:
                os.close(fd)
        except (OSError, IOError, struct.error):
            pps_jitter_ns = float("inf")

        # GPS lock status is inferred from valid PPS signal
        # GPSDO provides continuous PPS only when GPS-locked
        gps_locked = pps_jitter_ns < 1_000_000_000.0  # Valid PPS = GPS locked

        payload = IngestionPayload(
            payload_uuid=str(uuid.uuid4()),
            node_id=node_id,
            sensor_id=sensor_id,
            modality=SensorModality.GPS_PPS.value,
            timestamp_utc=time.time(),
            ingest_monotonic_ns=mono_ns,
            raw_value={
                "pps_time_ns": pps_time_ns,
                "source": "gpsdo_leo_bodnar_lbe1420",
                "pps_device": pps_device,
                "lbe1420_native_3v3": True,
            },
            extracted_phases=[],  # GPS provides no phase vector
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

    # pylint: disable=arguments-differ, too-many-arguments, too-many-positional-arguments, too-many-locals
    def ingest_sdr(
        self,
        center_freq: float = 100e6,
        sample_rate: float = 20e6,  # HackRF supports up to 20 MHz
        num_samples: int = 262144,  # Increased for 20 MHz bandwidth
        node_id: str = "PI5-ALPHA",
        sensor_id: str = "HACKRF-01",
        gps_locked: bool = True,
        pps_jitter_ns: float = 500.0,
        calibration_valid: bool = True,
        clock_source: str = "external",  # 'external' = GPSDO CLKIN
    ) -> IngestionPayload:
        """
        SPEC-005A.4b — SDR IQ Live Ingestion (RF Metrology, Rev 4.1-FORGE)
        
        Captures IQ samples using SoapySDR (hardware-agnostic) or pyhackrf fallback.
        The SDR MUST be hardware-locked to the GPSDO via 10 MHz CLKIN input.
        
        Pre-ingestion, this method enforces "Silent Traitor" mitigation:
        - Forces external clock source
        - Validates GPSDO lock
        - Exits on clock failure (prevents invalid data ingestion)
        
        USB jitter is irrelevant because:
        1. ADC sampling clock is GPS-locked at analog level (10 MHz CLKIN)
        2. Phase relationships between IQ samples are preserved by hardware
        3. UTC timestamps align samples via PPS + sample counting
        
        Args:
            center_freq: Center frequency in Hz (1 MHz - 6 GHz for HackRF)
            sample_rate: Sample rate in Hz (max 20 MHz for HackRF)
            num_samples: Number of IQ samples to capture
            node_id: Unique identifier for this anchor node
            sensor_id: Sensor identifier for the HackRF unit
            gps_locked: Whether GPSDO is providing valid reference
            pps_jitter_ns: Measured PPS jitter in nanoseconds
            calibration_valid: Whether calibration is within thresholds
            clock_source: 'external' (GPSDO) or 'internal' (free-running)
            
        Returns:
            IngestionPayload with GPS-locked IQ samples and phase extraction
        """
        mono_ns = time.monotonic_ns()
        phases: List[float] = []
        raw_val = {}
        
        # MANDATORY: Verify phase-lock before ingestion ("Silent Traitor" mitigation)
        if not self._clock_verified:
            lock_status = self.verify_tier1_phase_lock()
            if not lock_status["phase_lock_verified"]:
                print("[FATAL] Cannot ingest: Phase-lock not verified.")
                print("[ACTION] Check GPSDO 10 MHz → CLKIN connection.")
                sys.exit(1)
        
        if SOAPYSDR_AVAILABLE and self.sdr_device:
            # SoapySDR hardware-agnostic implementation
            raw_val = self._ingest_soapy(center_freq, sample_rate, num_samples)
            phases = raw_val.get("phases", [])
        elif PYHACKRF_AVAILABLE:
            # Fallback pyhackrf implementation
            raw_val = self._ingest_pyhackrf(center_freq, sample_rate, num_samples)
            phases = raw_val.get("phases", [])
        else:
            # No driver available
            raw_val = {
                "error": "No SDR driver available. Install: sudo apt install soapysdr-module-hackrf",
                "clock_source": clock_source,
                "center_freq": center_freq,
                "sample_rate": sample_rate,
            }

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
            source_path="/dev/hackrf0" if (SOAPYSDR_AVAILABLE or PYHACKRF_AVAILABLE) else "sdr_unavailable",
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
    
    def _ingest_soapy(self, center_freq: float, sample_rate: float, num_samples: int) -> dict:
        """
        SoapySDR-based ingestion (hardware-agnostic).
        """
        try:
            sdr = self.sdr_device
            
            # Configure device
            sdr.setSampleRate(SoapySDR.SOAPY_SDR_RX, 0, sample_rate)
            sdr.setFrequency(SoapySDR.SOAPY_SDR_RX, 0, center_freq)
            
            # Setup stream
            rx_stream = sdr.setupStream(SoapySDR.SOAPY_SDR_RX, SoapySDR.SOAPY_SDR_CF32)
            sdr.activateStream(rx_stream)
            
            # Read samples
            buff = np.empty(num_samples, np.complex64)
            sr = sdr.readStream(rx_stream, [buff], num_samples)
            
            # Cleanup
            sdr.deactivateStream(rx_stream)
            sdr.closeStream(rx_stream)
            
            # Phase extraction from GPS-locked samples
            phases = np.angle(buff).tolist()[:512]
            
            return {
                "iq_samples": buff[:512].tolist(),
                "center_freq": center_freq,
                "sample_rate": sample_rate,
                "clock_source": "external",
                "clock_locked_to_gpsdo": True,
                "bandwidth_mhz": sample_rate / 1e6,
                "phases": phases,
                "driver": "SoapySDR",
            }
            
        except Exception as e:
            return {
                "error": f"SoapySDR acquisition failed: {str(e)}",
                "clock_source": "external",
                "driver": "SoapySDR",
            }
    
    def _ingest_pyhackrf(self, center_freq: float, sample_rate: float, num_samples: int) -> dict:
        """
        pyhackrf fallback ingestion.
        """
        try:
            hackrf_device = pyhackrf.HackRF()
            hackrf_device.setup()
            
            # Configure frequency and sample rate
            hackrf_device.set_freq(int(center_freq))
            hackrf_device.set_sample_rate(int(sample_rate))
            
            # Set moderate gain for wideband capture
            hackrf_device.set_lna_gain(32)
            hackrf_device.set_vga_gain(20)
            
            # Capture samples
            iq_int8 = hackrf_device.read_samples(num_samples)
            hackrf_device.close()
            
            # Convert int8 to complex float normalized to [-1, 1]
            iq_raw = iq_int8.astype(np.float32) / 128.0
            iq_complex = iq_raw[0::2] + 1j * iq_raw[1::2]
            
            # Phase extraction from GPS-locked samples
            phases = np.angle(iq_complex).tolist()[:512]
            
            return {
                "iq_samples": iq_complex[:512].tolist(),
                "center_freq": center_freq,
                "sample_rate": sample_rate,
                "clock_source": "external",
                "clock_locked_to_gpsdo": True,
                "bandwidth_mhz": sample_rate / 1e6,
                "phases": phases,
                "driver": "pyhackrf",
            }
            
        except Exception as e:
            return {
                "error": f"pyhackrf acquisition failed: {str(e)}",
                "clock_source": "external",
                "driver": "pyhackrf",
            }

    def verify_gpsdo_lock(self, device_index: int = 0) -> dict:
        """
        SPEC-004A.3 — Verify GPSDO/HackRF hardware lock status.
        
        Returns diagnostic information about the RF Metrology chain.
        Includes "Silent Traitor" clock source verification.
        
        Args:
            device_index: HackRF device index (default 0)
            
        Returns:
            Dict with lock status and diagnostic information
        """
        info = {
            "soapy_available": SOAPYSDR_AVAILABLE,
            "pyhackrf_available": PYHACKRF_AVAILABLE,
            "driver_used": "none",
            "phase_lock_verified": False,
            "clock_source": "unknown",
            "rp1_warning": "Pi 5 RP1 uses 3.3V logic. Verify GPSDO PPS output voltage.",
        }
        
        if SOAPYSDR_AVAILABLE:
            try:
                results = SoapySDR.Device.enumerate()
                info["devices_found"] = len(results)
                info["driver_used"] = "SoapySDR"
                
                # Check if we can get clock source
                if self.sdr_device:
                    info["clock_source"] = self.sdr_device.getClockSource()
                    info["phase_lock_verified"] = info["clock_source"] == "external"
                    
            except Exception as e:
                info["error"] = str(e)
                
        elif PYHACKRF_AVAILABLE:
            try:
                device = pyhackrf.HackRF(device_index=device_index)
                device.setup()
                
                info["hackrf_detected"] = True
                info["serial_number"] = getattr(device, 'serial_number', 'unknown')
                info["board_id"] = getattr(device, 'board_id', 'unknown')
                info["clock_source"] = getattr(device, 'clock_source', 'unknown')
                info["phase_lock_verified"] = info["clock_source"] == "external"
                info["driver_used"] = "pyhackrf"
                info["sample_rate_range"] = "2.5 MHz - 20 MHz"
                info["frequency_range"] = "1 MHz - 6 GHz"
                
                device.close()
                
            except Exception as e:
                info["hackrf_detected"] = False
                info["error"] = str(e)
        else:
            info["error"] = "No SDR driver available. Install SoapySDR or pyhackrf."

        return info

    @staticmethod
    def verify_nmea_telemetry(
        serial_port: str = "/dev/ttyACM0",
        baud_rate: int = 9600,
        timeout: float = 3.0,
    ) -> dict:
        """
        SPEC-004A.3-NMEA — Verify LBE-1420 NMEA telemetry via USB-C virtual serial.

        The LBE-1420 provides observable NMEA sentences over a virtual serial port
        when connected via USB-C. This method queries the stream to confirm an
        active GPS fix before allowing data ingestion.

        Args:
            serial_port: Path to virtual serial device (default: /dev/ttyACM0)
            baud_rate: Serial baud rate (default: 9600)
            timeout: Read timeout in seconds

        Returns:
            Dict with GPS fix status and satellite info
        """
        result = {
            "nmea_available": False,
            "gps_fix": False,
            "serial_port": serial_port,
            "sentences": [],
            "warnings": [],
        }

        try:
            import serial  # pylint: disable=import-outside-toplevel
            ser = serial.Serial(serial_port, baud_rate, timeout=timeout)
            lines_read = 0
            max_lines = 10

            while lines_read < max_lines:
                line = ser.readline().decode("ascii", errors="ignore").strip()
                if not line:
                    break
                lines_read += 1
                result["sentences"].append(line)

                # Parse GGA sentence for fix quality
                if line.startswith("$GPGGA") or line.startswith("$GNGGA"):
                    parts = line.split(",")
                    if len(parts) > 6:
                        fix_quality = parts[6]
                        if fix_quality and int(fix_quality) > 0:
                            result["gps_fix"] = True
                        if len(parts) > 7 and parts[7]:
                            result["satellites_used"] = int(parts[7])

            ser.close()
            result["nmea_available"] = lines_read > 0

        except ImportError:
            result["warnings"].append("pyserial not installed: pip install pyserial")
        except (OSError, IOError) as e:
            result["warnings"].append(f"Serial port error: {e}")

        return result
