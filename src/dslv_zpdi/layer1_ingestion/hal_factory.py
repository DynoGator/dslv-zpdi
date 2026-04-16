"""
SPEC-005A.HAL-FACTORY | HAL Factory (Rev 4.2-LBE1420)
Dynamic selection between hardware and simulated ingestion layers.

Rev 4.1: Updated for RF Metrology architecture (Pi 5 + HackRF + GPSDO).
Note: Module name retained for backward compatibility; implements new hardware stack.
"""

import os

from .hal_base import BaseHAL
from .hal_hardware import HardwareHAL
from .hal_simulated import SimulatedHAL


def get_hal() -> BaseHAL:
    """
    SPEC-005A.HAL-FACTORY — Returns appropriate HAL based on environment.

    Returns:
        SimulatedHAL if DEV_SIMULATOR=1, otherwise HardwareHAL for RF Metrology stack
    """
    if os.environ.get("DEV_SIMULATOR") == "1":
        return SimulatedHAL()
    return HardwareHAL()


def ingest_gps_pps(**kwargs):
    """
    SPEC-005A.4a — GPS/PPS ingestion via GPSDO.

    Routes to appropriate HAL implementation:
    - Hardware: Leo Bodnar LBE-1420 GPSDO 1 PPS via GPIO
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
