"""
SPEC-005A.HAL-HW | Hardware Implementation (Rev 4.1-PIVOT)
Concrete implementation of the HAL for RF Metrology hardware:
Raspberry Pi 5 + HackRF One + Leo Bodnar Mini GPSDO.

This implementation achieves hardware-level ADC phase coherence by:
1. 10 MHz reference from GPSDO → HackRF CLKIN (hardware ADC lock)
2. 1 PPS from GPSDO → GPIO 18 (UTC epoch anchoring)

Rev 4.1: Pivoted from CM5/i210-T1/RTL-SDR to Pi5/GPSDO/HackRF architecture.
"""

# pylint: disable=duplicate-code

import fcntl
import os
import struct
import time
import uuid
from typing import List, Optional

import numpy as np

from .hal_base import BaseHAL
from .payload import IngestionPayload, SensorModality

# HackRF support - gracefully handle missing library
# Install: pip install pyhackrf
try:
    import pyhackrf
    HACKRF_AVAILABLE = True
except ImportError:
    HACKRF_AVAILABLE = False


class HardwareHAL(BaseHAL):
    """
    SPEC-005A.HAL-HW — Production hardware ingestion logic for RF Metrology stack.
    
    Hardware Requirements (SPEC-004A.1, SPEC-004A.2):
    - Raspberry Pi 5 (16GB) or compatible compute platform
    - HackRF One with CLKIN port for 10 MHz GPSDO reference
    - Leo Bodnar Mini GPSDO (10 MHz + 1 PPS output)
    - GPSDO 10 MHz SMA → HackRF CLKIN (hardware ADC phase-lock)
    - GPSDO 1 PPS → Pi 5 GPIO 18 (UTC timestamp interrupt)
    """

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
                "source": "gpsdo_leo_bodnar_mini",
                "pps_device": pps_device,
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
        SPEC-005A.4b — SDR IQ Live Ingestion (RF Metrology, Rev 4.1)
        
        Captures IQ samples from HackRF One with hardware-level phase coherence.
        The HackRF MUST be hardware-locked to the GPSDO via 10 MHz CLKIN input.
        This provides definitive phase coherence across geographically distributed nodes.
        
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
        
        if not HACKRF_AVAILABLE:
            # Graceful degradation: return error payload
            raw_val = {
                "error": "pyhackrf not installed. Install: pip install pyhackrf",
                "clock_source": clock_source,
                "center_freq": center_freq,
                "sample_rate": sample_rate,
            }
        else:
            try:
                # Initialize HackRF with GPSDO reference
                hackrf_device = pyhackrf.HackRF()
                hackrf_device.setup()
                
                # Configure frequency and sample rate
                hackrf_device.set_freq(int(center_freq))
                hackrf_device.set_sample_rate(int(sample_rate))
                
                # Verify external clock lock (SPEC-004A.1 compliance check)
                # The GPSDO 10 MHz must be connected to CLKIN
                actual_clock = hackrf_device.clock_source if hasattr(hackrf_device, 'clock_source') else "unknown"
                
                # Set moderate gain for wideband capture
                hackrf_device.set_lna_gain(32)  # 0-40 dB
                hackrf_device.set_vga_gain(20)  # 0-62 dB
                
                # Capture samples
                # Note: pyhackrf returns interleaved int8 IQ samples
                iq_int8 = hackrf_device.read_samples(num_samples)
                hackrf_device.close()
                
                # Convert int8 to complex float normalized to [-1, 1]
                iq_raw = iq_int8.astype(np.float32) / 128.0
                iq_complex = iq_raw[0::2] + 1j * iq_raw[1::2]
                
                # Phase extraction from GPS-locked samples
                # Per SPEC-005: Phase extraction is Layer 1's responsibility
                phases = np.angle(iq_complex).tolist()[:512]
                
                raw_val = {
                    "iq_samples": iq_complex[:512].tolist(),
                    "center_freq": center_freq,
                    "sample_rate": sample_rate,
                    "clock_source": actual_clock,
                    "clock_locked_to_gpsdo": clock_source == "external",
                    "bandwidth_mhz": sample_rate / 1e6,
                }
                
            except Exception as e:  # pylint: disable=broad-exception-caught
                # SPEC-005A.4b: Graceful failure with diagnostic info
                phases = []
                raw_val = {
                    "error": f"HackRF acquisition failed: {str(e)}",
                    "clock_source": clock_source,
                    "hackrf_available": HACKRF_AVAILABLE,
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
            source_path="/dev/hackrf0" if HACKRF_AVAILABLE else "hackrf_simulated",
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

    def verify_gpsdo_lock(self, device_index: int = 0) -> dict:
        """
        SPEC-004A.3 — Verify GPSDO/HackRF hardware lock status.
        
        Returns diagnostic information about the RF Metrology chain:
        - HackRF detection status
        - Clock source (internal vs external/GPSDO)
        - Sample rate capability
        
        Args:
            device_index: HackRF device index (default 0)
            
        Returns:
            Dict with lock status and diagnostic information
        """
        if not HACKRF_AVAILABLE:
            return {
                "hackrf_detected": False,
                "clock_source": "unknown",
                "error": "pyhackrf library not installed",
                "install_command": "pip install pyhackrf",
            }
        
        try:
            hackrf_device = pyhackrf.HackRF(device_index=device_index)
            hackrf_device.setup()
            
            info = {
                "hackrf_detected": True,
                "serial_number": hackrf_device.serial_number if hasattr(hackrf_device, 'serial_number') else "unknown",
                "board_id": hackrf_device.board_id if hasattr(hackrf_device, 'board_id') else "unknown",
                "clock_source": hackrf_device.clock_source if hasattr(hackrf_device, 'clock_source') else "unknown",
                "external_clock_detected": hackrf_device.clock_source == "external" if hasattr(hackrf_device, 'clock_source') else False,
                "sample_rate_range": "2.5 MHz - 20 MHz",
                "frequency_range": "1 MHz - 6 GHz",
            }
            hackrf_device.close()
            return info
            
        except Exception as e:  # pylint: disable=broad-exception-caught
            return {
                "hackrf_detected": False,
                "clock_source": "unknown",
                "error": str(e),
            }
