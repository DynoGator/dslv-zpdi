"""SDR waterfall panel — ASCII color render of a rolling FFT with Spectrum View.

Supports two data sources:
    * SIM      — synthesized spectrum with drifting carriers (default)
    * PlutoSDRplus   — live PlutoSDRplus_sweep subprocess streamed in a thread

Toggle the source at runtime with the "real-sdr" keybinding (default 'r')
which flips the DSLV_DASHBOARD_REAL_SDR environment variable. The panel
reconciles subprocess lifecycle on each render.
"""

from __future__ import annotations

import math
import os
import random
import subprocess
import threading
import time

import numpy as np
from rich.markup import escape as _esc
from rich.panel import Panel
from rich.text import Text

from dslv_zpdi.layer1_ingestion.sdr.capabilities import CaptureProfile
from dslv_zpdi.layer1_ingestion.sdr.pluto_iio import PlutoIioBackend

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

_PALETTE_IDX = 1


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


class PlutoSDRplusSweepStream:
    """
    Background thread wrapping PlutoIioBackend for live sweeps.
    """

    def __init__(self):
        self._thread = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._latest_row = None
        self._last_error = None
        self._sweeps = 0
        self._params = {}
        self._backend = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

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
        self._params = {
            "center_hz": center_hz,
            "span_hz": span_hz,
            "width": width,
        }
        self._stop.clear()

        try:
            import os

            from dslv_zpdi.layer1_ingestion.sdr.pluto_iio import PlutoIioBackend
            sdr_uri = os.environ.get("ZPDI_SDR_URI", "ip:192.168.2.1")
            self._backend = PlutoIioBackend(uri=sdr_uri)
        except Exception as e:
            self._last_error = f"PlutoIioBackend failed: {e}"
            self._backend = None
            return False

        self._last_error = None
        import threading
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop.set()
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.join(timeout=2.0)

        backend = self._backend
        self._backend = None
        if backend is not None:
            try:
                pass
            except Exception:
                pass

    def _reader(self):
        import time

        import numpy as np

        from dslv_zpdi.layer1_ingestion.sdr.capabilities import CaptureProfile
        try:
            while not self._stop.is_set():
                if self._backend is None:
                    break

                center_hz = self._params["center_hz"]
                span_hz = self._params["span_hz"]
                width = self._params["width"]

                try:
                    cprof = CaptureProfile(
                        center_frequency_hz=center_hz,
                        sample_rate_sps=max(int(span_hz), 2083334),
                        bandwidth_hz=span_hz,
                        gain_db=20,
                        num_samples=2048,
                    )
                    cap = self._backend.capture(cprof)
                    raw_iq = cap.samples
                    window = np.hanning(len(raw_iq))
                    spectrum = np.fft.fftshift(np.fft.fft(raw_iq * window))
                    power = 20 * np.log10(np.abs(spectrum) + 1e-9)

                    binned = np.interp(np.linspace(0, len(power)-1, width), np.arange(len(power)), power)
                    row = [float(p) - 80.0 for p in binned]

                    self._publish(row)
                    time.sleep(0.1)
                except Exception as e:
                    self._last_error = f"read error: {e}"
                    time.sleep(0.5)
        except Exception as e:
            self._last_error = f"reader thread: {e}"

    def _publish(self, dbm_row):
        if not dbm_row:
            return
        with self._lock:
            self._latest_row = dbm_row
        self._sweeps += 1

    def pop_row(self):
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
        proc = self._proc
        thread = self._thread
        self._proc = None
        self._thread = None
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=1.0)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        if thread is not None:
            thread.join(timeout=2.0)

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
                    float(parts[3])  # validate hz_high column without binding it
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


