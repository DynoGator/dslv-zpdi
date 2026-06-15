"""
SPEC-005A.TIMING-PPS — Kernel PPS edge listener via /dev/ppsX character device.

GPIO 18 is owned by the pps-gpio kernel driver (dtoverlay=pps-gpio,gpiopin=18).
The driver timestamps each rising edge in interrupt context and exposes events
through the Linux PPS character device. This module reads those events using
select.poll() + PPS_FETCH ioctl — the correct approach when the kernel holds
the GPIO line. Attempting to also claim GPIO 18 via libgpiod returns EBUSY.

PPS_FETCH ioctl constant derivation (aarch64, linux/pps.h):
    struct pps_ktime  = __s64 sec + __s32 nsec + __u32 flags = 16 bytes
    struct pps_fdata  = pps_ktime info + pps_ktime timeout   = 32 bytes
    PPS_FETCH         = _IOWR('p', 0xa4, struct pps_fdata)
                      = (3<<30)|(32<<16)|(0x70<<8)|0xa4 = 0xC02070A4
"""

from __future__ import annotations

import fcntl
import logging
import os
import select
import struct
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

        self._lock = threading.Lock()
        self._edge_event = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        # (monotonic_ns, kernel_pps_ns) — kernel_pps_ns is 0 if ioctl failed
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
        try:
            fd = os.open(self._device, os.O_RDWR)
        except OSError as exc:
            logger.error("PpsListener: cannot open %s: %s", self._device, exc)
            return

        poller = select.poll()
        poller.register(fd, select.POLLIN)

        try:
            while not self._stop.is_set():
                # 1.2 s poll timeout so _stop is checked promptly if PPS is absent
                events = poller.poll(1200)
                if not events:
                    continue

                # Snapshot CLOCK_MONOTONIC immediately after kernel wakeup.
                mono_ns = time.monotonic_ns()
                pps_kernel_ns = self._fetch_kernel_ts(fd)

                with self._lock:
                    self.last_edge_mono_ns = mono_ns
                    self._history.append((mono_ns, pps_kernel_ns))
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

    def _fetch_kernel_ts(self, fd: int) -> int:
        """
        SPEC-005A.TIMING-PPS — Fetch the kernel timestamp for the latest PPS edge.

        Issue PPS_FETCH ioctl to read the kernel-timestamped edge time.
        The timeout field is set to PPS_TIME_INVALID so the ioctl returns
        immediately with the most recent captured timestamp rather than
        blocking for the next pulse.

        Returns nanoseconds since UNIX epoch (CLOCK_REALTIME), or 0 on error.
        """
        try:
            request = struct.pack(
                _PPS_FDATA_FMT,
                0,
                0,
                0,  # info: sec=0, nsec=0, flags=0 (filled by kernel)
                0,
                0,
                _PPS_TIME_INVALID,  # timeout: sec=0, nsec=0, flags=PPS_TIME_INVALID
            )
            response = fcntl.ioctl(fd, _PPS_FETCH, request)
            sec, nsec, _ = struct.unpack_from("qiI", response, 0)
            return sec * 1_000_000_000 + nsec
        except OSError as exc:
            logger.debug("PpsListener: PPS_FETCH ioctl failed: %s", exc)
            return 0

    def _recompute_jitter(self) -> None:
        """
        SPEC-005A.TIMING-PPS — Recompute RMS PPS jitter from recent edge intervals.

        Compute RMS jitter from CLOCK_MONOTONIC inter-arrival intervals.
        Monotonic timestamps are immune to NTP slew, so this captures
        scheduling latency + GPS oscillator instability combined. Intervals
        outside 500 ms–2 s are treated as missed pulses and discarded.
        """
        mono_ts = [m for m, _ in self._history]
        if len(mono_ts) < 2:
            self.rms_jitter_ns = float("inf")
            return
        intervals = [mono_ts[i] - mono_ts[i - 1] for i in range(1, len(mono_ts))]
        valid = [iv for iv in intervals if 500_000_000 <= iv <= 2_000_000_000]
        if not valid:
            self.rms_jitter_ns = float("inf")
            return
        arr = np.array(valid, dtype=np.float64)
        deviations = np.abs(arr - 1_000_000_000.0)
        self.rms_jitter_ns = float(np.sqrt(np.mean(deviations**2)))
