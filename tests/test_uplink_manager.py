"""
SPEC-017.4 — Uplink manager unit tests.
"""



from dslv_zpdi.layer1_ingestion.uplink_manager import (
    NetworkStatus,
    OfflineCacheCoordinator,
    UplinkManager,
)


class TestUplinkManager:
    def test_check_returns_status(self):
        mgr = UplinkManager(pixel_host="127.0.0.1")
        status = mgr.check()
        assert isinstance(status, NetworkStatus)
        assert status.timestamp_utc > 0
        assert status.pixel_host == "127.0.0.1"

    def test_localhost_pixel_considered_reachable(self):
        mgr = UplinkManager(pixel_host="127.0.0.1", internet_probe_host="127.0.0.1")
        status = mgr.check()
        assert status.pixel_reachable is True
        assert status.online is True
        assert status.mode == "online"

    def test_unreachable_pixel_offline_mode(self):
        mgr = UplinkManager(pixel_host="192.0.2.1", internet_probe_host="192.0.2.2")
        status = mgr.check()
        assert status.pixel_reachable is False
        assert status.online is False
        assert status.mode == "offline"
        assert status.offline_since is not None

    def test_offline_then_online_triggers_backfill(self):
        mgr = UplinkManager(pixel_host="192.0.2.1")
        # First check: offline
        s1 = mgr.check()
        assert s1.backfill_pending is False
        assert mgr._offline_since is not None

        # Now pixel becomes reachable (mock by switching host)
        mgr.pixel_host = "127.0.0.1"
        s2 = mgr.check()
        assert s2.backfill_pending is True
        assert s2.online is True

        # Acknowledge backfill
        mgr.acknowledge_backfill()
        s3 = mgr.check()
        assert s3.backfill_pending is False

    def test_degraded_mode_no_internet(self):
        mgr = UplinkManager(
            pixel_host="127.0.0.1",
            internet_probe_host="192.0.2.2",  # unreachable
        )
        status = mgr.check()
        assert status.mode == "degraded"
        assert status.pixel_reachable is True
        assert status.internet_reachable is False

    def test_last_status_cached(self):
        mgr = UplinkManager(pixel_host="127.0.0.1")
        s1 = mgr.check()
        s2 = mgr.last_status
        assert s1.timestamp_utc == s2.timestamp_utc


class TestOfflineCacheCoordinator:
    def test_tag_when_online(self):
        mgr = UplinkManager(pixel_host="127.0.0.1")
        mgr.check()
        coord = OfflineCacheCoordinator(mgr)
        tag = coord.sample_tag()
        assert tag["offline_cached"] is False
        assert tag["pixel_reachable"] is True

    def test_tag_when_offline(self):
        mgr = UplinkManager(pixel_host="192.0.2.1")
        mgr.check()
        coord = OfflineCacheCoordinator(mgr)
        tag = coord.sample_tag()
        assert tag["offline_cached"] is True
        assert tag["pixel_reachable"] is False
