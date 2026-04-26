"""
SPEC-005A.HAL-SIM | Simulated Hardware Implementation (Rev 4.4.0)
Deterministic simulation of RF Metrology Tier 1 hardware for CI/CD and virtual validation.

Simulates: Raspberry Pi 5 + HackRF One + Leo Bodnar LBE-1421 GPSDO
Rev 4.1: Updated to match HackRF + GPSDO RF Metrology architecture.
"""

# pylint: disable=duplicate-code

import time
import uuid

import numpy as np

from .hal_base import BaseHAL
from .payload import IngestionPayload, SensorModality


class SimulatedHAL(BaseHAL):
    """
    SPEC-005A.HAL-SIM — Virtual hardware for testing and CI/CD.
    
    Simulates the RF Metrology stack:
    - GPSDO providing 10 MHz reference and 1 PPS
    - HackRF One with external clock lock
    - GPS-locked IQ samples with coherent phase
    """

    def ingest_gps_pps(self, **kwargs) -> IngestionPayload:
        """
        SPEC-005A.4a — Mock GPS/PPS Ingestion (LBE-1421 simulation).
        
        Emulates dual outputs (Out1=1PPS), 1e-12 stability, 100ms pulse,
        and NMEA sentences per datasheet.
        """
        node_id = kwargs.get("node_id", "SIM-ALPHA")
        sensor_id = kwargs.get("sensor_id", "SIM-LBE-1421")
        gps_locked = kwargs.get("gps_locked", True)
        # 1e-12 stability @ 1000s -> ~1ns jitter simulated
        pps_jitter_ns = kwargs.get("pps_jitter_ns", 1.0 if gps_locked else 50000.0)

        # Simulated NMEA sentences
        nmea = {
            "nmea_available": True,
            "gps_fix": gps_locked,
            "satellites_used": 12 if gps_locked else 0,
            "hdop": 0.8 if gps_locked else 99.9,
            "sentences": [
                "$GNGGA,123456.00,5130.0000,N,00000.0000,E,1,12,0.8,50.0,M,,,,*47" if gps_locked else "$GNGGA,,,,,,0,00,99.9,,,,,,*56"
            ]
        }

        gpsdo_data = {
            "pps_time_ns": time.time_ns(),
            "source": "gpsdo_lbe1421_simulated",
            "pps_device": "/dev/pps0",
            "out1_mode": "1PPS",
            "out1_pulse_width_ms": 100,
            "out2_freq_hz": 10000000,
            "stability": "1e-12",
            "nmea_telemetry": nmea,
        }

        payload = IngestionPayload(
            payload_uuid=str(uuid.uuid4()),
            node_id=node_id,
            sensor_id=sensor_id,
            modality=SensorModality.GPS_PPS.value,
            timestamp_utc=time.time(),
            ingest_monotonic_ns=time.monotonic_ns(),
            raw_value=gpsdo_data,
            extracted_phases=[],
            gps_locked=gps_locked,
            pps_jitter_ns=pps_jitter_ns,
            calibration_valid=gps_locked and pps_jitter_ns < 10000.0,
            trust_state="CAL_TRUSTED" if gps_locked else "SECONDARY_QUARANTINED",
        )
        return payload

    def ingest_sdr(self, **kwargs) -> IngestionPayload:
        """
        SPEC-005A.4b — Mock SDR IQ Ingestion with LBE-1421 phase-noise curve.
        """
        node_id = kwargs.get("node_id", "SIM-ALPHA")
        sensor_id = kwargs.get("sensor_id", "SIM-HACKRF-1421")
        sample_rate = kwargs.get("sample_rate", 20e6)
        center_freq = kwargs.get("center_freq", 100e6)
        clock_source = kwargs.get("clock_source", "external")
        coherent_burst = bool(kwargs.get("coherent_burst", False))
        gps_locked = kwargs.get("gps_locked", True)

        # Emulate phase noise based on LBE-1421 datasheet p.2
        # -145 dBc/Hz @ 10kHz offset
        noise_std = 0.001 if gps_locked else 0.1
        
        rng = np.random.default_rng(hash(node_id) & 0xFFFFFFFF)
        if coherent_burst:
            phases = (rng.normal(0.0, noise_std, 64)).tolist()
        else:
            t = np.linspace(0, 1, 64)
            phases = (2 * np.pi * 10 * t + rng.normal(0, noise_std, 64)).tolist()
            
        iq_samples = [[float(np.cos(p)), float(np.sin(p))] for p in phases]

        payload = IngestionPayload(
            payload_uuid=str(uuid.uuid4()),
            node_id=node_id,
            sensor_id=sensor_id,
            modality=SensorModality.RF_SDR.value,
            timestamp_utc=time.time(),
            ingest_monotonic_ns=time.monotonic_ns(),
            raw_value={
                "center_freq": center_freq,
                "sample_rate": sample_rate,
                "clock_source": clock_source,
                "clock_locked_to_gpsdo": gps_locked and clock_source == "external",
                "phase_noise_model": "LBE-1421-V1",
                "iq_samples": iq_samples,
            },
            extracted_phases=phases,
            gps_locked=gps_locked,
            pps_jitter_ns=1.0 if gps_locked else 50000.0,
            calibration_valid=gps_locked,
            trust_state="CAL_TRUSTED" if gps_locked else "SECONDARY_QUARANTINED",
        )
        return payload

    def verify_nmea_telemetry(self) -> dict:
        """Mock NMEA for SimulatedHAL."""
        return {
            'nmea_available': True,
            'gps_fix': True,
            'satellites_used': 12,
            'hdop': 0.8
        }

    def verify_gpsdo_lock(self, device_index: int = 0) -> dict:
        """
        SPEC-004A.3 — Simulated GPSDO/HackRF verification.
        
        Returns simulated lock status for CI/CD testing.
        """
        return {
            "hackrf_detected": True,
            "serial_number": "SIM-0000000000000000",
            "board_id": "HackRF One",
            "clock_source": "external",
            "external_clock_detected": True,
            "sample_rate_range": "2.5 MHz - 20 MHz",
            "frequency_range": "1 MHz - 6 GHz",
            "simulated": True,
        }
