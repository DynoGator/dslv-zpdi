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
    a            toggle RF front-end amp (Pluto/HackRF amp lockout enforced)
    </>          tune center frequency down/up
    ,/.          fine tune center frequency
    z/x          zoom out/in
    [/]          floor down/up
    {/}          ceil down/up
    p            cycle palette
    s            toggle spectrum view
    c            toggle compact layout
    t            toggle 10" touchscreen layout
"""

import argparse
import os
import select
import shutil
import signal
import subprocess
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
from dashboard.mobile_bridge import MobileBridge
from dashboard.panels.anomaly import RFAnomalyPanel
from dashboard.panels.bci import BCIPanel
from dashboard.panels.demod import DemodPanel
from dashboard.panels.hardware import HardwarePanel
from dashboard.panels.logs import LogPanel
from dashboard.panels.mobile import MobilePanel
from dashboard.panels.notifications import NotificationPanel
from dashboard.panels.pipeline import PipelinePanel
from dashboard.panels.radon import RadonPanel
from dashboard.panels.settings import SettingsPanel
from dashboard.panels.storm import StormPanel
from dashboard.panels.system import SystemPanel
from dashboard.panels.waterfall import WaterfallPanel
from dashboard.panels.weather import SpaceWeatherPanel

try:
    from dashboard.sdr_state import SDRStateManager
except ImportError:
    try:
        from sdr_state import SDRStateManager
    except ImportError:
        from tools.dashboard.sdr_state import SDRStateManager


def footer_panel(compact: bool = False, state: dict | None = None) -> Panel:
    s = state or {}
    paused = s.get("paused", False)
    wf_mode = s.get("wf_mode", "SWEEP")
    real_sdr = s.get("real_sdr", False)
    sdr_source = s.get("sdr_source", "SIM")
    spectrum_on = s.get("spectrum_on", True)
    lna_gain = s.get("lna_gain", 24)
    center_hz = s.get("center_hz", 80_000_000)
    modulation = s.get("modulation", "RAW-SWEEP")
    palette_nm = s.get("palette_name", "HEAT")

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

    if real_sdr:
        _ind("SDR", sdr_source, "bold bright_green")
    else:
        _ind("SDR", "SIM", "bold bright_yellow")
    _ind("WF",   wf_mode, "bold bright_cyan")
    if s.get("input_mode") == "freq":
        _ind("FREQ-INPUT", f"{s.get('input_buffer', '')}_ MHz", "bold bright_yellow")
    else:
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
            ("q",    "Quit"),
            ("SPC",  "Pause"),
            ("m",    "WF-Mode"),
            ("r",    "Real-SDR"),
            ("p",    "Palette"),
            ("s",    "Spectrum"),
            ("g/v",  "Gain"),
            ("</>",  "Tune"),
            ("z/x",  "Zoom"),
            ("c/t",  "Layout"),
            ("h",    "Banner"),
        ]
    else:
        legend = [
            ("q",       "Quit Dashboard"),
            ("space",   "Pause Data"),
            ("m",       "Cycle Waterfall Mode"),
            ("d",       "Cycle Modulation"),
            ("r",       "Toggle Real SDR"),
            ("p",       "Cycle Palette"),
            ("s",       "Toggle Spectrum View"),
            ("[/]",     "Adj Floor ±"),
            ("{/}",     "Adj Ceil ±"),
            ("h",       "Toggle Banner"),
            ("c",       "Toggle Compact Layout"),
            ("t",       "Toggle 10\" Layout"),
            ("g/v",     "Cycle LNA/VGA Gain"),
            ("a",       "Toggle Amp"),
            ("+/-",     "Gain Step ±"),
            ("</>",     "Tune Coarse ±"),
            (",/.",     "Tune Fine ±"),
            ("z/x",     "Zoom In/Out"),
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
    if os.getenv("DSLV_DASHBOARD_COMPACT", "0").strip() in ("1", "true", "yes"):
        return True
    return False


def _is_ten_inch() -> bool:
    """10\" touchscreen layout (about 1280x800 terminal, e.g. 160x45 cols/rows)."""
    if os.getenv("DSLV_DASHBOARD_10IN", "1").strip() in ("1", "true", "yes"):
        return True
    return True


def _enabled(names, panels):
    return [n for n in names if getattr(panels, n, True)]


