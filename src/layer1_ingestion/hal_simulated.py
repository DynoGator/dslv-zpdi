"""
SPEC-005A.HAL-SIM | Simulated Hardware Implementation (Rev 4.0.2)
Deterministic simulation of Tier 1 hardware for CI/CD and virtual validation.
"""

import time
import uuid
import numpy as np
from .hal_base import BaseHAL
from .payload import IngestionPayload, SensorModality


class SimulatedHAL(BaseHAL):
    """SPEC-005A.HAL-SIM — Virtual hardware for testing and CI/CD."""

    def ingest_gps_pps(self, **kwargs) -> IngestionPayload:
        """SPEC-005A.4a — Mock GPS/PPS Ingestion."""
        node_id = kwargs.get("node_id", "SIM-ALPHA")
        sensor_id = kwargs.get("sensor_id", "SIM-GPS-01")
        gps_locked = kwargs.get("gps_locked", True)
        pps_jitter_ns = kwargs.get("pps_jitter_ns", 120.0)

        nmea_data = {
            "sentence": ",123456.00,A,4000.0000,N,10500.0000,W,0.0,0.0,090426,,,A*77",
            "status": "A" if gps_locked else "V",
            "utc_time": "123456.00",
            "lat": "4000.0000",
            "lon": "10500.0000",
        }

        payload = IngestionPayload(
            payload_uuid=str(uuid.uuid4()),
            node_id=node_id,
            sensor_id=sensor_id,
            modality=SensorModality.GPS_PPS.value,
            timestamp_utc=time.time(),
            ingest_monotonic_ns=time.monotonic_ns(),
            raw_value=nmea_data,
            extracted_phases=[],
            gps_locked=gps_locked,
            pps_jitter_ns=pps_jitter_ns,
            calibration_valid=gps_locked and pps_jitter_ns < 10000.0,
            trust_state="CAL_TRUSTED" if gps_locked else "SECONDARY_QUARANTINED",
        )
        return payload

    def ingest_sdr(self, **kwargs) -> IngestionPayload:
        """SPEC-005A.4b — Mock SDR IQ Ingestion with deterministic phase."""
        node_id = kwargs.get("node_id", "SIM-ALPHA")
        sensor_id = kwargs.get("sensor_id", "SIM-RTLSDR-01")

        # Generate 512 samples of a coherent sine wave
        t = np.linspace(0, 1, 512)
        phases = (2 * np.pi * 10 * t).tolist()  # 10Hz signal

        payload = IngestionPayload(
            payload_uuid=str(uuid.uuid4()),
            node_id=node_id,
            sensor_id=sensor_id,
            modality=SensorModality.RF_SDR.value,
            timestamp_utc=time.time(),
            ingest_monotonic_ns=time.monotonic_ns(),
            raw_value={"center_freq": 100e6, "sample_rate": 2.4e6},
            extracted_phases=phases,
            gps_locked=True,
            pps_jitter_ns=500.0,
            calibration_valid=True,
            trust_state="CAL_TRUSTED",
        )
        return payload
