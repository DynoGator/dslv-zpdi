"""SDR waterfall panel — ASCII color render of a rolling FFT with Spectrum View.

Supports two data sources:
    * SIM      — synthesized spectrum with drifting carriers (default)
    * HACKRF   — live hackrf_sweep subprocess streamed in a thread

Toggle the source at runtime with the "real-sdr" keybinding (default 'r')
which flips the DSLV_DASHBOARD_REAL_SDR environment variable. The panel
reconciles subprocess lifecycle on each render.
"""

from __future__ import annotations

import math
import os
import random
import shutil
import subprocess
import threading
import time

from rich.markup import escape as _esc
from rich.panel import Panel
from rich.text import Text


_PALETTES = [
    # Classic Heat
    [
        (0,   0,   0),
        (0,   0,  64),
        (0,  64, 128),
        (0, 128, 128),
        (0, 180,  60),
        (180, 200, 0),
        (255, 180, 0),
        (255,  60, 0),
        (255, 255, 180),
    ],
    # Plasma-ish
    [
        (13, 8, 135),
        (71, 3, 161),
        (120, 28, 153),
        (160, 62, 116),
        (192, 99, 78),
        (219, 139, 44),
        (240, 184, 34),
        (250, 235, 37),
    ],
    # Viridis-ish
    [
        (68, 1, 84),
        (72, 35, 116),
        (64, 67, 135),
        (52, 94, 141),
        (41, 120, 142),
        (32, 143, 140),
        (34, 167, 132),
        (68, 190, 112),
        (121, 209, 81),
        (189, 222, 38),
        (253, 231, 37),
    ]
]

_PALETTE_IDX = 0

def _heat(v: float) -> str:
    """Map v in [0,1] to a truecolor hex string using the current palette."""
    v = max(0.0, min(1.0, v))
    stops = _PALETTES[_PALETTE_IDX % len(_PALETTES)]
    n = len(stops) - 1
    idx = v * n
    lo = int(idx)
    hi = min(lo + 1, n)
    t = idx - lo
    r = int(stops[lo][0] * (1 - t) + stops[hi][0] * t)
    g = int(stops[lo][1] * (1 - t) + stops[hi][1] * t)
    b = int(stops[lo][2] * (1 - t) + stops[hi][2] * t)
    return f"#{r:02x}{g:02x}{b:02x}"


class HackrfSweepStream:
    """
    Background thread wrapping `hackrf_sweep` stdout.
    """

    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._latest_row: list[float] | None = None
        self._last_error: str | None = None
        self._sweeps = 0
        self._params: dict = {}

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def last_error(self) -> str | None:
        return self._last_error

    def sweeps(self) -> int:
        return self._sweeps

    def start(
        self,
        center_hz: int,
        span_hz: int,
        width: int,
        lna: int = 24,
        vga: int = 20,
        amp: bool = False,
    ) -> bool:
        self.stop()
        freq_min_mhz = max(1, int((center_hz - span_hz / 2) / 1e6))
        freq_max_mhz = max(freq_min_mhz + 1, int((center_hz + span_hz / 2) / 1e6))
        bin_width_hz = max(2500, int(span_hz / max(width, 1)))
        self._params = {
            "center_hz": center_hz,
            "span_hz": span_hz,
            "width": width,
            "lna": lna,
            "vga": vga,
            "amp": amp,
            "freq_min_mhz": freq_min_mhz,
            "freq_max_mhz": freq_max_mhz,
            "bin_width_hz": bin_width_hz,
        }
        cmd = [
            "hackrf_sweep",
            "-f", f"{freq_min_mhz}:{freq_max_mhz}",
            "-w", str(bin_width_hz),
            "-l", str(lna),
            "-g", str(vga),
        ]
        if amp:
            cmd += ["-a", "1"]
        self._stop.clear()
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except Exception as e:
            self._last_error = f"spawn failed: {e}"
            self._proc = None
            return False
        self._last_error = None
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop.set()
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=1.0)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        self._proc = None
        self._thread = None

    def _reader(self):
        assert self._proc is not None
        assert self._proc.stdout is not None
        width = int(self._params["width"])
        freq_min_hz = self._params["freq_min_mhz"] * 1_000_000
        freq_max_hz = self._params["freq_max_mhz"] * 1_000_000
        span_hz = max(1, freq_max_hz - freq_min_hz)
        accum = [-120.0] * width  # dBm
        last_low = None
        try:
            for line in self._proc.stdout:
                if self._stop.is_set():
                    break
                line = line.strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 7:
                    continue
                try:
                    hz_low = float(parts[2])
                    hz_high = float(parts[3])
                    bin_w = float(parts[4])
                    powers = [float(x) for x in parts[6:]]
                except ValueError:
                    continue
                if last_low is not None and hz_low < last_low:
                    self._publish(accum)
                    accum = [-120.0] * width
                last_low = hz_low
                for i, p in enumerate(powers):
                    freq = hz_low + i * bin_w
                    if freq < freq_min_hz or freq > freq_max_hz:
                        continue
                    col = int((freq - freq_min_hz) / span_hz * (width - 1))
                    if 0 <= col < width:
                        if p > accum[col]:
                            accum[col] = p
            self._publish(accum)
        except Exception as e:
            self._last_error = f"reader: {e}"
        finally:
            if self._proc and self._proc.stderr:
                try:
                    err = self._proc.stderr.read()
                    if err and not self._last_error:
                        self._last_error = err.strip().splitlines()[-1][:120]
                except Exception:
                    pass

    def _publish(self, dbm_row: list[float]):
        if not dbm_row:
            return
        with self._lock:
            self._latest_row = dbm_row
        self._sweeps += 1

    def pop_row(self) -> list[float] | None:
        with self._lock:
            row = self._latest_row
            self._latest_row = None
        return row


