"""
SPEC-004A.3-NMEA — Compatibility re-export of the timing subpackage NMEA stream.

New code should import from `dslv_zpdi.layer1_ingestion.timing.nmea_stream`.
"""

from dslv_zpdi.layer1_ingestion.timing.nmea_stream import (
    NmeaStream,
    _empty_fix,
    logger,
    parse_gga,
)

__all__ = ["NmeaStream", "_empty_fix", "logger", "parse_gga"]
