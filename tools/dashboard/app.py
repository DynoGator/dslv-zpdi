"""
DSLV-ZPDI Operations Dashboard — main Live application.

Keyboard:
    q / Ctrl+C   quit
    [space]      pause / resume
    h            help banner toggle
    m            cycle waterfall mode
    r            toggle REAL SDR data (sets DSLV_DASHBOARD_REAL_SDR env)
    g            cycle LNA gain
    +/-          adjust LNA gain up/down
    a            toggle RF front-end amp
    </>          tune center frequency down/up
    z/x          zoom out/in
    [/]          floor down/up
    {/}          ceil down/up
    p            cycle palette
    s            toggle spectrum view
    c            toggle compact layout
"""

import argparse
import os
import select
import shutil
import signal
import sys
import termios
import time
import tty
from pathlib import Path
from typing import Any

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from dashboard.banner import (
    compact_banner,
    full_banner,
    startup_animation_frames,
    ultra_compact_banner,
)
from dashboard.config import DashboardConfig, load_config
from dashboard.panels.anomaly import RFAnomalyPanel
from dashboard.panels.bci import BCIPanel
from dashboard.panels.hardware import HardwarePanel
from dashboard.panels.logs import LogPanel
from dashboard.panels.mobile import MobilePanel
from dashboard.panels.notifications import NotificationPanel
from dashboard.panels.pipeline import PipelinePanel
from dashboard.panels.radon import RadonPanel
from dashboard.panels.storm import StormPanel
from dashboard.panels.system import SystemPanel
from dashboard.panels.waterfall import WaterfallPanel
from dashboard.panels.weather import SpaceWeatherPanel


def footer_panel(compact: bool = False, state: dict | None = None) -> Panel:
    s = state or {}
    paused      = s.get("paused", False)
    wf_mode     = s.get("wf_mode", "SWEEP")
    real_sdr    = s.get("real_sdr", False)
    spectrum_on = s.get("spectrum_on", True)
    lna_gain    = s.get("lna_gain", 24)
    center_hz   = s.get("center_hz", 100_000_000)
    modulation  = s.get("modulation", "RAW-SWEEP")
    palette_nm  = s.get("palette_name", "HEAT")

    pulse = "●" if int(time.time() * 2) % 2 == 0 else "○"
    ts = time.strftime("%H:%M:%S", time.gmtime())

    # ── Status bar ──────────────────────────────────────────────────────────
    status = Text(no_wrap=True, overflow="ellipsis")

    if paused:
        status.append("⏸ PAUSED  ", style="bold yellow")
    else:
        status.append(f"{pulse} LIVE  ", style="bold bright_cyan")

    def _ind(label: str, val: str, style: str = "bright_white"):
        status.append(f"[{label}:", style="dim")
        status.append(val, style=style)
        status.append("] ", style="dim")

    _ind("SDR",  "REAL" if real_sdr    else "SIM",
         "bold bright_green" if real_sdr else "bold bright_yellow")
    _ind("WF",   wf_mode, "bold bright_cyan")
    _ind("FREQ", f"{center_hz / 1e6:.1f}MHz", "bright_magenta")
    _ind("LNA",  f"{lna_gain}dB")
    _ind("SPEC", "ON" if spectrum_on else "OFF",
         "bright_green" if spectrum_on else "dim")
    if not compact:
        _ind("MOD",  modulation, "bright_white")
    _ind("PAL",  palette_nm, "bright_cyan")
    status.append(f"{ts} UTC", style="dim")

    # ── Key legend ───────────────────────────────────────────────────────────
    keys = Text(no_wrap=True, overflow="ellipsis")
    if compact:
        legend = [
            ("q",    "quit"),
            ("SPC",  "pause"),
            ("m",    "wf-mode"),
            ("r",    "sdr"),
            ("p",    "palette"),
            ("s",    "spec"),
            ("g/v",  "LNA/VGA"),
            ("</>",  "tune"),
            ("z/x",  "zoom"),
            ("c",    "wide"),
            ("h",    "banner"),
        ]
    else:
        legend = [
            ("q",    "quit"),
            ("space","pause"),
            ("m",    "wf-mode"),
            ("d",    "mod"),
            ("r",    "real-sdr"),
            ("p",    "palette"),
            ("s",    "spectrum"),
            ("[/]",  "floor±"),
            ("{/}",  "ceil±"),
            ("h",    "banner"),
            ("c",    "compact"),
            ("g/v",  "LNA/VGA-gain"),
            ("a",    "amp"),
            ("+/-",  "gain-step"),
            ("</>",  "tune-coarse"),
            (",/.",  "tune-fine"),
            ("z/x",  "zoom"),
        ]
    for k, desc in legend:
        keys.append("[", style="dim")
        keys.append(k, style="bold bright_yellow")
        keys.append("]", style="dim")
        keys.append(desc, style="bright_white")
        keys.append(" ", style="dim")

    if compact:
        content = Group(status, keys)
    else:
        brand = Text(
            "DSLV-ZPDI :: DynoGatorLabs :: Tier 1 Anchor :: "
            '"If it moves, it gets coherence-scored."',
            style="italic dim bright_white",
            no_wrap=True,
            overflow="ellipsis",
        )
        content = Group(status, keys, brand)

    return Panel(content, border_style="bright_black", padding=(0, 1))


