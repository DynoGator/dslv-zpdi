"""
SPEC-017.4 — Uplink manager unit tests.

These tests validate UplinkManager state logic (reachability classification,
offline→online backfill, degraded mode) deterministically. The real network
probes (`_ping_host`, `_check_dns`) are mocked so the suite is hermetic and does
not depend on ICMP, DNS, or host networking — which differ between dev hosts,
containers, and CI runners.
"""

from unittest.mock import patch

from dslv_zpdi.layer1_ingestion.uplink_manager import (
    NetworkStatus,
    OfflineCacheCoordinator,
    UplinkManager,
)


def _reachable(hosts):
    """Return a _ping_host replacement that reports `hosts` as reachable.

    Patched onto the class, so it is bound and receives `self` first.
    """
    reachable = set(hosts)

    def _ping(self, host, *args, **kwargs):
        return host in reachable

    return _ping


class TestUplinkManager:
    def test_check_returns_status(self):
        mgr = UplinkManager(pixel_host="10.42.0.2")
        with (
            patch.object(UplinkManager, "_ping_host", _reachable(["10.42.0.2"])),
            patch.object(UplinkManager, "_check_dns", return_value=True),
        ):
            status = mgr.check()
        assert isinstance(status, NetworkStatus)
        assert status.timestamp_utc > 0
        assert status.pixel_host == "10.42.0.2"

    def test_localhost_pixel_considered_reachable(self):
        mgr = UplinkManager(pixel_host="10.42.0.2", internet_probe_host="1.1.1.1")
        with (
            patch.object(UplinkManager, "_ping_host", _reachable(["10.42.0.2", "1.1.1.1"])),
            patch.object(UplinkManager, "_check_dns", return_value=True),
        ):
            status = mgr.check()
        assert status.pixel_reachable is True
        assert status.online is True
        assert status.mode == "online"

    def test_unreachable_pixel_offline_mode(self):
        mgr = UplinkManager(pixel_host="192.0.2.1", internet_probe_host="192.0.2.2")
        with (
            patch.object(UplinkManager, "_ping_host", _reachable([])),
            patch.object(UplinkManager, "_check_dns", return_value=False),
        ):
            status = mgr.check()
        assert status.pixel_reachable is False
        assert status.online is False
        assert status.mode == "offline"
        assert status.offline_since is not None

    def test_offline_then_online_triggers_backfill(self):
        mgr = UplinkManager(pixel_host="10.42.0.2")
        # First check: pixel unreachable -> offline.
        with (
            patch.object(UplinkManager, "_ping_host", _reachable([])),
            patch.object(UplinkManager, "_check_dns", return_value=False),
        ):
            s1 = mgr.check()
        assert s1.backfill_pending is False
        assert mgr._offline_since is not None

        # Pixel becomes reachable -> backfill flagged.
        with (
            patch.object(UplinkManager, "_ping_host", _reachable(["10.42.0.2"])),
            patch.object(UplinkManager, "_check_dns", return_value=True),
        ):
            s2 = mgr.check()
        assert s2.backfill_pending is True
        assert s2.online is True

        # Acknowledge backfill -> flag clears on next check.
        mgr.acknowledge_backfill()
        with (
            patch.object(UplinkManager, "_ping_host", _reachable(["10.42.0.2"])),
            patch.object(UplinkManager, "_check_dns", return_value=True),
        ):
            s3 = mgr.check()
        assert s3.backfill_pending is False

    def test_degraded_mode_no_internet(self):
        mgr = UplinkManager(pixel_host="10.42.0.2", internet_probe_host="1.1.1.1")
        # Pixel reachable but internet probe unreachable -> degraded.
        with (
            patch.object(UplinkManager, "_ping_host", _reachable(["10.42.0.2"])),
            patch.object(UplinkManager, "_check_dns", return_value=False),
        ):
            status = mgr.check()
        assert status.mode == "degraded"
        assert status.pixel_reachable is True
        assert status.internet_reachable is False

    def test_last_status_cached(self):
        mgr = UplinkManager(pixel_host="10.42.0.2")
        with (
            patch.object(UplinkManager, "_ping_host", _reachable(["10.42.0.2"])),
            patch.object(UplinkManager, "_check_dns", return_value=True),
        ):
            s1 = mgr.check()
        s2 = mgr.last_status
        assert s1.timestamp_utc == s2.timestamp_utc


class TestOfflineCacheCoordinator:
    def test_tag_when_online(self):
        mgr = UplinkManager(pixel_host="10.42.0.2")
        with (
            patch.object(UplinkManager, "_ping_host", _reachable(["10.42.0.2"])),
            patch.object(UplinkManager, "_check_dns", return_value=True),
        ):
            mgr.check()
        coord = OfflineCacheCoordinator(mgr)
        tag = coord.sample_tag()
        assert tag["offline_cached"] is False
        assert tag["pixel_reachable"] is True

    def test_tag_when_offline(self):
        mgr = UplinkManager(pixel_host="192.0.2.1")
        with (
            patch.object(UplinkManager, "_ping_host", _reachable([])),
            patch.object(UplinkManager, "_check_dns", return_value=False),
        ):
            mgr.check()
        coord = OfflineCacheCoordinator(mgr)
        tag = coord.sample_tag()
        assert tag["offline_cached"] is True
        assert tag["pixel_reachable"] is False
