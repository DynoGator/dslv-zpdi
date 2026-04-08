"""
DSLV-ZPDI Layer 1 — CM5 Ingestion API
SPEC-005A | Trust Tier: Measured (Tier 1 Raw)
Platform: Raspberry Pi CM5 (Tier 1 Anchor Node)
"""
from typing import Optional, Dict, Any
from .payload import IngestionPayload, SensorModality

def ingest_sdr(node_id: str, device_path: str, gps_state: dict) -> Optional[str]:
    """SPEC-005A.4a — SDR RF Ingestion"""
    payload = IngestionPayload(
        node_id=node_id,
        sensor_id=device_path,
        modality=SensorModality.RF_SDR,
        timestamp_utc=gps_state.get('utc', 0.0),
        raw_value={"iq_data": "buffer_stub"}, 
        gps_locked=gps_state.get('locked', False),
        pps_jitter_ns=gps_state.get('pps_jitter_ns', 0.0),
        calibration_valid=True,
        hardware_tier=1,
    )
    return payload.to_json()

def ingest_gps_pps(node_id: str, gps_device: str, hardware_state: dict) -> Optional[str]:
    """SPEC-005A.4b — GPS/PPS Timing Ingestion"""
    payload = IngestionPayload(
        node_id=node_id,
        sensor_id=gps_device,
        modality=SensorModality.GPS_PPS,
        timestamp_utc=hardware_state.get('utc', 0.0),
        raw_value={"fix": "3D", "satellites": 9},
        gps_locked=hardware_state.get('locked', False),
        pps_jitter_ns=hardware_state.get('pps_jitter_ns', 0.0),
        calibration_valid=True,
        hardware_tier=1,
    )
    return payload.to_json()

def ingest_thermal(node_id: str, device_path: str, gps_state: dict) -> Optional[str]:
    """SPEC-005A.4c — Thermal Sensor Ingestion"""
    payload = IngestionPayload(
        node_id=node_id,
        sensor_id=device_path,
        modality=SensorModality.THERMAL,
        timestamp_utc=gps_state.get('utc', 0.0),
        raw_value={"thermal_array": "data_stub"},
        gps_locked=gps_state.get('locked', False),
        pps_jitter_ns=gps_state.get('pps_jitter_ns', 0.0),
        calibration_valid=True,
        hardware_tier=1,
    )
    return payload.to_json()

def ingest_acoustic(node_id: str, device_path: str, gps_state: dict) -> Optional[str]:
    """SPEC-005A.4d — Acoustic Sensor Ingestion"""
    payload = IngestionPayload(
        node_id=node_id,
        sensor_id=device_path,
        modality=SensorModality.ACOUSTIC,
        timestamp_utc=gps_state.get('utc', 0.0),
        raw_value={"audio_waveform": "data_stub"},
        gps_locked=gps_state.get('locked', False),
        pps_jitter_ns=gps_state.get('pps_jitter_ns', 0.0),
        calibration_valid=True,
        hardware_tier=1,
    )
    return payload.to_json()