def _is_compact() -> bool:
    """Compact mode for 7" DSI (800×480 ≈ 92×30 cols/rows) and smaller screens."""
    if os.getenv("DSLV_DASHBOARD_COMPACT", "").strip() in ("1", "true", "yes"):
        return True
    try:
        cols, lines = shutil.get_terminal_size()
        return cols < 120 or lines < 35
    except Exception:
        return False


def _enabled(names, panels):
    return [n for n in names if getattr(panels, n, True)]


def build_layout(show_banner: bool, waterfall_only: bool = False, compact: bool = False, panels=None) -> Layout:
    panels = panels or {}
    layout = Layout()

    if waterfall_only:
        layout.split_column(Layout(name="waterfall"))
        return layout

    if compact:
        try:
            _, total_rows = shutil.get_terminal_size()
        except Exception:
            total_rows = 24

        # short_screen covers 7" DSI (~30 rows) and below; critical is very tight
        short_screen = total_rows < 33
        critical_screen = total_rows < 26

        status_a = _enabled(("system", "pipeline", "hardware"), panels)
        status_b = _enabled(("anomaly", "weather", "storm", "radon", "mobile", "bci"), panels)
        bottom = _enabled(("logs", "notifications"), panels)

        # 2-line footer (status bar + key legend); critical screens drop to 1 line
        footer_sz = 3 if critical_screen else 4
        # Suppress banner on 7" and smaller screens to free rows for waterfall
        banner_sz = 0 if (critical_screen or short_screen) else (
            (4 if total_rows >= 36 else 3) if show_banner else 0
        )

        rows: list[Layout] = []
        if banner_sz:
            rows.append(Layout(name="banner", size=banner_sz))

        if short_screen:
            # Combine status panels into two info-dense rows
            if status_a:
                rows.append(Layout(name="status_row_a", size=5))
            if status_b:
                rows.append(Layout(name="status_row_b", size=5))

            rows.append(Layout(name="waterfall", ratio=1))

            # Hide bottom panels if screen is too short for both waterfall + logs
            if bottom and total_rows >= 22:
                rows.append(Layout(name="bottom", size=5))
        else:
            if status_a:
                rows.append(Layout(name="status_a", size=5))
            if status_b:
                rows.append(Layout(name="status_b", size=5))
            rows.append(Layout(name="waterfall", ratio=1))
            if bottom:
                rows.append(Layout(name="bottom", size=5))

        rows.append(Layout(name="footer", size=footer_sz))
        layout.split_column(*rows)

        if short_screen:
            if status_a:
                layout["status_row_a"].split_row(*[Layout(name=n, ratio=1) for n in status_a])
            if status_b:
                layout["status_row_b"].split_row(*[Layout(name=n, ratio=1) for n in status_b])
        else:
            if status_a:
                layout["status_a"].split_row(*[Layout(name=n, ratio=1) for n in status_a])
            if status_b:
                layout["status_b"].split_row(*[Layout(name=n, ratio=1) for n in status_b])

        def _get_l(layout_obj, n):
            try:
                return layout_obj[n]
            except KeyError:
                return None

        if bottom and _get_l(layout, "bottom") is not None:
            layout["bottom"].split_row(*[Layout(name=n, ratio=1) for n in bottom])

        return layout

    # Wide layout
    top = _enabled(("system", "pipeline", "hardware", "anomaly"), panels)
    space = _enabled(("weather", "storm", "radon", "mobile", "bci"), panels)
    bottom = _enabled(("logs", "notifications"), panels)

    rows: list[Layout] = []
    if show_banner:
        rows.append(Layout(name="banner", size=9))
    if top:
        rows.append(Layout(name="top", size=11))
    rows.append(Layout(name="waterfall"))
    if space:
        rows.append(Layout(name="space", size=12))
    if bottom:
        rows.append(Layout(name="bottom", size=12))
    rows.append(Layout(name="footer", size=5))
    layout.split_column(*rows)

    if top:
        layout["top"].split_row(*[Layout(name=n, ratio=1) for n in top])
    if space:
        layout["space"].split_row(*[Layout(name=n, ratio=1) for n in space])
    if bottom:
        layout["bottom"].split_row(*[Layout(name=n, ratio=1) for n in bottom])
    return layout


