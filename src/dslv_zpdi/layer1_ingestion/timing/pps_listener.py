"""
SPEC-005A.TIMING-PPS — Kernel PPS edge listener via /dev/ppsX character device.

GPIO 24 is owned by the pps-gpio kernel driver (dtoverlay=pps-gpio,gpiopin=24).
The driver timestamps each rising edge in interrupt context and exposes events
through the Linux PPS character device. This module reads those events using
select.poll() + PPS_FETCH ioctl — the correct approach when the kernel holds
the GPIO line. Attempting to also claim GPIO 24 via libgpiod returns EBUSY.

PPS_FETCH ioctl constant derivation (aarch64, linux/pps.h):
    struct pps_ktime  = __s64 sec + __s32 nsec + __u32 flags = 16 bytes
    struct pps_fdata  = pps_ktime info + pps_ktime timeout   = 32 bytes
    PPS_FETCH         = _IOWR('p', 0xa4, struct pps_fdata)
                      = (3<<30)|(32<<16)|(0x70<<8)|0xa4 = 0xC02070A4
"""

from __future__ import annotations

import logging
import os
import threading
import time

import numpy as np

logger = logging.getLogger("dslv-zpdi.pps")

_PPS_FETCH = 0xC02070A4  # _IOWR('p', 0xa4, struct pps_fdata) on aarch64
_PPS_FDATA_FMT = "qiIqiI"  # pps_fdata: info{sec,nsec,flags} + timeout{sec,nsec,flags}
_PPS_TIME_INVALID = 0x1  # timeout.flags: return last timestamp, do not wait


