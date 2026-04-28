"""
SPEC-015 - Raspberry Pi Hardware Watchdog Pinger
Pets /dev/watchdog on every pipeline tick. System reboots if starved.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger("dslv-zpdi.watchdog")

WATCHDOG_DEVICE = "/dev/watchdog"
WATCHDOG_TIMEOUT_SEC = 15


class PiWatchdog:
    """SPEC-015 - bcm2835_wdt interface."""

    def __init__(self, device: str = WATCHDOG_DEVICE):
        self.device = device
        self._fd: Optional[int] = None

    def open(self) -> bool:
        """Open watchdog device. Returns False if unavailable."""
        try:
            self._fd = os.open(self.device, os.O_WRONLY)
            logger.info("Watchdog opened: %s", self.device)
            return True
        except OSError as exc:
            logger.warning("Watchdog unavailable (%s): %s", self.device, exc)
            return False

    def pet(self) -> None:
        """Write a keepalive to the watchdog. Must be called regularly."""
        if self._fd is not None:
            try:
                os.write(self._fd, b"\n")
            except OSError as exc:
                logger.error("Watchdog pet failed: %s", exc)

    def close(self, disable: bool = False) -> None:
        """Close watchdog handle.

        If disable=True, write 'V' to disable the watchdog before closing
        (magic close feature on Linux watchdog drivers).
        """
        if self._fd is not None:
            try:
                if disable:
                    os.write(self._fd, b"V")
                os.close(self._fd)
            except OSError as exc:
                logger.error("Watchdog close failed: %s", exc)
            finally:
                self._fd = None
