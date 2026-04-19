"""SDR waterfall panel — ASCII color render of a rolling FFT."""

import math
import os
import random
import subprocess
import time

from rich.panel import Panel
from rich.text import Text


# 256-color grayscale-to-heat palette indices (low->high signal)
# Using ANSI truecolor escapes for smoother gradient.
_PALETTE_STOPS = [
    (0,   0,   0),      # black
    (0,   0,  64),      # deep blue
    (0,  64, 128),      # blue
    (0, 128, 128),      # teal
    (0, 180,  60),      # green
    (180, 200, 0),      # yellow-green
    (255, 180, 0),      # amber
    (255,  60, 0),      # red-orange
    (255, 255, 180),    # hot white
]


def _heat(v: float) -> str:
    """v in [0,1] → ANSI truecolor fg code."""
    v = max(0.0, min(1.0, v))
    n = len(_PALETTE_STOPS) - 1
    idx = v * n
    lo = int(idx)
    hi = min(lo + 1, n)
    t = idx - lo
    r = int(_PALETTE_STOPS[lo][0] * (1 - t) + _PALETTE_STOPS[hi][0] * t)
    g = int(_PALETTE_STOPS[lo][1] * (1 - t) + _PALETTE_STOPS[hi][1] * t)
    b = int(_PALETTE_STOPS[lo][2] * (1 - t) + _PALETTE_STOPS[hi][2] * t)
    return f"#{r:02x}{g:02x}{b:02x}"


class WaterfallPanel:
    """
    Simulator-mode waterfall: synthesized spectrum with moving carriers
    and broadband noise. Real-mode (future): sample hackrf_sweep output.
    """

    def __init__(self, width: int = 80, history: int = 12):
        self.width = width
        self.history = history
        self.rows: list[list[float]] = []
        self.center_hz = 100_000_000  # 100 MHz default
        self.span_hz = 20_000_000     # 20 MHz
        self.mode = "SWEEP"           # SWEEP | NARROW | SCOPE
        self._t0 = time.time()
        self._sim_carriers = [
            (0.25, 0.8, 0.0003),
            (0.55, 0.6, 0.0007),
            (0.78, 0.4, 0.0011),
        ]
        self._have_hackrf = self._probe_hackrf()

    def _probe_hackrf(self) -> bool:
        try:
            subprocess.check_output(
                ["hackrf_info"], stderr=subprocess.STDOUT, timeout=1, text=True
            )
            return True
        except Exception:
            return False

    def set_mode(self, mode: str):
        self.mode = mode

    def tune(self, center_hz: int, span_hz: int):
        self.center_hz = center_hz
        self.span_hz = span_hz

    def _sim_row(self) -> list[float]:
        """Build a simulated FFT row."""
        t = time.time() - self._t0
        row = []
        for i in range(self.width):
            x = i / (self.width - 1)
            # noise floor
            v = 0.08 + 0.05 * random.random()
            # drifting carriers
            for base_x, amp, drift in self._sim_carriers:
                cx = (base_x + drift * t) % 1.0
                d = abs(x - cx)
                v += amp * math.exp(-((d * 60) ** 2))
            # periodic pulses
            if int(t * 3) % 9 == 0 and i % 7 == 0:
                v += 0.3
            row.append(v)
        return row

    def _real_row(self) -> list[float]:
        """(Stub) Real hackrf_sweep bin — future wiring."""
        # Keep simple for now; real wiring shells out to hackrf_sweep and parses output.
        return self._sim_row()

    def tick(self):
        row = self._real_row() if self._have_hackrf and os.getenv(
            "DSLV_DASHBOARD_REAL_SDR") == "1" else self._sim_row()
        self.rows.append(row)
        if len(self.rows) > self.history:
            self.rows.pop(0)

    def _row_text(self, row: list[float]) -> Text:
        t = Text(no_wrap=True)
        for v in row:
            t.append("█", style=_heat(v))
        return t

    def render(self) -> Panel:
        self.tick()
        lines = Text()
        center_mhz = self.center_hz / 1e6
        span_mhz = self.span_hz / 1e6
        if not self.rows:
            lines.append("\n  [ buffering... ]\n")
        else:
            for row in reversed(self.rows):  # newest on top
                lines.append_text(self._row_text(row))
                lines.append("\n")

        # frequency axis
        lo = center_mhz - span_mhz / 2
        hi = center_mhz + span_mhz / 2
        mid = center_mhz
        axis = Text()
        left = f"{lo:.2f}"
        right = f"{hi:.2f}"
        mid_s = f"{mid:.2f}MHz"
        pad_total = self.width - len(left) - len(right) - len(mid_s)
        left_pad = max(0, pad_total // 2)
        right_pad = max(0, pad_total - left_pad)
        axis.append(left, style="dim bright_cyan")
        axis.append(" " * left_pad)
        axis.append(mid_s, style="bright_magenta")
        axis.append(" " * right_pad)
        axis.append(right, style="dim bright_cyan")
        lines.append_text(axis)

        sdr_source = "HACKRF" if (self._have_hackrf and os.getenv(
            "DSLV_DASHBOARD_REAL_SDR") == "1") else "SIM"
        title = (
            f"[bold bright_magenta]▓ WATERFALL ▓[/] "
            f"[dim]({self.mode} · {sdr_source} · "
            f"{span_mhz:.1f} MHz span)[/]"
        )
        return Panel(
            lines,
            title=title,
            border_style="bright_magenta",
            padding=(0, 1),
        )
