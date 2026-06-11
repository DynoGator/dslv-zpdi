"""
SPEC-017 | Trust Tier: Network Infrastructure
Uplink manager — monitors Pi 5 ↔ Pixel hotspot relationship, exposes
network_status for dashboard HW/PIPE panels, and coordinates offline-cache
mode when the uplink drops.

Design Principles
─────────────────
- Never lose data because the uplink blipped.  When offline, samples are
  still written to local HDF5 and flagged "offline_cached".  When the uplink
  returns, a backfill flag is set so upstream consumers know a gap may exist.
- The manager is read-only w.r.t. the actual network interface.  It uses
  `ip route` parsing and ICMP echo (ping) to assess reachability, never
  modifying routing tables or NetworkManager state.
- Hotspot detection is heuristic: look for a default route on a Wi-Fi
  interface whose gateway is in the Pixel's expected subnet.
"""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass

logger = logging.getLogger("dslv-zpdi.uplink")


@dataclass
class NetworkStatus:
    """SPEC-017.1 — Canonical network health snapshot."""

    spec_id: str = "SPEC-017.1"
    timestamp_utc: float = 0.0
    online: bool = False
    primary_interface: str = ""
    gateway_ip: str = ""
    pixel_host: str = ""
    pixel_reachable: bool = False
    internet_reachable: bool = False
    dns_working: bool = False
    offline_since: float | None = None
    backfill_pending: bool = False
    mode: str = "unknown"  # online | offline | degraded

    def to_dict(self) -> dict:
        return {
            "online": self.online,
            "mode": self.mode,
            "primary_interface": self.primary_interface,
            "gateway_ip": self.gateway_ip,
            "pixel_reachable": self.pixel_reachable,
            "internet_reachable": self.internet_reachable,
            "dns_working": self.dns_working,
            "offline_since": self.offline_since,
            "backfill_pending": self.backfill_pending,
            "timestamp_utc": self.timestamp_utc,
        }


class UplinkManager:
    """SPEC-017.2 — Monitor and report Pi 5 uplink health."""

    def __init__(
        self,
        pixel_host: str = "10.42.0.2",
        internet_probe_host: str = "1.1.1.1",
        dns_probe_host: str = "cloudflare-dns.com",
        check_interval_sec: float = 10.0,
        offline_threshold_sec: float = 30.0,
    ):
        self.pixel_host = pixel_host
        self.internet_probe_host = internet_probe_host
        self.dns_probe_host = dns_probe_host
        self.check_interval = check_interval_sec
        self.offline_threshold = offline_threshold_sec
        self._last_status = NetworkStatus()
        self._offline_since: float | None = None
        self._backfill_pending = False

    def check(self) -> NetworkStatus:
        """Run a full connectivity check and return status."""
        ts = time.time()
        iface, gateway = self._detect_default_route()
        pixel_ok = self._ping_host(self.pixel_host)
        inet_ok = self._ping_host(self.internet_probe_host)
        dns_ok = self._check_dns()

        online = pixel_ok  # Pixel reachability is our primary concern
        mode = "online" if online else "offline"
        if online and not inet_ok:
            mode = "degraded"  # Pixel hotspot up but no internet passthrough

        if online:
            if self._offline_since is not None:
                # We just came back online
                self._backfill_pending = True
                logger.info("Uplink restored — backfill_pending = True")
            self._offline_since = None
        else:
            if self._offline_since is None:
                self._offline_since = ts

        status = NetworkStatus(
            timestamp_utc=ts,
            online=online,
            primary_interface=iface or "",
            gateway_ip=gateway or "",
            pixel_host=self.pixel_host,
            pixel_reachable=pixel_ok,
            internet_reachable=inet_ok,
            dns_working=dns_ok,
            offline_since=self._offline_since,
            backfill_pending=self._backfill_pending,
            mode=mode,
        )
        self._last_status = status
        return status

    def acknowledge_backfill(self):
        """Call after upstream consumer has processed the backfill queue."""
        self._backfill_pending = False
        logger.info("Backfill acknowledged")

    @property
    def last_status(self) -> NetworkStatus:
        return self._last_status

    def _detect_default_route(self) -> tuple[str | None, str | None]:
        """Return (interface_name, gateway_ip) for the current default route."""
        try:
            # psutil does not expose routes directly, so we parse `ip route`
            result = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0 and result.stdout:
                parts = result.stdout.strip().split()
                iface = None
                gateway = None
                for i, p in enumerate(parts):
                    if p == "dev" and i + 1 < len(parts):
                        iface = parts[i + 1]
                    if p == "via" and i + 1 < len(parts):
                        gateway = parts[i + 1]
                return iface, gateway
        except Exception as exc:
            logger.debug("Default route detection failed: %s", exc)
        return None, None

    def _ping_host(self, host: str, timeout_sec: float = 2.0) -> bool:
        """ICMP echo probe.  Returns True if host replies."""
        try:
            # -c 1 : one packet
            # -W 1 : wait 1 second for reply (Linux)
            cmd = ["ping", "-c", "1", "-W", str(int(timeout_sec)), host]
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout_sec + 2.0,
                check=False,
            )
            return result.returncode == 0
        except Exception as exc:
            logger.debug("Ping to %s failed: %s", host, exc)
            return False

    def _check_dns(self, timeout_sec: float = 3.0) -> bool:
        """Resolve a known hostname to verify DNS is functional."""
        try:
            import socket
            socket.setdefaulttimeout(timeout_sec)
            socket.getaddrinfo(self.dns_probe_host, None)
            return True
        except Exception as exc:
            logger.debug("DNS check failed: %s", exc)
            return False
        finally:
            socket.setdefaulttimeout(None)


class OfflineCacheCoordinator:
    """SPEC-017.3 — Coordinate local caching and backfill when uplink returns.

    This is a thin policy wrapper: it tells consumers whether to mark
    new samples as "offline_cached" and whether a backfill window is open.
    The actual queue/file backfill is handled by the session orchestrator
    and HDF5 writer (they already write locally).
    """

    def __init__(self, uplink: UplinkManager):
        self.uplink = uplink

    def sample_tag(self) -> dict:
        """Return metadata tag to attach to every sample during this cycle."""
        status = self.uplink.last_status
        tag = {
            "offline_cached": not status.online,
            "backfill_pending": status.backfill_pending,
            "network_mode": status.mode,
            "pixel_reachable": status.pixel_reachable,
        }
        return tag
