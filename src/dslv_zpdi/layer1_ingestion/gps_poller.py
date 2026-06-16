"""
SPEC-005A.4-GPS | GPS / Network Location Poller for Mobile Tier-2

Wraps termux-location with aggressive timeouts and backoff so that a
missing GPS fix or permission denial never blocks the sensor stream.
Location fixes are written to a shared async-safe structure for
Layer-1 enrichment.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

log = logging.getLogger("zpdi.gps")

TERMUX_LOCATION_BIN = "/data/data/com.termux/files/usr/bin/termux-location"

# How often to attempt a location fix (seconds)
DEFAULT_GPS_INTERVAL_S = float(os.environ.get("ZPDI_GPS_INTERVAL_S", "15.0"))
# Max time to wait for a single termux-location invocation (seconds)
DEFAULT_GPS_TIMEOUT_S = float(os.environ.get("ZPDI_GPS_TIMEOUT_S", "10.0"))
# Accuracy threshold (metres) below which a fix is considered usable
DEFAULT_GPS_ACCURACY_M = float(os.environ.get("ZPDI_GPS_ACCURACY_M", "50.0"))


@dataclass
class LocationFix:
    """SPEC-003A"""
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy: Optional[float] = None
    provider: str = "unknown"
    ts: float = 0.0

    # SPEC-003A
    def to_dict(self) -> dict[str, Any]:
        """SPEC-003A"""
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude,
            "accuracy": self.accuracy,
            "provider": self.provider,
            "ts": self.ts,
        }


# SPEC-003A
class GPSPoller:
    """Maintains the latest location fix via termux-location.

    Runs an asyncio task that polls termux-location at a configurable
    interval.  If a fix succeeds, it is stored in ``latest``.  If the
    device has no GPS lock or permissions are missing, the poller logs
    at debug level and continues retrying with capped exponential backoff.
    """

    # SPEC-003A
    def __init__(
        self,
        interval_s: float = DEFAULT_GPS_INTERVAL_S,
        timeout_s: float = DEFAULT_GPS_TIMEOUT_S,
        accuracy_m: float = DEFAULT_GPS_ACCURACY_M,
    ) -> None:
        self._interval = interval_s
        self._timeout = timeout_s
        self._accuracy = accuracy_m
        self.latest: Optional[LocationFix] = None
        self._lock = asyncio.Lock()
        self._stop = asyncio.Event()
        self._backoff = 1.0

    async def get_latest(self) -> Optional[LocationFix]:
        async with self._lock:
            return self.latest

    # SPEC-003A
    async def _set_latest(self, fix: Optional[LocationFix]) -> None:
        async with self._lock:
            self.latest = fix

    # SPEC-003A
    async def _poll_once(self) -> Optional[LocationFix]:
        """Run termux-location once and parse the JSON output."""
        # Try GPS first, then network, then passive
        for provider in ("gps", "network", "passive"):
            cmd = [
                TERMUX_LOCATION_BIN,
                "-p", provider,
                "-r", "once",
            ]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(), timeout=self._timeout
                    )
                except asyncio.TimeoutError:
                    with contextlib.suppress(ProcessLookupError):
                        proc.kill()
                    await proc.wait()
                    continue

                if proc.returncode != 0:
                    err = stderr.decode("utf-8", errors="replace").strip()
                    log.debug("termux-location (%s) failed: %s", provider, err)
                    continue

                text = stdout.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    log.debug("termux-location (%s) returned non-JSON: %s", provider, text)
                    continue

                # Validate required fields
                lat = data.get("latitude")
                lon = data.get("longitude")
                if lat is None or lon is None:
                    log.debug("termux-location (%s) missing lat/lon: %s", provider, data)
                    continue

                fix = LocationFix(
                    latitude=float(lat),
                    longitude=float(lon),
                    altitude=data.get("altitude"),
                    accuracy=data.get("accuracy"),
                    provider=provider,
                    ts=asyncio.get_event_loop().time(),
                )
                if fix.accuracy is not None and fix.accuracy <= self._accuracy:
                    return fix
                elif fix.accuracy is None:
                    # Accept fix if accuracy field is missing entirely
                    return fix
                else:
                    # Accuracy too poor — keep it as fallback but keep trying
                    log.debug("termux-location (%s) accuracy %.1fm exceeds threshold", provider, fix.accuracy)
                    # Store as tentative but don't return yet
                    await self._set_latest(fix)
            except (FileNotFoundError, OSError) as exc:
                log.debug("termux-location (%s) spawn error: %s", provider, exc)
                continue
        return None

    # SPEC-003A
    async def run(self) -> None:
        """Main loop — poll until stop event is set."""
        log.info("GPS poller starting interval=%.1fs timeout=%.1fs", self._interval, self._timeout)
        while not self._stop.is_set():
            fix = await self._poll_once()
            if fix is not None:
                await self._set_latest(fix)
                log.debug("GPS fix updated: %.6f, %.6f (±%.1fm %s)", fix.latitude,
                          fix.longitude, fix.accuracy or -1, fix.provider)
                self._backoff = 1.0
            else:
                log.debug("GPS fix unavailable — retry in %.1fs", self._backoff)

            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self._backoff)
                return
            except asyncio.TimeoutError:
                pass
            self._backoff = min(self._backoff * 2, self._interval)

    def stop(self) -> None:
        """SPEC-003A"""
        self._stop.set()
