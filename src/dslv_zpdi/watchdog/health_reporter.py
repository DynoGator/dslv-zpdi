"""
SPEC-014 — Machine-Readable Health Endpoint
Writes /run/dslv-zpdi/health.json every N seconds for external orchestrators.
"""

import json
import os
import time
from pathlib import Path
from threading import Event, Thread
from typing import Any, Dict, Optional

from dslv_zpdi.logging_config import get_logger

logger = get_logger("health")

DEFAULT_INTERVAL_SEC = 10.0
DEFAULT_PATH = "/run/dslv-zpdi/health.json"


class HealthReporter:
    """SPEC-014 — Non-blocking health state emitter."""

    def __init__(
        self,
        interval_sec: float = DEFAULT_INTERVAL_SEC,
        path: str = DEFAULT_PATH,
    ):
        self.interval_sec = interval_sec
        self.path = Path(path)
        self._stop_event = Event()
        self._thread: Optional[Thread] = None
        self._state: Dict[str, Any] = {}

    def update(self, state: Dict[str, Any]) -> None:
        """Merge new state into the health snapshot (thread-safe via GIL dict)."""
        self._state.update(state)

    def start(self) -> None:
        """Start the background reporter thread."""
        self._thread = Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Health reporter started: %s every %.1fs", self.path, self.interval_sec)

    def stop(self) -> None:
        """Signal shutdown and emit final state."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self.interval_sec + 2)
        self._write()

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            self._write()
            self._stop_event.wait(self.interval_sec)

    def _write(self) -> None:
        payload = {
            "timestamp_utc": time.time(),
            "uptime_s": time.monotonic(),
            **self._state,
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=None, default=str)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        except PermissionError:
            # Fallback to /tmp when not running under systemd RuntimeDirectory
            fallback = Path("/tmp") / self.path.name
            try:
                with open(fallback, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=None, default=str)
            except OSError as exc:
                logger.debug("Health write fallback failed: %s", exc)
        except OSError as exc:
            logger.error("Health write failed: %s", exc)
