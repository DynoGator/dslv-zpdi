"""
DEPRECATION WARNING: cm5_ingestion.py is retained for backward compatibility only.

The canonical module for HAL factory functionality is now `hal_factory.py`.
All new code should import from `dslv_zpdi.layer1_ingestion.hal_factory`.
"""

import warnings

from .hal_factory import (
    BaseHAL,
    HardwareHAL,
    SimulatedHAL,
    get_hal,
    ingest_gps_pps,
    ingest_sdr,
    verify_hardware_lock,
)

warnings.warn(
    "cm5_ingestion.py is deprecated; use hal_factory.py instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "BaseHAL",
    "HardwareHAL",
    "SimulatedHAL",
    "get_hal",
    "ingest_gps_pps",
    "ingest_sdr",
    "verify_hardware_lock",
]