class PlutoSweepStream:
    """
    Background capture thread for PlutoSDR+ devices using the native libiio
    backend. Computes a power spectrum row suitable for the waterfall panel.

    The values are approximate dBFS (dB relative to full-scale). A calibration
    offset can be applied later once the receiver chain is characterised.
    """

    def __init__(self):
        self._backend: PlutoIioBackend | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._latest_row: list[float] | None = None
        self._last_error: str | None = None
        self._sweeps = 0
        self._params: dict = {}

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

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
        # vga/amp are HackRF-specific; ignore them for Pluto.
        del vga, amp
        self.stop()
        self._last_error = None

        uri = os.environ.get("DSLV_SDR_URI", "auto")
        try:
            backend = PlutoIioBackend(uri=uri)
        except Exception as exc:
            self._last_error = f"pluto open failed: {exc}"
            return False

        caps = backend.discover()
        min_rate = caps.available_sample_rates_sps[0] if caps.available_sample_rates_sps else 2_083_333
        max_rate = caps.max_sample_rate_sps or 61_440_000
        sample_rate = max(min_rate, min(max_rate, span_hz))

        # Request a few more FFT bins than display columns for smooth resampling.
        num_samples = max(4096, width * 4)
        # AD936x buffers prefer powers of two.
        num_samples = 1 << (num_samples - 1).bit_length()

        profile = CaptureProfile(
            center_frequency_hz=center_hz,
            sample_rate_sps=sample_rate,
            bandwidth_hz=sample_rate,
            gain_db=float(lna),
            gain_mode="manual",
            receive_channels=(0,),
            transmit_enabled=False,
            buffer_samples=num_samples,
            num_samples=num_samples,
            external_clock_configured=False,
        )

        self._params = {
            "center_hz": center_hz,
            "span_hz": span_hz,
            "width": width,
            "lna": lna,
            "sample_rate": sample_rate,
            "profile": profile,
        }
        self._backend = backend
        self._stop.clear()
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop.set()
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.join(timeout=2.0)
        backend = self._backend
        self._backend = None
        if backend is not None:
            try:
                backend.close()
            except Exception:
                pass

    def _reader(self):
        while not self._stop.is_set():
            try:
                backend = self._backend
                if backend is None:
                    break
                profile = self._params["profile"]
                width = int(self._params["width"])
                result = backend.capture(profile)
                if result.samples_received < width:
                    continue
                row = self._spectrum_row(result.samples, result.center_frequency_hz, result.effective_sample_rate_sps or profile.sample_rate_sps, width)
                self._publish(row)
            except Exception as exc:
                self._last_error = f"capture: {exc}"
                # Back off briefly to avoid tight error loops.
                time.sleep(0.5)

    @staticmethod
    def _spectrum_row(samples: np.ndarray, center_hz: float, sample_rate: float, width: int) -> list[float]:
        # One-sided power spectrum via FFT; dBFS for now.
        n = len(samples)
        fft = np.fft.fftshift(np.fft.fft(samples))
        # dBFS: 20*log10(|fft|/(n*FS)). Pluto samples are raw AD9361 12-bit
        # ADC counts (full scale ±2047), so divide by 2048.0 as well — without
        # this the spectrum is offset by +66 dB and every bin saturates the
        # palette ceiling. A full-scale tone approaches 0 dBFS.
        power = 20.0 * np.log10(np.maximum(np.abs(fft) / (max(1, n) * 2048.0), 1e-12))

        # Resample the FFT to `width` columns using max-hold.
        if len(power) == width:
            return power.tolist()
        if len(power) < width:
            # Stretch with linear interpolation.
            indices = np.linspace(0, len(power) - 1, width)
            return np.interp(indices, np.arange(len(power)), power).tolist()

        row = []
        scale = len(power) / width
        for i in range(width):
            start = int(i * scale)
            end = max(start + 1, int((i + 1) * scale))
            row.append(float(np.max(power[start:end])))
        return row

    def _publish(self, row: list[float]):
        if not row:
            return
        with self._lock:
            self._latest_row = row
        self._sweeps += 1

    def pop_row(self) -> list[float] | None:
        with self._lock:
            row = self._latest_row
            self._latest_row = None
        return row