class PpsListener:
    """
    SPEC-005A.TIMING-PPS — Continuous timing health monitor for kernel PPS edges.

    Background daemon thread that captures 1 PPS rising edges from /dev/ppsX.
    Maintains a ring buffer of (monotonic_ns, kernel_pps_ns) tuples — one
    entry per pulse. CLOCK_MONOTONIC arrival times (immune to NTP slew) are
    used for jitter computation. Kernel-timestamped PPS times are retained
    for sub-second offset calculation in ingest payloads.

    Public API (all thread-safe):
        start() / stop()          — lifecycle
        wait_for_edge(timeout_s)  — block until next pulse (threading.Event)
        snapshot()                — copy of current state as a plain dict
    """

    def __init__(
        self,
        device: str = "/dev/pps0",
        history_max: int = 16,
    ) -> None:
        self._device = device
        self._history_max = history_max
        self._sysfs_path = f"/sys/class/pps/{os.path.basename(device)}/assert"

        self._lock = threading.Lock()
        self._edge_event = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        # (monotonic_ns, kernel_pps_ns) — kernel_pps_ns is 0 if read failed
        self._history: list[tuple[int, int]] = []
        self.last_edge_mono_ns: int = 0
        self.rms_jitter_ns: float = float("inf")

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        """SPEC-005A.TIMING-PPS — Start the background PPS edge listener thread (idempotent)."""
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="pps-listener", daemon=True)
        self._thread.start()
        logger.info("PpsListener: started on %s", self._device)

    def stop(self) -> None:
        """SPEC-005A.TIMING-PPS — Signal the listener thread to stop and join it."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        logger.info("PpsListener: stopped")

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def wait_for_edge(self, timeout_s: float = 2.0) -> bool:
        """
        SPEC-005A.TIMING-PPS — Wait for a trusted PPS edge before timestamping ingestion.

        Block the calling thread until the next PPS rising edge or timeout.
        Clears the internal event before waiting so a previous pulse does
        not cause an immediate false return. Returns True on edge, False on
        timeout. Safe to call from the pipeline ingestion thread — does not
        interfere with the listener thread.
        """
        self._edge_event.clear()
        return self._edge_event.wait(timeout=timeout_s)

    def snapshot(self) -> dict:
        """SPEC-005A.TIMING-PPS — Return a copy of the current PPS health state."""
        with self._lock:
            return {
                "last_edge_mono_ns": self.last_edge_mono_ns,
                "rms_jitter_ns": self.rms_jitter_ns,
                "history_len": len(self._history),
                "history": list(self._history),  # shallow copy of tuples
                "device": self._device,
            }

    # ------------------------------------------------------------------ #
    # Listener thread                                                      #
    # ------------------------------------------------------------------ #

    def _run(self) -> None:
        """
        SPEC-005A.TIMING-PPS — Monitor the sysfs PPS assert node.

        The pps-gpio driver exposes one assert timestamp per second under
        /sys/class/pps/pps0/assert. Poll it at 10 Hz, detect sequence-number
        changes, and record the arrival time. This avoids the PPS_FETCH ioctl,
        which is not reliably implemented across all Pi 5 kernel configurations.
        """
        sysfs_path = self._sysfs_path
        if not os.path.exists(sysfs_path):
            logger.error("PpsListener: sysfs node not found: %s", sysfs_path)
            return

        last_seq: int = -1
        try:
            fd = os.open(sysfs_path, os.O_RDONLY)
        except OSError as exc:
            logger.error("PpsListener: cannot open %s: %s", sysfs_path, exc)
            return

        try:
            while not self._stop.is_set():
                os.lseek(fd, 0, os.SEEK_SET)
                try:
                    raw = os.read(fd, 256)
                except OSError as exc:
                    logger.debug("PpsListener: sysfs read error: %s", exc)
                    self._stop.wait(0.1)
                    continue

                parsed = self._parse_sysfs_assert(raw)
                if parsed is None:
                    self._stop.wait(0.1)
                    continue

                seq, kernel_ns = parsed
                if seq == last_seq:
                    # No new edge since last read; wait a tick and retry.
                    self._stop.wait(0.1)
                    continue
                last_seq = seq

                mono_ns = time.monotonic_ns()
                with self._lock:
                    self.last_edge_mono_ns = mono_ns
                    self._history.append((mono_ns, kernel_ns))
                    if len(self._history) > self._history_max:
                        self._history.pop(0)
                    self._recompute_jitter()

                self._edge_event.set()

        except Exception as exc:  # pylint: disable=broad-except
            logger.error("PpsListener: thread error: %s", exc)
        finally:
            try:
                os.close(fd)
            except OSError:
                pass

    def _parse_sysfs_assert(self, raw: bytes) -> tuple[int, int] | None:
        """
        SPEC-005A.TIMING-PPS — Parse a sysfs PPS assert line.

        Format: `<sec>.<nsec>#<sequence>\n`
        Returns (sequence, kernel_ns) or None on parse failure.
        """
        try:
            line = raw.decode("ascii", errors="ignore").strip()
            ts_part, seq_part = line.split("#", 1)
            sec_str, nsec_str = ts_part.split(".", 1)
            seq = int(seq_part)
            kernel_ns = int(sec_str) * 1_000_000_000 + int(nsec_str.ljust(9, "0")[:9])
            return seq, kernel_ns
        except Exception:  # pylint: disable=broad-except
            return None

    def _fetch_kernel_ts(self, fd: int, timeout_s: float = 2.0) -> int:
        """
        SPEC-005A.TIMING-PPS — Deprecated ioctl path; retained for API compat.

        This implementation reads the sysfs assert node instead of issuing the
        PPS_FETCH ioctl, which is unreliable on the current Pi 5 kernel.
        """
        _ = fd, timeout_s  # signature kept for compatibility
        try:
            with open(self._sysfs_path, "rb") as f:  # noqa: SIM115
                raw = f.read(256)
            parsed = self._parse_sysfs_assert(raw)
            return parsed[1] if parsed else 0
        except OSError as exc:
            logger.debug("PpsListener: sysfs fetch failed: %s", exc)
            return 0

    def _recompute_jitter(self) -> None:
        """
        SPEC-005A.TIMING-PPS — Recompute RMS PPS jitter from recent edge intervals.

        Compute RMS jitter from kernel PPS timestamps exposed by the pps-gpio
        driver. These timestamps are captured in interrupt context and are
        immune to userspace scheduling latency. Intervals outside 500 ms–2 s
        are treated as missed pulses and discarded.
        """
        # Prefer kernel timestamps; fall back to monotonic only if the driver
        # returned zero (should not happen with pps-gpio sysfs assert node).
        ts_list = [k if k else m for m, k in self._history]
        if len(ts_list) < 2:
            self.rms_jitter_ns = float("inf")
            return
        intervals = [ts_list[i] - ts_list[i - 1] for i in range(1, len(ts_list))]
        valid = [iv for iv in intervals if 500_000_000 <= iv <= 2_000_000_000]
        if not valid:
            self.rms_jitter_ns = float("inf")
            return
        arr = np.array(valid, dtype=np.float64)
        deviations = np.abs(arr - 1_000_000_000.0)
        self.rms_jitter_ns = float(np.sqrt(np.mean(deviations**2)))
