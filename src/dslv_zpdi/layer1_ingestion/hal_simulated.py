"""
SPEC-005A.HAL-SIM | Simulated Hardware Implementation (Rev 4.2-LBE1420)
Deterministic simulation of RF Metrology Tier 1 hardware for CI/CD and virtual validation.

Simulates: Raspberry Pi 5 + HackRF One + Leo Bodnar LBE-1420 GPSDO
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
        SPEC-005A.4a — Mock GPS/PPS Ingestion (GPSDO simulation).
        
        Simulates Leo Bodnar LBE-1420 GPSDO 1 PPS output.
        """
        node_id = kwargs.get("node_id", "SIM-ALPHA")
        sensor_id = kwargs.get("sensor_id", "SIM-GPSDO-01")
        gps_locked = kwargs.get("gps_locked", True)
        pps_jitter_ns = kwargs.get("pps_jitter_ns", 120.0)

        # Simulated GPSDO data
        gpsdo_data = {
            "pps_time_ns": time.time_ns(),
            "source": "gpsdo_lbe1420_simulated",
            "pps_device": "/dev/pps0",
            "gpsdo_lock": gps_locked,
            "satellites_visible": 12 if gps_locked else 0,
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
        SPEC-005A.4b — Mock SDR IQ Ingestion with GPS-locked phase coherence.
        
        Simulates HackRF One with 10 MHz GPSDO reference input.
        Generates deterministic GPS-locked IQ samples for testing.
        """
        node_id = kwargs.get("node_id", "SIM-ALPHA")
        sensor_id = kwargs.get("sensor_id", "SIM-HACKRF-01")
        sample_rate = kwargs.get("sample_rate", 20e6)  # HackRF: up to 20 MHz
        center_freq = kwargs.get("center_freq", 100e6)
        clock_source = kwargs.get("clock_source", "external")  # GPSDO-locked

        # Generate 512 samples of a coherent sine wave
        # Simulating GPS-locked phase stability
        t = np.linspace(0, 1, 512)
        phases = (2 * np.pi * 10 * t).tolist()  # 10Hz signal

        # Simulated GPS-locked IQ samples (serialized as [I, Q] pairs)
        iq_samples = [[float(np.cos(p)), float(np.sin(p))] for p in phases[:64]]

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
                "clock_locked_to_gpsdo": clock_source == "external",
                "bandwidth_mhz": sample_rate / 1e6,
                "iq_samples": iq_samples,
            },
            extracted_phases=phases,
            gps_locked=True,
            pps_jitter_ns=120.0,  # Simulated GPSDO stability
            calibration_valid=True,
            trust_state="CAL_TRUSTED",
        )
        return payload

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
