"""
SPEC-004A.4-PPS — Compatibility re-export of the timing subpackage PPS listener.

New code should import from `dslv_zpdi.layer1_ingestion.timing.pps_listener`.
"""

from dslv_zpdi.layer1_ingestion.timing.pps_listener import (
    PpsListener,
    logger,
)

__all__ = ["PpsListener", "logger"]