def build_layout(
    show_banner: bool,
    waterfall_only: bool = False,
    compact: bool = False,
    ten_inch: bool = False,
    panels=None,
) -> Layout:
    panels = panels or {}
    layout = Layout()

    if waterfall_only:
        layout.split_column(Layout(name="waterfall"))
        return layout

    settings = _enabled(("settings",), panels)

    if ten_inch:
        # 10" touchscreen: two-column layout. Left column carries dense status
        # panels and the settings reference; the right column is dominated by
        # the waterfall with logs/notifications underneath.
        left_names = _enabled(("system", "pipeline", "hardware", "settings"), panels)
        right_bottom = _enabled(("logs", "notifications"), panels)

        root_rows: list[Layout] = []
        if show_banner:
            root_rows.append(Layout(name="banner", size=5))
        root_rows.append(Layout(name="main", ratio=1))
        root_rows.append(Layout(name="footer", size=4))
        layout.split_column(*root_rows)

        layout["main"].split_row(
            Layout(name="left", size=45),
            Layout(name="right", ratio=1),
        )

        if left_names:
            left_rows: list[Layout] = []
            for n in left_names:
                left_rows.append(Layout(name=n, size=8 if n == "settings" else 7))
            layout["left"].split_column(*left_rows)

        right_rows: list[Layout] = [Layout(name="waterfall", ratio=1)]
        if right_bottom:
            right_rows.append(Layout(name="bottom", size=10))
        layout["right"].split_column(*right_rows)
        if right_bottom:
            layout["right"]["bottom"].split_row(
                *[Layout(name=n, ratio=1) for n in right_bottom]
            )
        return layout

    if compact:
        try:
            _, total_rows = shutil.get_terminal_size()
        except Exception:
            total_rows = 24

        short_screen = total_rows < 33
        critical_screen = total_rows < 26

        status_a = _enabled(("system", "pipeline", "hardware"), panels)
        status_b = _enabled(("anomaly", "weather", "storm", "radon", "mobile", "bci", "demod"), panels)
        bottom = _enabled(("logs", "notifications"), panels)

        footer_sz = 3 if critical_screen else 4
        banner_sz = 0 if (critical_screen or short_screen) else (
            (4 if total_rows >= 36 else 3) if show_banner else 0
        )

        rows: list[Layout] = []
        if banner_sz:
            rows.append(Layout(name="banner", size=banner_sz))

        if short_screen:
            if status_a:
                rows.append(Layout(name="status_row_a", size=5))
            if status_b:
                rows.append(Layout(name="status_row_b", size=5))
            rows.append(Layout(name="waterfall", ratio=1))
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

        if settings:
            rows.append(Layout(name="settings", size=4))

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
    space = _enabled(("weather", "storm", "radon", "mobile", "bci", "demod"), panels)
    bottom = _enabled(("logs", "notifications"), panels)

    rows: list[Layout] = []
    if show_banner:
        rows.append(Layout(name="banner", size=9))
    if top:
        rows.append(Layout(name="top", size=11))
    rows.append(Layout(name="waterfall"))
    if space:
        rows.append(Layout(name="space", size=12))
    if settings:
        rows.append(Layout(name="settings", size=7))
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
        ten_inch: bool | None = None,
        config: DashboardConfig | None = None,
    ):
        cfg = config if config is not None else load_config()
        self.console = Console()
        self.refresh = refresh if refresh is not None else cfg.refresh
        self.fps = max(1, min(30, int(cfg.fps)))
        self.compact = _is_compact() if compact is None else compact
        self.ten_inch = (_is_ten_inch() if ten_inch is None else ten_inch) and not self.compact
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
            self.mobile_bridge = MobileBridge(self.mobile_p)
            self.mobile_bridge.start()
        else:
            self.mobile_bridge = None
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
        if getattr(cfg.panels, "settings", True):
            self.settings_p = SettingsPanel(border_style=cfg.theme.accent)
            self._panels["settings"] = self.settings_p

        self.demod_p = DemodPanel()
        self._panels["demod"] = self.demod_p

        self.paused = False
        self.state_mgr = SDRStateManager(owner_name="app.py")
        self._publish_sdr_state()

        self._panels_cfg = cfg.panels
        self.layout = build_layout(
            self.show_banner,
            self.waterfall_only,
            self.compact,
            self.ten_inch,
            cfg.panels,
        )
        self._keyboard_mode = None
        self._orig_attrs = None

        self._wf_modes = ["SWEEP", "NARROW", "SCOPE"]
        self._wf_idx = 0
        self._live: Any = None
        self._input_mode: str | None = None
        self._input_buffer: str = ""

    def _publish_sdr_state(self):
        wf = self._panels.get("waterfall")
        demod_panel = self._panels.get("demod")
        state = {
            "center_hz": float(wf.center_hz) if wf else 80_000_000.0,
            "bandwidth_hz": float(wf.span_hz) if wf else 20_000_000.0,
            "gain_db": float(wf.lna_gain) if wf else 24.0,
            "paused": self.paused,
        }
        if demod_panel:
            state["demod_profile"] = getattr(demod_panel, "active_profile", "FM Radio")
            state["audio_active"] = getattr(demod_panel, "is_active", False)
            state["mimo_tx"] = getattr(demod_panel, "mimo_tx", False)
        if hasattr(self, "state_mgr"):
            self.state_mgr.write_state(state)

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
        if hasattr(self, "state_mgr"):
            self.state_mgr.sync_from_disk(self)

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
        for name in ("system", "pipeline", "hardware", "anomaly", "weather", "storm", "radon", "mobile", "bci", "logs", "notifications", "settings", "demod", "waterfall"):
            panel = self._panels.get(name)
            panel_l = self._get_layout(name)
            if panel and panel_l:
                try:
                    if name in ("settings", "demod"):
                        panel_l.update(panel.render(compact=self.compact, state=self._get_state()))
                    else:
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
        demod_panel = self._panels.get("demod")
        demod_profile = getattr(demod_panel, "active_profile", "None") if demod_panel else "None"
        demod_active = getattr(demod_panel, "is_active", False) if demod_panel else False
        mimo_tx = getattr(demod_panel, "mimo_tx", False) if demod_panel else False

        return {
            "input_mode":  self._input_mode,
            "input_buffer": self._input_buffer,
            "demod_profile": demod_profile,
            "demod_active": demod_active,
            "mimo_tx": mimo_tx,
            "paused":      self.paused,
            "wf_mode":     wf.mode if wf else "SWEEP",
            "real_sdr":    os.getenv("DSLV_DASHBOARD_REAL_SDR", "0") == "1",
            "sdr_source":  wf._last_source if wf else "SIM",
            "spectrum_on": wf.show_spectrum if wf else True,
            "lna_gain":    wf.lna_gain if wf else 24,
            "vga_gain":    wf.vga_gain if wf else 20,
            "center_hz":   wf.center_hz if wf else 80_000_000,
            "span_hz":     wf.span_hz if wf else 20_000_000,
            "modulation":  getattr(wf, "modulation", "RAW-SWEEP") if wf else "RAW-SWEEP",
            "palette_name": wf.palette_name if wf else "HEAT",
            "dbm_floor":   wf.dbm_floor if wf else -90.0,
            "dbm_ceil":    wf.dbm_ceil if wf else -20.0,
            "refresh":     self.refresh,
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
        if self._input_mode == "freq":
            if k == "\n" or k == "\r":
                if self._input_buffer:
                    try:
                        hz = float(self._input_buffer) * 1e6
                        if "waterfall" in self._panels:
                            self._panels["waterfall"].center_hz = int(hz)
                            self._panels["waterfall"]._restart_stream_if_running()
                            if "notifications" in self._panels:
                                self._panels["notifications"].push("INFO", f"freq set: {hz/1e6:.3f} MHz")
                    except ValueError:
                        pass
                self._input_mode = None
                self._input_buffer = ""
                self._publish_sdr_state()
            elif k in ("BACKSPACE", "\x7f", "\b"):
                self._input_buffer = self._input_buffer[:-1]
            elif k == "\x1b":
                self._input_mode = None
                self._input_buffer = ""
            elif k.isdigit() or k == ".":
                self._input_buffer += k
            return

        if k in ("q", "Q"):
            raise KeyboardInterrupt
        if k == " ":
            self.paused = not self.paused
            if "notifications" in self._panels:
                self._panels["notifications"].push("INFO", "paused" if self.paused else "resumed")
            self._publish_sdr_state()
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
                self.layout = build_layout(self.show_banner, self.waterfall_only, self.compact, self.ten_inch, panels)
                if self._live is not None:
                    self._live.update(self.layout)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"banner: {'shown' if self.show_banner else 'hidden'}")
        elif k == "f":
            self._input_mode = "freq"
            self._input_buffer = ""
        elif k in ("1", "2", "3", "4", "5"):
            if "demod" in self._panels:
                p = self._panels["demod"]
                profile_map = {"1": "ADS-B", "2": "FM Radio", "3": "AM Radio", "4": "EMS/Fire", "5": "Broadcast TV"}
                p.active_profile = profile_map[k]
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"Profile selected: {p.active_profile}")
                self._publish_sdr_state()
        elif k in ("\n", "\r"):
            if "demod" in self._panels:
                p = self._panels["demod"]
                p.is_active = not getattr(p, "is_active", False)
                if p.is_active:
                    import subprocess
                    import sys
                    import os
                    profile = getattr(p, "active_profile", "ADS-B")
                    mimo_tx = getattr(p, "mimo_tx", False)
                    
                    wf = self._panels.get("waterfall")
                    freq_arg = f"--freq {wf.center_hz}" if wf else ""
                    bw_arg = f"--bw {wf.span_hz}" if wf else ""
                    gain_arg = f"--gain {wf.lna_gain}" if wf else ""
                    
                    # Get path to demod_app.py relative to app.py
                    demod_script = os.path.join(os.path.dirname(__file__), "demod_app.py")
                    cmd_str = f"{sys.executable} {demod_script} --profile '{profile}' {freq_arg} {bw_arg} {gain_arg} {'--tx' if mimo_tx else ''}"
                    cmd = ["lxterminal", "--title", "DSLV-ZPDI :: Demodulation Interface", "-e", cmd_str]
                    try:
                        subprocess.Popen(cmd)
                        msg = "Demodulation Interface Launched"
                    except Exception as e:
                        msg = f"Failed to launch Demod: {e}"
                    if "notifications" in self._panels:
                        self._panels["notifications"].push("INFO", msg)
                else:
                    if "notifications" in self._panels:
                        self._panels["notifications"].push("INFO", "Demodulation: OFF")
                self._publish_sdr_state()
        elif k == "T":
            if "demod" in self._panels:
                p = self._panels["demod"]
                p.mimo_tx = not getattr(p, "mimo_tx", False)
                if "notifications" in self._panels:
                    if p.mimo_tx:
                        self._panels["notifications"].push("WARN", "MIMO TX Enabled (RESTRICTED)")
                    else:
                        self._panels["notifications"].push("INFO", "MIMO TX Disabled")
                self._publish_sdr_state()
        elif k in ("c", "C"):
            if not self.waterfall_only:
                self.compact = not self.compact
                # Ten-inch and compact are mutually exclusive.
                if self.compact:
                    self.ten_inch = False
                self.show_banner = self._banner_pref
                if "waterfall" in self._panels:
                    self._panels["waterfall"].compact = self.compact
                panels = getattr(self, "_panels_cfg", None)
                self.layout = build_layout(self.show_banner, self.waterfall_only, self.compact, self.ten_inch, panels)
                if self._live is not None:
                    self._live.update(self.layout)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"compact: {'ON' if self.compact else 'OFF'}")
        elif k in ("t", "T"):
            if not self.waterfall_only:
                self.ten_inch = not self.ten_inch
                if self.ten_inch:
                    self.compact = False
                if "waterfall" in self._panels:
                    self._panels["waterfall"].compact = self.compact
                panels = getattr(self, "_panels_cfg", None)
                self.layout = build_layout(self.show_banner, self.waterfall_only, self.compact, self.ten_inch, panels)
                if self._live is not None:
                    self._live.update(self.layout)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"10\" layout: {'ON' if self.ten_inch else 'OFF'}")
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
                    self._panels["notifications"].push(
                        "INFO", f"spectrum: {'ON' if self._panels['waterfall'].show_spectrum else 'OFF'}")
        elif k == "UP":
            if "waterfall" in self._panels:
                self._panels["waterfall"].zoom(0.5)
                if "notifications" in self._panels:
                    self._panels["notifications"].push(
                        "INFO", f"zoom in: {self._panels['waterfall'].span_hz / 1e6:.1f}MHz")
                self._publish_sdr_state()
        elif k == "DOWN":
            if "waterfall" in self._panels:
                self._panels["waterfall"].zoom(2.0)
                if "notifications" in self._panels:
                    self._panels["notifications"].push(
                        "INFO", f"zoom out: {self._panels['waterfall'].span_hz / 1e6:.1f}MHz")
                self._publish_sdr_state()
        elif k == "LEFT":
            if "waterfall" in self._panels:
                wf = self._panels["waterfall"]
                wf.tune(-int(wf.span_hz * 0.1))
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"tune -: {wf.center_hz / 1e6:.2f}MHz")
                self._publish_sdr_state()
        elif k == "RIGHT":
            if "waterfall" in self._panels:
                wf = self._panels["waterfall"]
                wf.tune(int(wf.span_hz * 0.1))
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"tune +: {wf.center_hz / 1e6:.2f}MHz")
                self._publish_sdr_state()
        elif k == "+":
            if "waterfall" in self._panels:
                self._panels["waterfall"].adjust_gain(1)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"lna gain: {self._panels['waterfall'].lna_gain}dB")
                self._publish_sdr_state()
        elif k == "-":
            if "waterfall" in self._panels:
                self._panels["waterfall"].adjust_gain(-1)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"lna gain: {self._panels['waterfall'].lna_gain}dB")
                self._publish_sdr_state()
        elif k == "<":
            if "waterfall" in self._panels:
                wf = self._panels["waterfall"]
                wf.tune(-int(wf.span_hz * 0.1))
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"tune: {wf.center_hz / 1e6:.2f}MHz")
                self._publish_sdr_state()
        elif k == ">":
            if "waterfall" in self._panels:
                wf = self._panels["waterfall"]
                wf.tune(int(wf.span_hz * 0.1))
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"tune: {wf.center_hz / 1e6:.2f}MHz")
                self._publish_sdr_state()
        elif k in ("z", "Z"):
            if "waterfall" in self._panels:
                wf = self._panels["waterfall"]
                wf.zoom(0.5)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"zoom in: {wf.span_hz / 1e6:.1f}MHz")
                self._publish_sdr_state()
        elif k in ("x", "X"):
            if "waterfall" in self._panels:
                wf = self._panels["waterfall"]
                wf.zoom(2.0)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"zoom out: {wf.span_hz / 1e6:.1f}MHz")
                self._publish_sdr_state()
        elif k in ("g", "G"):
            if "waterfall" in self._panels:
                self._panels["waterfall"].cycle_gain()
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"lna gain: {self._panels['waterfall'].lna_gain}dB")
                self._publish_sdr_state()
        elif k in ("v", "V"):
            if "waterfall" in self._panels:
                self._panels["waterfall"].cycle_vga_gain()
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"vga gain: {self._panels['waterfall'].vga_gain}dB")
        elif k in ("d", "D"):
            if "waterfall" in self._panels:
                self._panels["waterfall"].cycle_modulation()
                if "notifications" in self._panels:
                    self._panels["notifications"].push(
                        "INFO", f"mod: {getattr(self._panels['waterfall'], 'modulation', 'RAW-SWEEP')}")
        elif k in ("a", "A"):
            if "notifications" in self._panels:
                self._panels["notifications"].push(
                    "WARN", "AMP LOCKED OUT — PlutoSDRplus 1 amp blown, parts on order"
                )
        elif k == ",":
            if "waterfall" in self._panels:
                wf = self._panels["waterfall"]
                wf.tune(-int(wf.span_hz * 0.01))
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"tune fine-: {wf.center_hz / 1e6:.3f}MHz")
                self._publish_sdr_state()
        elif k == ".":
            if "waterfall" in self._panels:
                wf = self._panels["waterfall"]
                wf.tune(int(wf.span_hz * 0.01))
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"tune fine+: {wf.center_hz / 1e6:.3f}MHz")
                self._publish_sdr_state()

    def run(self):
        self._boot_animation()
        if "logs" in self._panels:
            self._panels["logs"].start()
        if "notifications" in self._panels:
            self._panels["notifications"].push("INFO", "dashboard online")
        self._enter_raw()
        try:
            self._live = Live(self.layout, console=self.console,
                              refresh_per_second=self.fps, screen=True)
            frame_period = 1.0 / self.fps
            next_frame = time.monotonic()
            with self._live:
                while True:
                    while (k := self._read_key()) is not None:
                        self._handle_key(k)
                    if not self.paused:
                        self._render()
                    next_frame += frame_period
                    now = time.monotonic()
                    if now - next_frame > frame_period:
                        # Overran by more than a frame; resync the deadline.
                        next_frame = now + frame_period
                    time.sleep(max(0.0, next_frame - now))
        except KeyboardInterrupt:
            pass
        finally:
            self._exit_raw()
            if getattr(self, "mobile_bridge", None):
                self.mobile_bridge.stop()
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
    parser.add_argument("--ten-inch", action="store_true", help='force 10" touchscreen two-column layout')
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
    ten_inch: bool | None = None
    if args.compact:
        compact = True
    elif args.wide:
        compact = False
    if args.ten_inch:
        ten_inch = True

    # Real SDR is ON by default; --no-real-sdr flag allows explicit opt-out.
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
        ten_inch=ten_inch,
        config=cfg,
    )
    if args.no_boot:
        dash._boot_animation = lambda: None  # type: ignore
    dash.run()


if __name__ == "__main__":
    main()