class Dashboard:
    def __init__(
        self,
        refresh: float | None = None,
        show_banner: bool | None = None,
        waterfall_only: bool = False,
        compact: bool | None = None,
        config: DashboardConfig | None = None,
    ):
        cfg = config if config is not None else load_config()
        self.console = Console()
        self.refresh = refresh if refresh is not None else cfg.refresh
        self.compact = _is_compact() if compact is None else compact
        self._banner_pref = show_banner if show_banner is not None else cfg.show_banner
        self.show_banner = self._banner_pref
        self.waterfall_only = waterfall_only

        self._panels: dict[str, Any] = {}
        if getattr(cfg.panels, "system", True):
            self.sys_p = SystemPanel(border_style=cfg.theme.system_border)
            self._panels["system"] = self.sys_p
        if getattr(cfg.panels, "pipeline", True):
            self.pipe_p = PipelinePanel(
                unit=cfg.service_unit, border_style=cfg.theme.pipeline_border
            )
            self._panels["pipeline"] = self.pipe_p
        if getattr(cfg.panels, "hardware", True):
            self.hw_p = HardwarePanel(border_style=cfg.theme.hardware_border)
            self._panels["hardware"] = self.hw_p
        wf_cfg = cfg.waterfall
        try:
            wf_width = max(40 if self.compact else 60, shutil.get_terminal_size().columns - 6)
        except Exception:
            wf_width = 80
        if getattr(cfg.panels, "waterfall", True):
            self.wf_p = WaterfallPanel(
                width=wf_width,
                history=wf_cfg.history,
                mode=wf_cfg.mode,
                center_hz=wf_cfg.center_hz,
                span_hz=wf_cfg.span_hz,
                border_style=cfg.theme.waterfall_border,
                compact=self.compact,
            )
            self._panels["waterfall"] = self.wf_p
            # Anomaly depends on waterfall metrics and optionally pipeline for coherence
            pipe_ref = getattr(self, "pipe_p", None)
            self.anom_p = RFAnomalyPanel(self.wf_p, pipe_ref)
            self._panels["anomaly"] = self.anom_p
        if getattr(cfg.panels, "weather", True):
            self.weather_p = SpaceWeatherPanel()
            self._panels["weather"] = self.weather_p
        if getattr(cfg.panels, "storm", True):
            self.storm_p = StormPanel()
            self._panels["storm"] = self.storm_p
        if getattr(cfg.panels, "radon", True):
            self.radon_p = RadonPanel(border_style="bright_green")
            self._panels["radon"] = self.radon_p
        if getattr(cfg.panels, "mobile", True):
            self.mobile_p = MobilePanel(border_style="bright_blue")
            self._panels["mobile"] = self.mobile_p
        if getattr(cfg.panels, "bci", True):
            self.bci_p = BCIPanel(border_style="bright_magenta")
            self._panels["bci"] = self.bci_p
        if getattr(cfg.panels, "logs", True):
            max_l = 3 if self.compact else cfg.logs.max_lines
            self.log_p = LogPanel(
                unit=cfg.service_unit,
                max_lines=max_l,
                border_style=cfg.theme.logs_border,
            )
            self._panels["logs"] = self.log_p
        if getattr(cfg.panels, "notifications", True):
            max_n = 3 if self.compact else cfg.notifications.max_items
            self.note_p = NotificationPanel(
                max_items=max_n,
                humor_every_s=cfg.notifications.humor_every_s,
                glitch_every_s=cfg.notifications.glitch_every_s,
                border_style=cfg.theme.notifications_border,
            )
            self._panels["notifications"] = self.note_p

        self.paused = False
        self._panels_cfg = cfg.panels
        self.layout = build_layout(self.show_banner, self.waterfall_only, self.compact, cfg.panels)
        self._keyboard_mode = None
        self._orig_attrs = None

        self._wf_modes = ["SWEEP", "NARROW", "SCOPE"]
        self._wf_idx = 0
        self._live: Any = None

    # keyboard raw mode ---
    def _enter_raw(self):
        if not sys.stdin.isatty():
            return
        fd = sys.stdin.fileno()
        self._orig_attrs = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        self._keyboard_mode = fd

    def _exit_raw(self):
        if self._orig_attrs is not None and self._keyboard_mode is not None:
            termios.tcsetattr(self._keyboard_mode, termios.TCSADRAIN, self._orig_attrs)

    def _read_key(self) -> str | None:
        if not sys.stdin.isatty():
            return None
        r, _, _ = select.select([sys.stdin], [], [], 0.0)
        if not r:
            return None
        try:
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                # Non-blocking attempt to consume the rest of an escape sequence.
                seq = ""
                while True:
                    r2, _, _ = select.select([sys.stdin], [], [], 0.0)
                    if not r2:
                        break
                    seq += sys.stdin.read(1)
                if seq == "[A":
                    return "UP"
                elif seq == "[B":
                    return "DOWN"
                elif seq == "[C":
                    return "RIGHT"
                elif seq == "[D":
                    return "LEFT"
                return f"\x1b{seq}"
            return ch
        except Exception:
            return None

    # render ---
    def _get_layout(self, name: str) -> Layout | None:
        try:
            return self.layout[name]
        except KeyError:
            return None

    def _render(self):
        if self.waterfall_only:
            if "waterfall" in self._panels:
                wf_l = self._get_layout("waterfall")
                if wf_l:
                    wf_l.update(self._panels["waterfall"].render())
            return

        banner_l = self._get_layout("banner")
        if self.show_banner and banner_l:
            try:
                _, total_rows = shutil.get_terminal_size((80, 24))
            except Exception:
                total_rows = 24

            if total_rows < 28:
                banner_l.update(ultra_compact_banner())
            else:
                banner_l.update(
                    compact_banner() if self.compact else full_banner()
                )

        # Priority: render critical metrics first
        for name in ("system", "pipeline", "hardware", "anomaly", "weather", "storm", "radon", "mobile", "bci", "logs", "notifications", "waterfall"):
            panel = self._panels.get(name)
            panel_l = self._get_layout(name)
            if panel and panel_l:
                try:
                    panel_l.update(panel.render(compact=self.compact))
                except Exception as e:
                    # Don't crash the whole dashboard if one panel fails to render
                    if "notifications" in self._panels:
                        self.note_p.push("ERROR", f"render {name}: {e}")
                    else:
                        print(f"[!] Error rendering {name}: {e}")

        footer_l = self._get_layout("footer")
        if footer_l:
            footer_l.update(footer_panel(self.compact, self._get_state()))

    def _get_state(self) -> dict:
        wf = self._panels.get("waterfall")
        return {
            "paused":      self.paused,
            "wf_mode":     wf.mode if wf else "SWEEP",
            "real_sdr":    os.getenv("DSLV_DASHBOARD_REAL_SDR", "0") == "1",
            "spectrum_on": wf.show_spectrum if wf else True,
            "lna_gain":    wf.lna_gain if wf else 24,
            "vga_gain":    wf.vga_gain if wf else 20,
            "center_hz":   wf.center_hz if wf else 100_000_000,
            "modulation":  getattr(wf, "modulation", "RAW-SWEEP") if wf else "RAW-SWEEP",
            "palette_name": wf.palette_name if wf else "HEAT",
            "compact":     self.compact,
            "banner":      self.show_banner,
        }

    def _boot_animation(self):
        if self.waterfall_only:
            return
        for frame in startup_animation_frames(self.console):
            self.console.print(frame)
            time.sleep(0.15)
        time.sleep(0.5)

    def _handle_key(self, k: str):
        if k in ("q", "Q"):
            raise KeyboardInterrupt
        if k == " ":
            self.paused = not self.paused
            if "notifications" in self._panels:
                self._panels["notifications"].push("INFO", "paused" if self.paused else "resumed")
        elif k in ("m", "M"):
            if "waterfall" in self._panels:
                self._wf_idx = (self._wf_idx + 1) % len(self._wf_modes)
                self._panels["waterfall"].set_mode(self._wf_modes[self._wf_idx])
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"waterfall mode: {self._wf_modes[self._wf_idx]}")
        elif k in ("r", "R"):
            cur = os.getenv("DSLV_DASHBOARD_REAL_SDR", "0")
            new = "0" if cur == "1" else "1"
            os.environ["DSLV_DASHBOARD_REAL_SDR"] = new
            if "notifications" in self._panels:
                self._panels["notifications"].push("INFO", f"real SDR mode: {'ON' if new == '1' else 'OFF'}")
        elif k in ("h", "H"):
            if not self.waterfall_only:
                self._banner_pref = not self._banner_pref
                self.show_banner = self._banner_pref
                panels = getattr(self, "_panels_cfg", None)
                self.layout = build_layout(self.show_banner, self.waterfall_only, self.compact, panels)
                if self._live is not None:
                    self._live.update(self.layout)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"banner: {'shown' if self.show_banner else 'hidden'}")
        elif k in ("c", "C"):
            if not self.waterfall_only:
                self.compact = not self.compact
                self.show_banner = self._banner_pref
                if "waterfall" in self._panels:
                    self._panels["waterfall"].compact = self.compact
                panels = getattr(self, "_panels_cfg", None)
                self.layout = build_layout(self.show_banner, self.waterfall_only, self.compact, panels)
                if self._live is not None:
                    self._live.update(self.layout)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"compact: {'ON' if self.compact else 'OFF'}")
        elif k == "[":
            if "waterfall" in self._panels:
                self._panels["waterfall"].adjust_floor(-5.0)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"floor: {self._panels['waterfall'].dbm_floor} dBm")
        elif k == "]":
            if "waterfall" in self._panels:
                self._panels["waterfall"].adjust_floor(5.0)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"floor: {self._panels['waterfall'].dbm_floor} dBm")
        elif k == "{":
            if "waterfall" in self._panels:
                self._panels["waterfall"].adjust_ceil(-5.0)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"ceil: {self._panels['waterfall'].dbm_ceil} dBm")
        elif k == "}":
            if "waterfall" in self._panels:
                self._panels["waterfall"].adjust_ceil(5.0)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"ceil: {self._panels['waterfall'].dbm_ceil} dBm")
        elif k in ("p", "P"):
            if "waterfall" in self._panels:
                self._panels["waterfall"].cycle_palette()
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", "palette cycled")
        elif k in ("s", "S"):
            if "waterfall" in self._panels:
                self._panels["waterfall"].show_spectrum = not self._panels["waterfall"].show_spectrum
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"spectrum: {'ON' if self._panels['waterfall'].show_spectrum else 'OFF'}")
        elif k == "UP":
            if "waterfall" in self._panels:
                self._panels["waterfall"].zoom(0.5)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"zoom in: {self._panels['waterfall'].span_hz / 1e6:.1f}MHz")
        elif k == "DOWN":
            if "waterfall" in self._panels:
                self._panels["waterfall"].zoom(2.0)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"zoom out: {self._panels['waterfall'].span_hz / 1e6:.1f}MHz")
        elif k == "LEFT":
            if "waterfall" in self._panels:
                wf = self._panels["waterfall"]
                wf.tune(-int(wf.span_hz * 0.1))
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"tune -: {wf.center_hz / 1e6:.2f}MHz")
        elif k == "RIGHT":
            if "waterfall" in self._panels:
                wf = self._panels["waterfall"]
                wf.tune(int(wf.span_hz * 0.1))
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"tune +: {wf.center_hz / 1e6:.2f}MHz")
        elif k == "+":
            if "waterfall" in self._panels:
                self._panels["waterfall"].adjust_gain(1)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"lna gain: {self._panels['waterfall'].lna_gain}dB")
        elif k == "-":
            if "waterfall" in self._panels:
                self._panels["waterfall"].adjust_gain(-1)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"lna gain: {self._panels['waterfall'].lna_gain}dB")
        elif k == "<":
            if "waterfall" in self._panels:
                wf = self._panels["waterfall"]
                wf.tune(-int(wf.span_hz * 0.1))
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"tune: {wf.center_hz / 1e6:.2f}MHz")
        elif k == ">":
            if "waterfall" in self._panels:
                wf = self._panels["waterfall"]
                wf.tune(int(wf.span_hz * 0.1))
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"tune: {wf.center_hz / 1e6:.2f}MHz")
        elif k in ("z", "Z"):
            if "waterfall" in self._panels:
                wf = self._panels["waterfall"]
                wf.zoom(0.5)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"zoom in: {wf.span_hz / 1e6:.1f}MHz")
        elif k in ("x", "X"):
            if "waterfall" in self._panels:
                wf = self._panels["waterfall"]
                wf.zoom(2.0)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"zoom out: {wf.span_hz / 1e6:.1f}MHz")
        elif k in ("g", "G"):
            if "waterfall" in self._panels:
                self._panels["waterfall"].cycle_gain()
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"lna gain: {self._panels['waterfall'].lna_gain}dB")
        elif k in ("v", "V"):
            if "waterfall" in self._panels:
                self._panels["waterfall"].cycle_vga_gain()
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"vga gain: {self._panels['waterfall'].vga_gain}dB")
        elif k in ("d", "D"):
            if "waterfall" in self._panels:
                self._panels["waterfall"].cycle_modulation()
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"mod: {getattr(self._panels['waterfall'], 'modulation', 'RAW-SWEEP')}")
        elif k in ("a", "A"):
            if "notifications" in self._panels:
                self._panels["notifications"].push(
                    "WARN", "AMP LOCKED OUT — HackRF 1 amp blown, parts on order"
                )
        elif k == ",":
            if "waterfall" in self._panels:
                wf = self._panels["waterfall"]
                wf.tune(-int(wf.span_hz * 0.01))
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"tune fine-: {wf.center_hz / 1e6:.3f}MHz")
        elif k == ".":
            if "waterfall" in self._panels:
                wf = self._panels["waterfall"]
                wf.tune(int(wf.span_hz * 0.01))
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"tune fine+: {wf.center_hz / 1e6:.3f}MHz")

    def run(self):
        self._boot_animation()
        if "logs" in self._panels:
            self._panels["logs"].start()
        if "notifications" in self._panels:
            self._panels["notifications"].push("INFO", "dashboard online")
        self._enter_raw()
        try:
            self._live = Live(self.layout, console=self.console, refresh_per_second=max(1, int(1 / self.refresh)), screen=True)
            with self._live:
                while True:
                    k = self._read_key()
                    if k:
                        self._handle_key(k)
                    if not self.paused:
                        self._render()
                    time.sleep(self.refresh)
        except KeyboardInterrupt:
            pass
        finally:
            self._exit_raw()
            if "logs" in self._panels:
                self._panels["logs"].stop()
            if "waterfall" in self._panels:
                self._panels["waterfall"].shutdown()
            self.console.print("\n[bold bright_cyan]Dashboard offline. Pipeline continues in background.[/]\n")


