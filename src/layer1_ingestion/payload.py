"""SPEC-005A.1a — Sensor Type Registry (Mobile Extension)"""
from enum import Enum


class SensorModality(Enum):
    """Canonical modality registry."""
    RF_SDR = "rf_sdr"
    GPS_PPS = "gps_pps"
    THERMAL = "thermal"
    ACOUSTIC = "acoustic"
    ACCEL = "accel"
    MAGNETOMETER = "magnetometer"
    BAROMETER = "barometer"
    # Mobile Tier-2 modalities (Pixel 9 Pro XL sensor suite)
    GYROSCOPE = "gyroscope"
    ROTATION_VECTOR = "rotation_vector"
    GEOMAGNETIC_ROTATION = "geomagnetic_rotation"
    GRAVITY = "gravity"