class WaterfallPanel:
    """
    Rolling FFT waterfall + Spectrum view.
    """

    MODES = ("SWEEP", "NARROW", "SCOPE")

    def __init__(
        self,
        width: int = 80,
        history: int = 24,  # Increased default from 12
        mode: str = "SWEEP",
        center_hz: int = 100_000_000,
        span_hz: int = 20_000_000,
        border_style: str = "bright_magenta",
        lna_gain: int = 24,
        vga_gain: int = 20,
        amp_enabled: bool = False,
        compact: bool = False,
    ):
        self.width = max(20, width)
        self.history = max(10, history)  # Ensured minimum for usability
        self.rows: list[list[float]] = []  # Store normalized [0,1] rows
        self.peak_hold: list[float] = [0.0] * self.width
        self.center_hz = center_hz
        self.span_hz = span_hz
        self.mode = mode
        self.border_style = border_style
        self.lna_gain = lna_gain
        self.vga_gain = vga_gain
        self.amp_enabled = amp_enabled
        self.dbm_floor = -75.0
        self.dbm_ceil = -70.0
        self.show_spectrum = True
        self.compact = compact
        self.modulation = "RAW"

        self._t0 = time.time()
        self._sim_carriers = [
            (0.25, 0.80, 0.00030),
            (0.55, 0.60, 0.00070),
            (0.78, 0.40, 0.00110),
        ]
        self._have_hackrf = hackrf_present()
        self._hackrf_stream = HackrfSweepStream()
        self._pluto_stream = PlutoSDRplusSweepStream()
        self._active_real: str | None = None  # 'pluto' or 'hackrf' when live
        self._want_real = True
        self._stream_retry_at = 0.0
        self._last_source = "SIM"
        # Raw dBm view of the latest row (real or simulated). Consumed by the
        # RF anomaly panel so it can report peak dBm, noise floor, etc.
        self.last_dbm_row: list[float] | None = None
        self._anomaly_count_recent = 0
        # Data production runs on a daemon thread (mirrors LogPanel) so the
        # render path stays pure drawing. _rows_lock guards rows, peak_hold,
        # last_dbm_row and the anomaly counters shared with the UI thread;
        # _stream_lock serializes stream start/stop against keypress-driven
        # restarts from the UI thread.
        self._rows_lock = threading.Lock()
        self._stream_lock = threading.Lock()
        self._tick_thread: threading.Thread | None = None
        self._tick_stop = threading.Event()
        self._tick_started = False

    def cycle_palette(self):
        global _PALETTE_IDX
        _PALETTE_IDX += 1

    @property
    def palette_name(self) -> str:
        names = ["HEAT", "PLASMA", "VIRIDIS"]
        return names[_PALETTE_IDX % len(_PALETTES)]

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

    def cycle_vga_gain(self):
        steps = [0, 8, 16, 24, 32, 40, 48, 56, 62]
        try:
            i = steps.index(self.vga_gain)
        except ValueError:
            i = 0
        self.vga_gain = steps[(i + 1) % len(steps)]
        self._restart_stream_if_running()

    def cycle_modulation(self):
        mods = ["RAW-SWEEP", "AM", "NFM", "WFM", "LSB", "USB", "CW"]
        try:
            i = mods.index(getattr(self, "modulation", "RAW-SWEEP"))
        except ValueError:
            i = 0
        self.modulation = mods[(i + 1) % len(mods)]

    def toggle_amp(self):
        self.amp_enabled = not self.amp_enabled
        self._restart_stream_if_running()

    def resize(self, width: int):
        w = max(20, int(width))
        if w != self.width:
            self.width = w
            with self._rows_lock:
                self.rows = []
                self.peak_hold = [0.0] * self.width
            self._restart_stream_if_running()

    def start(self):
        """Start the background tick thread (idempotent)."""
        if self._tick_started:
            return
        self._tick_started = True
        self._tick_thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._tick_thread.start()

    def stop(self):
        self._tick_stop.set()

    def _tick_loop(self):
        # Scroll rate is data-driven: real rows are consumed as fast as they
        # arrive; when no row is available, back off briefly instead of
        # spinning.
        while not self._tick_stop.is_set():
            try:
                got_row = self.tick()
            except Exception:
                got_row = False
            if not got_row:
                time.sleep(0.04)

    def shutdown(self):
        self.stop()
        self._hackrf_stream.stop()
        self._pluto_stream.stop()

    def _sync_stream(self):
        with self._stream_lock:
            self._sync_stream_locked()

    def _sync_stream_locked(self):
        want_real = os.getenv("DSLV_DASHBOARD_REAL_SDR") == "1"
        if not want_real:
            if self._active_real is not None:
                self._hackrf_stream.stop()
                self._pluto_stream.stop()
                self._active_real = None
            self._want_real = False
            return

        # If a real stream is already running, leave it alone (user can toggle
        # real mode off/on to force a re-scan).
        if self._active_real == "pluto" and self._pluto_stream.is_running():
            self._want_real = True
            return
        if self._active_real == "hackrf" and self._hackrf_stream.is_running():
            self._want_real = True
            return

        now = time.time()
        if now - self._stream_retry_at < 5.0:
            self._want_real = True
            return
        self._stream_retry_at = now

        # Prefer PlutoSDR+ (canonical Tier-1), fall back to HackRF (legacy).
        self._hackrf_stream.stop()
        self._pluto_stream.stop()
        if self._pluto_stream.start(
            center_hz=self.center_hz,
            span_hz=self.span_hz,
            width=self.width,
            lna=self.lna_gain,
            vga=self.vga_gain,
            amp=self.amp_enabled,
        ):
            self._active_real = "pluto"
        elif self._have_hackrf and self._hackrf_stream.start(
            center_hz=self.center_hz,
            span_hz=self.span_hz,
            width=self.width,
            lna=self.lna_gain,
            vga=self.vga_gain,
            amp=self.amp_enabled,
        ):
            self._active_real = "hackrf"
        else:
            self._active_real = None
        self._want_real = want_real

    def _restart_stream_if_running(self):
        with self._stream_lock:
            self._restart_stream_if_running_locked()

    def _restart_stream_if_running_locked(self):
        if self._active_real == "pluto" and self._pluto_stream.is_running():
            self._pluto_stream.start(
                center_hz=self.center_hz,
                span_hz=self.span_hz,
                width=self.width,
                lna=self.lna_gain,
                vga=self.vga_gain,
                amp=self.amp_enabled,
            )
        elif self._active_real == "hackrf" and self._hackrf_stream.is_running():
            self._hackrf_stream.start(
                center_hz=self.center_hz,
                span_hz=self.span_hz,
                width=self.width,
                lna=self.lna_gain,
                vga=self.vga_gain,
                amp=self.amp_enabled,
            )

    def _normalize(self, row: list[float]) -> list[float]:
        span = self.dbm_ceil - self.dbm_floor
        if span <= 0:
            return [0.5] * len(row)
        return [max(0.0, min(1.0, (v - self.dbm_floor) / span)) for v in row]

    def _sim_row(self) -> list[float]:
        t = time.time() - self._t0
        row = []
        for i in range(self.width):
            x = i / max(1, self.width - 1)
            v = 0.08 + 0.05 * random.random()
            for base_x, amp, drift in self._sim_carriers:
                cx = (base_x + drift * t) % 1.0
                d = abs(x - cx)
                v += amp * math.exp(-((d * 60) ** 2))
            if int(t * 3) % 9 == 0 and i % 7 == 0:
                v += 0.3
            row.append(v)
        return row

    def tick(self) -> bool:
        """Produce one waterfall row. Returns True when a real stream row was
        consumed (False for sim/fallback rows). Runs on the tick thread."""
        self._sync_stream()
        row: list[float] | None = None
        raw_dbm: list[float] | None = None
        source = "SIM"
        got_row = False
        if self._want_real:
            if self._active_real == "pluto":
                raw_row = self._pluto_stream.pop_row()
                if raw_row is not None:
                    source = "PLUTO"
                    raw_dbm = raw_row
                    row = self._normalize(raw_row)
                    got_row = True
                    self._last_row_time = time.time()
            elif self._active_real == "hackrf":
                raw_row = self._hackrf_stream.pop_row()
                if raw_row is not None:
                    source = "HACKRF"
                    raw_dbm = raw_row
                    row = self._normalize(raw_row)
                    got_row = True
                    self._last_row_time = time.time()
        if row is None:
            if self._want_real:
                now = time.time()
                if not hasattr(self, "_last_row_time"):
                    self._last_row_time = now
                if now - self._last_row_time > 1.0:
                    self._last_source = f"{self._active_real.upper()}-WAIT" if self._active_real else "WAIT"
                return False
            else:
                row = self._sim_row()
                raw_dbm = [self.dbm_floor + v * (self.dbm_ceil - self.dbm_floor) for v in row]
                source = "SIM"
        else:
            self._last_row_time = time.time()

        self._last_source = source

        with self._rows_lock:
            self.last_dbm_row = raw_dbm
            if raw_dbm:
                floor = self._estimate_floor(raw_dbm)
                self._anomaly_count_recent = sum(1 for v in raw_dbm if v >= floor + 10.0)

            if row:
                if len(self.peak_hold) != len(row):
                    self.peak_hold = list(row)
                else:
                    for i in range(len(row)):
                        self.peak_hold[i] = max(row[i], self.peak_hold[i] * 0.98)

            self.rows.append(row)
            if len(self.rows) > self.history:
                self.rows.pop(0)
        return got_row

    @staticmethod
    def _estimate_floor(row: list[float]) -> float:
        """Median is a robust noise-floor estimate against a few strong carriers."""
        s = sorted(row)
        return s[len(s) // 2]

    def metrics(self) -> dict:
        """Snapshot of current spectrum metrics for the RF anomaly panel."""
        with self._rows_lock:
            row = list(self.last_dbm_row) if self.last_dbm_row else None
            anomaly_count = self._anomaly_count_recent
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
                "sweeps": (
                self._pluto_stream.sweeps() if self._active_real == "pluto"
                else self._hackrf_stream.sweeps() if self._active_real == "hackrf"
                else 0
            ),
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
            "anomaly_count": anomaly_count,
            "source": self._last_source,
            "span_hz": self.span_hz,
            "center_hz": self.center_hz,
            "sweeps": (
                self._pluto_stream.sweeps() if self._active_real == "pluto"
                else self._hackrf_stream.sweeps() if self._active_real == "hackrf"
                else 0
            ),
        }

    def _active_stream(self):
        if self._active_real == "pluto":
            return self._pluto_stream
        if self._active_real == "hackrf":
            return self._hackrf_stream
        return None

    def _spectrum_text(self, row: list[float], peak_hold: list[float], height: int = 5) -> Text:
        t = Text()
        # Estimate noise floor for the normalized row
        floor_val = sum(sorted(row)[:len(row)//4]) / (len(row)//4 + 1)

        for y in range(height, 0, -1):
            threshold = y / height
            for i, v in enumerate(row):
                pk = peak_hold[i]
                if v >= threshold:
                    t.append("█", style=_heat(v))
                elif pk >= threshold:
                    # Peak hold marker
                    t.append("·", style="bright_red" if pk > 0.7 else "red")
                elif v >= threshold - (1/height/2):
                    t.append("▄", style=_heat(v))
                elif floor_val >= threshold - (1/height/2):
                    t.append("_", style="dim blue")
                else:
                    t.append(" ", style="dim")
            t.append("\n")
        return t

    def _row_text(self, row: list[float]) -> Text:
        t = Text(no_wrap=True)
        if len(row) != self.width and len(row) > 1:
            # Better resampling: use max to avoid missing peaks
            resampled = []
            scale = len(row) / self.width
            for i in range(self.width):
                start = int(i * scale)
                end = max(start + 1, int((i + 1) * scale))
                resampled.append(max(row[start:end]))
            row = resampled
        for v in row:
            t.append("█", style=_heat(v))
        return t

    def render(self, compact: bool | None = None) -> Panel:
        if compact is not None:
            self.compact = compact
        # Data production lives on the tick thread; render is pure drawing
        # over a consistent snapshot of the shared state.
        self.start()
        with self._rows_lock:
            rows = list(self.rows)
            peak_hold = list(self.peak_hold)
        lines = Text()
        center_mhz = self.center_hz / 1e6
        span_mhz = self.span_hz / 1e6

        if not rows:
            lines.append("\n  [ buffering spectrum... ]\n")
        else:
            if self.show_spectrum:
                spec_h = 3 if self.compact else 5
                lines.append_text(self._spectrum_text(rows[-1], peak_hold, height=spec_h))
                lines.append("─" * self.width, style="dim")
                lines.append("\n")

            # Use as much history as we have, but limit for very small screens if needed.
            # However, the Layout ratio=1 will provide the space, so we should fill it.
            # We don't know the exact line count here, so we'll show most of it.
            rows_to_show = rows
            if self.compact and len(rows) > 15:
                rows_to_show = rows[-15:]

            for row in reversed(rows_to_show):
                lines.append_text(self._row_text(row))
                lines.append("\n")

        lo = center_mhz - span_mhz / 2
        hi = center_mhz + span_mhz / 2
        axis = Text()

        # More descriptive axis for compact
        lo_s = f"{lo:.2f}"
        hi_s = f"{hi:.2f}"
        mid_s = f" {center_mhz:.3f} MHz "

        if self.compact:
            lo_s = f"{lo:.1f}"
            hi_s = f"{hi:.1f}"
            mid_s = f" {center_mhz:.2f}M "

        axis.append(lo_s, style="dim bright_cyan")
        pad = max(0, self.width - len(lo_s) - len(hi_s) - len(mid_s))
        axis.append("─" * (pad // 2), style="dim")
        axis.append(mid_s, style="bold bright_magenta")
        axis.append("─" * (pad - pad // 2), style="dim")
        axis.append(hi_s, style="dim bright_cyan")
        lines.append_text(axis)

        src_label = {
            "PLUTO": "PLU",
            "PLUTO-WAIT": "PLU-INIT",
            "HACKRF": "HRF",
            "HACKRF-WAIT": "HRF-INIT",
            "WAIT": "INIT",
            "SIM": "SIM",
        }.get(self._last_source, "SIM") if self.compact else {
            "PLUTO": "PlutoSDR+",
            "PLUTO-WAIT": "PlutoSDR+ (initializing)",
            "HACKRF": "HackRF",
            "HACKRF-WAIT": "HackRF (initializing)",
            "WAIT": "SDR initializing...",
            "SIM": "SIMULATOR",
        }.get(self._last_source, "SIMULATOR")

        mod_label = getattr(self, "modulation", "RAW") if self.compact else getattr(self, "modulation", "RAW-SWEEP")

        if self.compact:
            title = f"[bold {self.border_style}]▓ WF ▓[/] [dim]({self.mode}·{src_label}·{span_mhz:.1f}M·{self.dbm_floor:.0f}/{self.dbm_ceil:.0f})[/]"
        else:
            stream = self._active_stream()
            err = stream.last_error() if stream else None
            err_suffix = f" · err: {_esc(err)}" if (self._want_real and err) else ""
            gain_info = f" · floor {self.dbm_floor:.0f} ceil {self.dbm_ceil:.0f}"
            unit = "dBFS" if self._active_real == "pluto" else "dBm"
            gain_suffix = (
                f" · lna {self.lna_gain}dB vga {self.vga_gain}dB AMP-LOCK"
                if self._active_real == "hackrf"
                else f" · gain {self.lna_gain}dB"
                if self._active_real == "pluto"
                else ""
            )
            sweeps = stream.sweeps() if stream else 0
            sweep_suffix = f" · sweeps {sweeps}" if self._want_real else ""
            title = (
                f"[bold {self.border_style}]▓ WATERFALL + SPECTRUM ▓[/] "
                f"[dim]({self.mode} · {src_label} · {mod_label} · "
                f"{span_mhz:.1f}MHz BW · {unit}{gain_info}{gain_suffix}{sweep_suffix}{err_suffix})[/]"
            )
        return Panel(lines, title=title, border_style=self.border_style, padding=(0, 1))
