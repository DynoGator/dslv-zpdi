"""
SPEC-005A.4 — Canonical HAL factory (Rev 4.4.0).
Dynamic selection between hardware and simulated ingestion layers.
"""

import os

from .hal_hardware import HardwareHAL
from .hal_simulated import SimulatedHAL


def get_hal(tier: int = 1, simulator: bool = False) -> HardwareHAL | SimulatedHAL:
    """
    SPEC-005A.4 — Returns appropriate HAL based on environment.

    Args:
        tier: Hardware tier level (default 1).
        simulator: Force simulated HAL regardless of environment.

    Returns:
        SimulatedHAL if simulator=True or DEV_SIMULATOR=1, otherwise HardwareHAL.
    """
    if simulator or os.getenv("DEV_SIMULATOR") == "1":
        return SimulatedHAL()
    return HardwareHAL()  # SoapySDR primary → pyhackrf fallback, external clock enforced


def ingest_gps_pps(**kwargs):
    """
    SPEC-005A.4a — GPS/PPS ingestion via GPSDO.

    Routes to appropriate HAL implementation:
    - Hardware: Leo Bodnar LBE-1421 GPSDO 1 PPS via GPIO
    - Simulated: Deterministic GPSDO simulation
    """
    return get_hal().ingest_gps_pps(**kwargs)


def ingest_sdr(**kwargs):
    """
    SPEC-005A.4b — SDR IQ ingestion via HackRF One.

    Routes to appropriate HAL implementation:
    - Hardware: HackRF One with GPSDO 10 MHz CLKIN (hardware phase-lock)
    - Simulated: Deterministic GPS-locked IQ simulation

    Hardware Requirements (SPEC-004A.1):
    - GPSDO 10 MHz SMA → HackRF CLKIN (hardware ADC lock)
    - GPSDO 1 PPS → Pi 5 GPIO 18 (UTC timestamp)
    """
    return get_hal().ingest_sdr(**kwargs)


def verify_hardware_lock(device_index: int = 0) -> dict:
    """
    SPEC-004A.3 — Verify GPSDO/HackRF hardware lock status.

    Checks:
    - HackRF detection
    - External clock source (GPSDO 10 MHz)
    - Clock lock status

    Args:
        device_index: HackRF device index (default 0)

    Returns:
        Dict with lock status and diagnostic information
    """
    return get_hal().verify_gpsdo_lock(device_index)
