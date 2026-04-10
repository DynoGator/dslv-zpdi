"""
SPEC-005A.HAL-FACTORY | HAL Factory (Rev 4.0.2)
Dynamic selection between hardware and simulated ingestion layers.
"""

import os
from .hal_hardware import HardwareHAL
from .hal_simulated import SimulatedHAL
from .hal_base import BaseHAL


def get_hal() -> BaseHAL:
    """SPEC-005A.HAL-FACTORY — Returns appropriate HAL based on environment."""
    if os.environ.get("DEV_SIMULATOR") == "1":
        return SimulatedHAL()
    return HardwareHAL()


# Legacy functional hooks for Phase 1 compatibility
def ingest_gps_pps(**kwargs):
    """SPEC-005A.4a — Legacy functional hook for GPS/PPS."""
    return get_hal().ingest_gps_pps(**kwargs)


def ingest_sdr(**kwargs):
    """SPEC-005A.4b — Legacy functional hook for SDR."""
    return get_hal().ingest_sdr(**kwargs)
