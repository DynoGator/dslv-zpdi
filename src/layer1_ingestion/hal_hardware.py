"""
SPEC-005A.HAL-HW | Hardware Implementation (Rev 3.5.2)
Concrete implementation of the HAL for physical CM5 + i210-T1 hardware.
"""
import os
import fcntl
import struct
import serial
import rtlsdr
import time
import uuid
import numpy as np
from .hal_base import BaseHAL
from .payload import IngestionPayload, SensorModality

class HardwareHAL(BaseHAL):
    """SPEC-005A.HAL-HW — Production hardware ingestion logic."""

    def ingest_gps_pps(
        self,
        serial_port: str = "/dev/ttyACM0",
        pps_device: str = "/dev/pps0",
        baud: int = 9600,
        node_id: str = "CM5-ALPHA",
        sensor_id: str = "UBLOX-GPS-01",
        pps_jitter_threshold_ns: float = 10_000.0,
    ) -> IngestionPayload:
        """SPEC-005A.4a — GPS/PPS Live Ingestion (Hardware-Anchored, Rev 3.2)"""
        mono_ns = time.monotonic_ns()
        pps_jitter_ns = float('inf')
        try:
            fd = os.open(pps_device, os.O_RDONLY)
            try:
                buf = fcntl.ioctl(fd, 0x80047001, struct.pack('llll', 0, 0, 0, 0))
                sec, nsec, _, _ = struct.unpack('llll', buf)
                pps_time_ns = sec * 1_000_000_000 + nsec
                mono_now_ns = time.monotonic_ns()
                pps_jitter_ns = float(abs(mono_now_ns - pps_time_ns) % 1_000_000_000)
            finally:
                os.close(fd)
        except (OSError, IOError):
            pps_jitter_ns = float('inf') 

        try:
            ser = serial.Serial(serial_port, baud, timeout=2)
            nmea_data = {}
            for _ in range(20):
                line = ser.readline().decode("ascii", errors="replace").strip()
                if line.startswith("$GPRMC") or line.startswith("$GNRMC"):
                    parts = line.split(",")
                    nmea_data["sentence"] = line
                    nmea_data["status"] = parts[2] if len(parts) > 2 else "V"
                    nmea_data["utc_time"] = parts[1] if len(parts) > 1 else ""
                    nmea_data["lat"] = parts[3] if len(parts) > 3 else ""
                    nmea_data["lon"] = parts[5] if len(parts) > 5 else ""
                    break
            ser.close()
        except Exception as e:
            nmea_data = {"error": str(e)}

        gps_locked = nmea_data.get("status") == "A"

        payload = IngestionPayload(
            payload_uuid=str(uuid.uuid4()),
            node_id=node_id,
            sensor_id=sensor_id,
            modality=SensorModality.GPS_PPS.value,
            timestamp_utc=time.time(),
            ingest_monotonic_ns=mono_ns,
            raw_value=nmea_data,
            extracted_phases=[],
            gps_locked=gps_locked,
            pps_jitter_ns=pps_jitter_ns,
            calibration_valid=gps_locked and pps_jitter_ns < pps_jitter_threshold_ns,
            calibration_age_s=0.0,
            drift_percent=0.0,
            source_path=serial_port,
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

    def ingest_sdr(
        self,
        center_freq: float = 100e6,
        sample_rate: float = 2.4e6,
        num_samples: int = 65536,
        node_id: str = "CM5-ALPHA",
        sensor_id: str = "RTLSDR-01",
        gps_locked: bool = True,
        pps_jitter_ns: float = 500.0,
        calibration_valid: bool = True,
    ) -> IngestionPayload:
        """SPEC-005A.4b — SDR IQ Live Ingestion (Rev 3.5.2 Robustness Fix)"""
        mono_ns = time.monotonic_ns()
        try:
            sdr = rtlsdr.RtlSdr()
            sdr.center_freq = center_freq
            sdr.sample_rate = sample_rate
            sdr.gain = "auto"
            iq_raw = sdr.read_samples(num_samples)
            sdr.close()
            
            # SPEC-005 Correctness: iq_raw is complex, compute phases directly
            phases = np.angle(iq_raw).tolist()[:512]
            raw_val = {
                "iq_samples": iq_raw[:512].tolist(),
                "center_freq": center_freq,
                "sample_rate": sample_rate,
            }
        except Exception as e:
            phases = []
            raw_val = {"error": str(e)}

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
            calibration_valid=calibration_valid,
            calibration_age_s=0.0,
            drift_percent=0.0,
            source_path="/dev/rtlsdr0",
            trust_state="ASSEMBLED",
            hardware_tier=1,
        )

        state, reason = payload.validate()
        payload.trust_state = state
        if reason:
            payload.quarantine_reason = reason
        if state == "ASSEMBLED" and not raw_val.get("error"):
            payload.trust_state = "TIME_TRUSTED"
            if payload.calibration_valid:
                payload.trust_state = "CAL_TRUSTED"

        return payload
