"""
SPEC-004A.3 — Continuous Timing Health Monitoring
"""

import logging
import subprocess
from threading import Event, Thread

logger = logging.getLogger("dslv-zpdi.timing")


class TimingMonitor:
    """SPEC-004A.3 — Runtime GPSDO/PPS jitter monitoring with automatic quarantine trigger."""

    def __init__(self, check_interval_seconds=10, jitter_threshold_ns=50000):
        self.check_interval = check_interval_seconds
        self.threshold_ns = jitter_threshold_ns
        self._stop_event = Event()
        self._thread = None
        self.last_jitter_ns = float("inf")
        self.healthy = False

    def start(self):
        """Start monitoring thread."""
        self._thread = Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Timing Monitor started (threshold: %d ns)", self.threshold_ns)

    def stop(self):
        """Signal thread to stop."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _monitor_loop(self):
        """Continuous monitoring loop."""
        while not self._stop_event.is_set():
            try:
                jitter = self._read_pps_jitter()
                self.last_jitter_ns = jitter
                self.healthy = jitter < self.threshold_ns

                if not self.healthy:
                    logger.error(
                        "SPEC-004A.3 VIOLATION: PPS jitter %d ns exceeds %d ns threshold",
                        jitter,
                        self.threshold_ns,
                    )
                    # Trigger system-wide quarantine via MVIP-6 hooks (Phase 2B integration)
                    self._trigger_timing_quarantine()

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Timing monitoring error: %s", e)
                self.healthy = False

            self._stop_event.wait(self.check_interval)

    def _read_pps_jitter(self) -> float:
        """Read current PPS jitter from chronyc tracking."""
        try:
            result = subprocess.run(
                ["chronyc", "tracking"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "RMS offset" in line:
                        # Example: RMS offset     : 0.000000021 s
                        parts = line.split(":")
                        if len(parts) > 1:
                            val_str = parts[1].strip().split()[0]
                            return float(val_str) * 1e9
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError, ValueError):
            pass  # Expected if chronyc is not running or output is unparsable
        return float("inf")

    def _trigger_timing_quarantine(self):
        """Emit signal to quarantine all Tier 1 data until timing recovers."""
        # Integration point with MVIP-6 watchdog - to be refined in Phase 2B