def _signal_handler(sig, frame):
    raise KeyboardInterrupt


def main(cfg=None):
    if cfg is None:
        cfg = load_config()

    parser = argparse.ArgumentParser(description="DSLV-ZPDI Operations Dashboard")
    parser.add_argument("--refresh", type=float, default=cfg.refresh, help="refresh interval (s)")
    parser.add_argument("--no-banner", action="store_true", help="hide startup banner")
    parser.add_argument("--no-boot", action="store_true", help="skip boot animation")
    parser.add_argument("--waterfall-only", action="store_true", help="render only the waterfall panel")
    parser.add_argument("--compact", action="store_true", help='force compact layout (5" DSI)')
    parser.add_argument("--wide", action="store_true", help="force wide layout (disable compact auto-detect)")
    parser.add_argument("--no-real-sdr", action="store_true", help="start with real-SDR mode OFF (default is ON)")
    parser.add_argument("--headless", action="store_true", help="run without TUI (journald only)")
    parser.add_argument("--config", type=str, default="", help="use a custom dashboard.toml")
    parser.add_argument("--print-config", action="store_true", help="dump resolved config and exit")
    args = parser.parse_args()

    if args.config:
        cfg = load_config(Path(args.config))
    if args.print_config:
        from pprint import pformat
        print(pformat(cfg))
        return

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    compact: bool | None = None
    if args.compact:
        compact = True
    elif args.wide:
        compact = False

    # HackRF is ON by default; --no-real-sdr flag allows explicit opt-out.
    os.environ["DSLV_DASHBOARD_REAL_SDR"] = "0" if args.no_real_sdr else "1"

    show_banner = False if args.no_banner else cfg.show_banner

    if args.headless:
        print("[+] Headless mode active. Dashboard logic running in background. Check journalctl -u dslv-zpdi")
        # Minimal loop to keep process alive and handle signals
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("[+] Headless dashboard shutting down.")
            return

    dash = Dashboard(
        refresh=args.refresh,
        show_banner=show_banner,
        waterfall_only=args.waterfall_only,
        compact=compact,
        config=cfg,
    )
    if args.no_boot:
        dash._boot_animation = lambda: None  # type: ignore
    dash.run()


if __name__ == "__main__":
    main()
