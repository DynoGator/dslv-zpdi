"""
SPEC-004A.3 — GPSDOLockMonitor timing tests.

The monitor reads wall-clock time and shells out to ``chronyc`` and the
PlutoSDRplus clock probe. These tests replace both probes with stubs and drive
the monitor's clock explicitly, so grace-period and holdover behaviour is
asserted deterministically instead of depending on real sleeps, subprocess
latency, or whatever tools happen to be installed on the CI runner.
"""

import pytest

from dslv_zpdi.layer1_ingestion import lock_monitor as lock_monitor_module
from dslv_zpdi.layer1_ingestion.hal_simulated import SimulatedHAL
from dslv_zpdi.layer1_ingestion.lock_monitor import GPSDOLockMonitor

_HEALTHY_JITTER_NS = 1.0
_BAD_JITTER_NS = 50000.0


class _FakeClock:
    """SPEC-004A.3 — Manually advanced stand-in for the ``time`` module."""

    def __init__(self, start: float = 1_000_000.0) -> None:
        self.now = start

    def time(self) -> float:
        """SPEC-004A.3 — Return the current fake wall-clock time."""
        return self.now

    def advance(self, seconds: float) -> None:
        """SPEC-004A.3 — Move the fake clock forward."""
        self.now += seconds


class _LostGPSHAL:
    """SPEC-004A.3 — HAL stub reporting NMEA telemetry without a GPS fix."""

    def verify_nmea_telemetry(self) -> dict:
        """SPEC-004A.3 — Report loss of GPS fix."""
        return {"gps_fix": False}


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> _FakeClock:
    """SPEC-004A.3 — Patch the lock monitor's clock with a controllable fake."""
    fake = _FakeClock()
    monkeypatch.setattr(lock_monitor_module, "time", fake)
    return fake


def _make_monitor(monkeypatch: pytest.MonkeyPatch, jitter_ns: list[float], **kwargs):
    """SPEC-004A.3 — Build a monitor whose chronyc and Pluto clock probes are stubbed."""
    monitor = GPSDOLockMonitor(**kwargs)
    monkeypatch.setattr(monitor, "_get_chronyc_jitter", lambda: jitter_ns[0])
    monkeypatch.setattr(monitor, "_verify_plutosdrplus_clock", lambda: True)
    return monitor


def test_lbe1421_stability_mock(monkeypatch, clock):
    """SPEC-004A.3 — Verify monitor accepts 1e-12 stability (~1 ns jitter)."""
    monitor = _make_monitor(monkeypatch, [_HEALTHY_JITTER_NS], jitter_threshold_ns=10.0)

    status = monitor.check_lock_state(SimulatedHAL())

    assert status["healthy"] is True
    assert status["quarantine"] is False
    assert status["metrics"]["pps_jitter_ns"] < 10.0


def test_lbe1421_jitter_quarantine(monkeypatch, clock):
    """SPEC-004A.3 — Verify quarantine only after the jitter grace period elapses."""
    jitter = [_HEALTHY_JITTER_NS]
    # Grace period stays below the default 30 s unlock threshold so this test
    # exercises the jitter path rather than the total-unlock path.
    monitor = _make_monitor(
        monkeypatch, jitter, jitter_threshold_ns=10.0, jitter_grace_period_s=0.1
    )
    hal = SimulatedHAL()

    # 1. Healthy start
    status = monitor.check_lock_state(hal)
    assert status["quarantine"] is False

    # 2. Inject jitter: first violation opens the grace window
    jitter[0] = _BAD_JITTER_NS
    status = monitor.check_lock_state(hal)
    assert status["quarantine"] is False

    # 3. Still inside the grace window
    clock.advance(0.05)
    status = monitor.check_lock_state(hal)
    assert status["quarantine"] is False

    # 4. Grace window expired
    clock.advance(0.1)
    status = monitor.check_lock_state(hal)
    assert status["quarantine"] is True
    assert status["healthy"] is False


def test_lbe1421_holdover_seamless(monkeypatch, clock):
    """SPEC-004A.3 — Verify holdover within the unlock threshold, quarantine after it."""
    monitor = _make_monitor(monkeypatch, [_HEALTHY_JITTER_NS], unlock_threshold_s=2.0)

    # 1. Lock active
    status = monitor.check_lock_state(SimulatedHAL())
    assert status["healthy"] is True

    # 2. GPS loss: holdover, not yet quarantined
    lost_hal = _LostGPSHAL()
    clock.advance(1.0)
    status = monitor.check_lock_state(lost_hal)
    assert status["healthy"] is False
    assert status["quarantine"] is False

    # 3. Holdover expires
    clock.advance(1.5)
    status = monitor.check_lock_state(lost_hal)
    assert status["quarantine"] is True
