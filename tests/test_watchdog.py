"""Unit tests for MVIP-6 Watchdog."""

from dslv_zpdi.watchdog.mvip6 import MVIP6Watchdog


def test_watchdog_healthy():
    wd = MVIP6Watchdog()
    payload = {"gps_locked": True, "pps_jitter_ns": 120.0, "drift_percent": 0.05}
    assert wd.evaluate_node_health(payload) is True


def test_watchdog_unhealthy():
    wd = MVIP6Watchdog()

    # GPS Unlocked
    assert (
        wd.evaluate_node_health({"gps_locked": False, "pps_jitter_ns": 120.0}) is False
    )

    # High Jitter
    assert (
        wd.evaluate_node_health({"gps_locked": True, "pps_jitter_ns": 50000.0}) is False
    )

    # High Drift
    assert (
        wd.evaluate_node_health(
            {"gps_locked": True, "pps_jitter_ns": 120.0, "drift_percent": 25.0}
        )
        is False
    )


if __name__ == "__main__":
    test_watchdog_healthy()
    test_watchdog_unhealthy()
    print("Watchdog tests passed.")
