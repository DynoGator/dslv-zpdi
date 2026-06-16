"""SPEC-011.CLI — Command-line interface package."""

from dslv_zpdi.cli.preflight import preflight_main
from dslv_zpdi.cli.probe import probe_main
from dslv_zpdi.cli.verify import verify_main

__all__ = ["preflight_main", "probe_main", "verify_main"]
