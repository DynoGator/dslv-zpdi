"""
SPEC-005A.TIMING-CHRONY — Parse chronyc tracking output for timing evidence.

This module does not shell out blindly; it expects `chronyc tracking` to be
available and parses the RMS offset / system time fields. Absence of chrony
is treated as unknown evidence (None) rather than a forced healthy state.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass

logger = logging.getLogger("dslv-zpdi.chrony")


@dataclass(frozen=True)
class ChronySnapshot:
    """SPEC-005A.TIMING-CHRONY — Structured chronyc tracking snapshot."""

    available: bool = False
    reference_id: str | None = None
    stratum: int | None = None
    rms_offset_ns: float | None = None
    system_offset_ns: float | None = None
    last_update_interval_s: float | None = None
    leap_status: str | None = None
    raw_lines: tuple[str, ...] = ()

    def summary(self) -> dict:
        return {
            "available": self.available,
            "reference_id": self.reference_id,
            "stratum": self.stratum,
            "rms_offset_ns": self.rms_offset_ns,
            "system_offset_ns": self.system_offset_ns,
            "last_update_interval_s": self.last_update_interval_s,
            "leap_status": self.leap_status,
        }


class ChronyMonitor:
    """SPEC-005A.TIMING-CHRONY — Monitor chronyd discipline status."""

    def __init__(self, max_system_offset_ns: float = 50_000.0) -> None:
        self.max_system_offset_ns = max_system_offset_ns

    def snapshot(self) -> ChronySnapshot:
        """SPEC-005A.TIMING-CHRONY — Return current chronyc tracking snapshot."""
        if not shutil.which("chronyc"):
            logger.debug("ChronyMonitor: chronyc not found")
            return ChronySnapshot(available=False)

        try:
            result = subprocess.run(
                ["chronyc", "tracking"],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("ChronyMonitor: chronyc tracking failed: %s", exc)
            return ChronySnapshot(available=False)

        if result.returncode != 0:
            logger.warning("ChronyMonitor: chronyc exited %d", result.returncode)
            return ChronySnapshot(available=False)

        return self._parse(result.stdout)

    def synchronized(self) -> bool:
        """Return True if chrony reports a current reference and small offset."""
        snap = self.snapshot()
        if not snap.available:
            return False
        if snap.reference_id in (None, "", "."):
            return False
        if snap.system_offset_ns is None:
            return False
        return abs(snap.system_offset_ns) <= self.max_system_offset_ns

    @staticmethod
    def _parse(output: str) -> ChronySnapshot:
        data: dict[str, str] = {}
        lines = output.strip().splitlines()
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip().lower().replace(" ", "_")] = value.strip()

        def _ns(field: str) -> float | None:
            """SPEC-005A.TIMING-CHRONY — Parse a chronyc nanosecond field."""
            raw = data.get(field)
            if not raw:
                return None
            # chronyc prints values like "-0.000000123 seconds" or "123 nanoseconds"
            match = re.search(
                r"([-+]?[\d.]+)\s*(seconds|nanoseconds|microseconds|milliseconds)?", raw
            )
            if not match:
                return None
            value = float(match.group(1))
            unit = match.group(2) or "seconds"
            multipliers = {
                "seconds": 1e9,
                "milliseconds": 1e6,
                "microseconds": 1e3,
                "nanoseconds": 1.0,
            }
            return value * multipliers.get(unit, 1e9)

        def _int(field: str) -> int | None:
            """SPEC-005A.TIMING-CHRONY — Parse a chronyc integer field."""
            raw = data.get(field)
            if not raw:
                return None
            try:
                return int(raw)
            except ValueError:
                return None

        ref = data.get("reference_id")
        if ref == ".":
            ref = None

        return ChronySnapshot(
            available=True,
            reference_id=ref,
            stratum=_int("stratum"),
            rms_offset_ns=_ns("rms_offset"),
            system_offset_ns=_ns("system_time"),
            last_update_interval_s=_ns("last_update"),
            leap_status=data.get("leap_status"),
            raw_lines=tuple(lines),
        )