def hackrf_present() -> bool:
    try:
        subprocess.check_output(
            ["hackrf_info"], stderr=subprocess.STDOUT, timeout=2, text=True
        )
        return True
    except Exception:
        return False


class WaterfallPanel:
    """
    Rolling FFT waterfall + Spectrum view.
    """

    MODES = ("SWEEP", "NARROW", "SCOPE")

    def __init__(
        self,
        width: int = 80,
        history: int = 12,
        mode: str = "SWEEP",
        center_hz: int = 100_000_000,
        span_hz: int = 20_000_000,
        border_style: str = "bright_magenta",
        lna_gain: int = 24,
        vga_gain: int = 20,
        amp_enabled: bool = False,
    ):
        self.width = max(20, width)
        self.history = max(4, history)
        self.rows: list[list[float]] = []  # Store normalized [0,1] rows
        self.center_hz = center_hz
        self.span_hz = span_hz
        self.mode = mode
        self.border_style = border_style
        self.lna_gain = lna_gain
        self.vga_gain = vga_gain
        self.amp_enabled = amp_enabled
        self.dbm_floor = -90.0
        self.dbm_ceil = -20.0
        self.show_spectrum = True
        
        self._t0 = time.time()
        self._sim_carriers = [
            (0.25, 0.80, 0.00030),
            (0.55, 0.60, 0.00070),
            (0.78, 0.40, 0.00110),
        ]
        self._have_hackrf = hackrf_present()
        self._stream = HackrfSweepStream()
        self._want_real = False
        self._last_source = "SIM"
        # Raw dBm view of the latest row (real or simulated). Consumed by the
        # RF anomaly panel so it can report peak dBm, noise floor, etc.
        self.last_dbm_row: list[float] | None = None
        self._anomaly_count_recent = 0

    def cycle_palette(self):
        global _PALETTE_IDX
        _PALETTE_IDX += 1

    def set_mode(self, mode: str):
        if mode in self.MODES:
            self.mode = mode
            self._apply_mode_defaults()
            self._restart_stream_if_running()

    def _apply_mode_defaults(self):
        if self.mode == "SWEEP":
            self.span_hz = max(self.span_hz, 20_000_000)
        elif self.mode == "NARROW":
            self.span_hz = min(self.span_hz, 5_000_000)
        elif self.mode == "SCOPE":
            self.span_hz = min(self.span_hz, 2_000_000)

    def tune(self, delta_hz: int):
        self.center_hz = max(1_000_000, int(self.center_hz + delta_hz))
        self._restart_stream_if_running()

    def zoom(self, factor: float):
        new = max(1_000_000, min(500_000_000, int(self.span_hz * factor)))
        self.span_hz = new
        self._restart_stream_if_running()

    def adjust_floor(self, delta: float):
        self.dbm_floor = max(-150.0, min(self.dbm_ceil - 5.0, self.dbm_floor + delta))

    def adjust_ceil(self, delta: float):
        self.dbm_ceil = max(self.dbm_floor + 5.0, min(0.0, self.dbm_ceil + delta))

    def adjust_gain(self, step: int):
        steps = [0, 8, 16, 24, 32, 40]
        try:
            i = steps.index(self.lna_gain)
        except ValueError:
            i = 0
        i = max(0, min(len(steps) - 1, i + step))
        self.lna_gain = steps[i]
        self._restart_stream_if_running()

    def cycle_gain(self):
        steps = [0, 8, 16, 24, 32, 40]
        try:
            i = steps.index(self.lna_gain)
        except ValueError:
            i = 0
        self.lna_gain = steps[(i + 1) % len(steps)]
        self._restart_stream_if_running()

    def toggle_amp(self):
        self.amp_enabled = not self.amp_enabled
        self._restart_stream_if_running()

    def resize(self, width: int):
        w = max(20, int(width))
        if w != self.width:
            self.width = w
            self.rows = []
            self._restart_stream_if_running()

    def shutdown(self):
        self._stream.stop()

    def _sync_stream(self):
        want_real = (
            self._have_hackrf
            and os.getenv("DSLV_DASHBOARD_REAL_SDR") == "1"
        )
        if want_real and not self._stream.is_running():
            self._stream.start(
                center_hz=self.center_hz,
                span_hz=self.span_hz,
                width=self.width,
                lna=self.lna_gain,
                vga=self.vga_gain,
                amp=self.amp_enabled,
            )
        elif not want_real and self._stream.is_running():
            self._stream.stop()
        self._want_real = want_real

    def _restart_stream_if_running(self):
        if self._stream.is_running():
            self._stream.start(
                center_hz=self.center_hz,
                span_hz=self.span_hz,
                width=self.width,
                lna=self.lna_gain,
                vga=self.vga_gain,
                amp=self.amp_enabled,
            )

    def _normalize(self, row: list[float]) -> list[float]:
        return [max(0.0, min(1.0, (v - self.dbm_floor) / (self.dbm_ceil - self.dbm_floor))) for v in row]

    def _sim_row(self) -> list[float]:
        t = time.time() - self._t0
        row = []
        for i in range(self.width):
            x = i / (self.width - 1)
            v = 0.08 + 0.05 * random.random()
            for base_x, amp, drift in self._sim_carriers:
                cx = (base_x + drift * t) % 1.0
                d = abs(x - cx)
                v += amp * math.exp(-((d * 60) ** 2))
            if int(t * 3) % 9 == 0 and i % 7 == 0:
                v += 0.3
            row.append(v)
        return row

    def tick(self):
        self._sync_stream()
        row: list[float] | None = None
        raw_dbm: list[float] | None = None
        source = "SIM"
        if self._want_real:
            raw_row = self._stream.pop_row()
            if raw_row is not None:
                source = "HACKRF"
                raw_dbm = raw_row
                row = self._normalize(raw_row)
        if row is None:
            row = self._sim_row()
            # Synthesize a plausible dBm trace from the normalized sim row so
            # the anomaly panel still has something meaningful to display.
            raw_dbm = [self.dbm_floor + v * (self.dbm_ceil - self.dbm_floor) for v in row]
            if self._want_real:
                source = "HACKRF-WAIT"
        self._last_source = source
        self.last_dbm_row = raw_dbm
        if raw_dbm:
            floor = self._estimate_floor(raw_dbm)
            self._anomaly_count_recent = sum(1 for v in raw_dbm if v >= floor + 10.0)
        self.rows.append(row)
        if len(self.rows) > self.history:
            self.rows.pop(0)

    @staticmethod
    def _estimate_floor(row: list[float]) -> float:
        """Median is a robust noise-floor estimate against a few strong carriers."""
        s = sorted(row)
        return s[len(s) // 2]

    def metrics(self) -> dict:
        """Snapshot of current spectrum metrics for the RF anomaly panel."""
        row = self.last_dbm_row
        if not row:
            return {
                "have_data": False,
                "peak_dbm": float("nan"),
                "peak_freq_hz": float("nan"),
                "noise_floor_dbm": float("nan"),
                "snr_db": float("nan"),
                "anomaly_count": 0,
                "source": self._last_source,
                "span_hz": self.span_hz,
                "center_hz": self.center_hz,
                "sweeps": self._stream.sweeps(),
            }
        peak_idx = max(range(len(row)), key=lambda i: row[i])
        peak_v = row[peak_idx]
        floor = self._estimate_floor(row)
        lo_hz = self.center_hz - self.span_hz / 2
        bin_hz = self.span_hz / max(1, len(row) - 1)
        peak_freq_hz = lo_hz + peak_idx * bin_hz
        return {
            "have_data": True,
            "peak_dbm": peak_v,
            "peak_freq_hz": peak_freq_hz,
            "noise_floor_dbm": floor,
            "snr_db": peak_v - floor,
            "anomaly_count": self._anomaly_count_recent,
            "source": self._last_source,
            "span_hz": self.span_hz,
            "center_hz": self.center_hz,
            "sweeps": self._stream.sweeps(),
        }

    def _spectrum_text(self, row: list[float], height: int = 5) -> Text:
        t = Text()
        for y in range(height, 0, -1):
            threshold = y / height
            for v in row:
                if v >= threshold:
                    t.append("█", style=_heat(v))
                elif v >= threshold - (1/height/2):
                    t.append("▄", style=_heat(v))
                else:
                    t.append(" ", style="dim")
            t.append("\n")
        return t

    def _row_text(self, row: list[float]) -> Text:
        t = Text(no_wrap=True)
        if len(row) != self.width and len(row) > 1:
            scale = (len(row) - 1) / (self.width - 1) if self.width > 1 else 1
            resampled = [row[min(len(row) - 1, int(i * scale))] for i in range(self.width)]
            row = resampled
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
            if self.show_spectrum:
                lines.append_text(self._spectrum_text(self.rows[-1]))
                lines.append("─" * self.width, style="dim")
                lines.append("\n")
            
            for row in reversed(self.rows):
                lines.append_text(self._row_text(row))
                lines.append("\n")

        lo = center_mhz - span_mhz / 2
        hi = center_mhz + span_mhz / 2
        axis = Text()
        axis.append(f"{lo:.2f}", style="dim bright_cyan")
        mid_s = f"{center_mhz:.2f}MHz"
        pad = max(0, self.width - len(f"{lo:.2f}") - len(f"{hi:.2f}") - len(mid_s))
        axis.append(" " * (pad // 2))
        axis.append(mid_s, style="bright_magenta")
        axis.append(" " * (pad - pad // 2))
        axis.append(f"{hi:.2f}", style="dim bright_cyan")
        lines.append_text(axis)

        src_label = {
            "HACKRF": "HACKRF",
            "HACKRF-WAIT": "HACKRF…",
            "SIM": "SIM",
        }.get(self._last_source, "SIM")
        err = self._stream.last_error()
        err_suffix = f" · err: {_esc(err)}" if (self._want_real and err) else ""
        gain_info = f" · floor {self.dbm_floor:.0f} ceil {self.dbm_ceil:.0f}"
        gain_suffix = (
            f" · lna {self.lna_gain}dB vga {self.vga_gain}dB amp {'ON' if self.amp_enabled else 'off'}"
            if self._want_real
            else ""
        )
        sweeps = self._stream.sweeps()
        sweep_suffix = f" · sweeps {sweeps}" if self._want_real else ""
        title = (
            f"[bold {self.border_style}]▓ WATERFALL + SPECTRUM ▓[/] "
            f"[dim]({self.mode} · {src_label} · "
            f"{span_mhz:.1f}MHz BW{gain_info}{gain_suffix}{sweep_suffix}{err_suffix})[/]"
        )
        return Panel(lines, title=title, border_style=self.border_style, padding=(0, 1))
