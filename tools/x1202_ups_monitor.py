#!/usr/bin/env python3
"""
SPEC-004A.8 — Geekworm X-1202 UPS monitor daemon.

Polls the UPS fuel gauge and GPIO status. Triggers a single graceful shutdown
when either the battery SOC/voltage falls below configured emergency thresholds
or AC power has been absent longer than the configured hold-up time.

The monitor is intentionally conservative: if the UPS cannot be read, no
shutdown is initiated and the loop retries. This prevents a missing HAT or
I2C permission problem from killing a production node.

Environment variables:
    DSLV_X1202_POLL_SECONDS                 default 10
    DSLV_X1202_BATTERY_SHUTDOWN_PERCENT     default 15
    DSLV_X1202_BATTERY_SHUTDOWN_VOLTAGE     default 3.40
    DSLV_X1202_AC_LOST_SHUTDOWN_SECONDS     default 300
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# Allow importing from the repo src tree when run as a script.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from dslv_zpdi.layer1_ingestion.x1202_ups import X1202UpsMonitor

logger = logging.getLogger("dslv-zpdi.x1202-monitor")

STATE_DIR = Path("/var/lib/dslv_zpdi")
SHUTDOWN_MARKER = STATE_DIR / "x1202_shutdown_requested"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _request_shutdown(reason: str) -> None:
    """SPEC-004A.8 — Schedule a graceful halt exactly once."""
    if SHUTDOWN_MARKER.exists():
        return
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        SHUTDOWN_MARKER.write_text(
            f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {reason}\n",
            encoding="utf-8",
        )
    except OSError as exc:
        logger.error("Cannot write shutdown marker: %s", exc)

    logger.critical("X-1202 shutdown requested: %s", reason)
    try:
        subprocess.run(["sudo", "/sbin/shutdown", "-h", "+1"], check=False)
    except Exception as exc:  # pragma: no cover
        logger.error("shutdown command failed: %s", exc)


def main() -> None:
    """SPEC-004A.8 — Main monitor loop."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    poll_s = _env_int("DSLV_X1202_POLL_SECONDS", 10)
    shutdown_soc = _env_int("DSLV_X1202_BATTERY_SHUTDOWN_PERCENT", 15)
    shutdown_v = _env_float("DSLV_X1202_BATTERY_SHUTDOWN_VOLTAGE", 3.40)
    ac_lost_shutdown_s = _env_int("DSLV_X1202_AC_LOST_SHUTDOWN_SECONDS", 300)

    logger.info(
        "X-1202 monitor starting: poll=%ds shutdown_soc=%d%% shutdown_v=%.2fV ac_lost=%ds",
        poll_s, shutdown_soc, shutdown_v, ac_lost_shutdown_s,
    )

    ac_lost_since: float | None = None

    with X1202UpsMonitor() as monitor:
        while True:
            sample = monitor.sample()
            health = sample.health

            if health == "absent":
                logger.warning("UPS unreadable: %s", sample.error or "unknown")
                # Do not track AC state while unreadable; reset to avoid false shutdown.
                ac_lost_since = None
                time.sleep(poll_s)
                continue

            logger.info(
                "UPS: %.2fV %05.2f%% %.2f%%/h AC=%s charging=%s health=%s",
                sample.battery_voltage_v,
                sample.battery_percent,
                sample.charge_rate_percent_per_hour,
                sample.ac_present if sample.ac_present is not None else "?",
                sample.charging_enabled if sample.charging_enabled is not None else "?",
                health,
            )

            # Track continuous AC loss.
            if sample.ac_present is True:
                ac_lost_since = None
            elif sample.ac_present is False:
                if ac_lost_since is None:
                    ac_lost_since = time.time()
                ac_lost_s = time.time() - ac_lost_since
                if ac_lost_s >= ac_lost_shutdown_s:
                    _request_shutdown(
                        f"AC lost for {int(ac_lost_s)}s (>= {ac_lost_shutdown_s}s)"
                    )
                    break

            # Critical battery thresholds.
            if sample.battery_percent <= shutdown_soc:
                _request_shutdown(
                    f"battery SOC {sample.battery_percent:.2f}% <= {shutdown_soc}%"
                )
                break
            if sample.battery_voltage_v > 0 and sample.battery_voltage_v <= shutdown_v:
                _request_shutdown(
                    f"battery voltage {sample.battery_voltage_v:.2f}V <= {shutdown_v}V"
                )
                break

            time.sleep(poll_s)


if __name__ == "__main__":
    main()
