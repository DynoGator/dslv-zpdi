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

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from dashboard.banner import compact_banner, full_banner, startup_animation_frames
from dashboard.config import DashboardConfig, load_config
from dashboard.panels.anomaly import RFAnomalyPanel
from dashboard.panels.hardware import HardwarePanel
from dashboard.panels.logs import LogPanel
from dashboard.panels.notifications import NotificationPanel
from dashboard.panels.pipeline import PipelinePanel
from dashboard.panels.storm import StormPanel
from dashboard.panels.system import SystemPanel
from dashboard.panels.waterfall import WaterfallPanel
from dashboard.panels.weather import SpaceWeatherPanel


def footer_panel(compact: bool = False) -> Panel:
    t = Text()
    if compact:
        keys = [
            ("q", "quit"),
            ("␣", "pause"),
            ("m", "wf"),
            ("r", "real"),
            ("p", "pal"),
            ("s", "spec"),
            ("c", "wide"),
            ("g", "gain"),
            ("a", "amp"),
            ("z/x", "zoom"),
        ]
    else:
        keys = [
            ("q", "quit"),
            ("space", "pause"),
            ("m", "wf-mode"),
            ("r", "real-sdr"),
            ("p", "palette"),
            ("s", "spec"),
            ("[/]", "floor"),
            ("{/}", "ceil"),
            ("h", "banner"),
            ("c", "compact"),
            ("g", "gain"),
            ("a", "amp"),
            ("+/-", "gain"),
            ("</>", "tune"),
            ("z/x", "zoom"),
        ]
    for k, desc in keys:
        t.append(" [ ", style="dim")
        t.append(k, style="bold bright_yellow on black")
        t.append(" ] ", style="dim")
        t.append(desc, style="bright_white")
        t.append("  ", style="dim")
    if not compact:
        t.append("\n")
        t.append(
            "DSLV-ZPDI :: DynoGatorLabs :: Tier 1 Anchor :: "
            "If it moves, it gets coherence-scored.",
            style="italic dim bright_white",
        )
    # Live pulse + timestamp strip
    pulse = "● LIVE" if int(time.time() * 2) % 2 == 0 else "○ LIVE"
    ts = time.strftime("%H:%M:%S UTC", time.gmtime())
    t.append("\n")
    t.append(f"{pulse}  {ts}", style="bold bright_cyan")
    return Panel(t, border_style="bright_black", padding=(0, 1))


def _is_compact() -> bool:
    """Compact mode when terminal is narrower than 140 cols (e.g. 5\" DSI at
    800x480, or a DSLV_DASHBOARD_COMPACT=1 override)."""
    if os.getenv("DSLV_DASHBOARD_COMPACT", "").strip() in ("1", "true", "yes"):
        return True
    try:
        return shutil.get_terminal_size().columns < 140
    except Exception:
        return False


def _enabled(names, panels):
    return [n for n in names if getattr(panels, n, True)]


def build_layout(show_banner: bool, waterfall_only: bool = False, compact: bool = False, panels=None) -> Layout:
    panels = panels or {}
    layout = Layout()

    if waterfall_only:
        layout.split_column(Layout(name="middle"))
        return layout

    if compact:
        try:
            total_rows = shutil.get_terminal_size().lines
        except Exception:
            total_rows = 24
        roomy = total_rows >= 30
        want_space = total_rows >= 32

        status_a = _enabled(("system", "pipeline"), panels)
        status_b = _enabled(("hardware", "anomaly"), panels)
        space = _enabled(("weather", "storm"), panels)
        bottom = _enabled(("logs", "notifications"), panels)

        status_sz = 8 if roomy else 7
        bottom_sz = 6 if roomy else 5
        footer_sz = 3
        banner_sz = (4 if roomy else 3) if show_banner else 0

        rows: list[Layout] = []
        if banner_sz:
            rows.append(Layout(name="banner", size=banner_sz))
        if status_a:
            rows.append(Layout(name="status_a", size=status_sz))
        if status_b:
            rows.append(Layout(name="status_b", size=status_sz))
        rows.append(Layout(name="middle"))
        if want_space and space:
            rows.append(Layout(name="space", size=8))
        if bottom:
            rows.append(Layout(name="bottom", size=bottom_sz))
        rows.append(Layout(name="footer", size=footer_sz))
        layout.split_column(*rows)

        if status_a:
            layout["status_a"].split_row(*[Layout(name=n, ratio=1) for n in status_a])
        if status_b:
            layout["status_b"].split_row(*[Layout(name=n, ratio=1) for n in status_b])
        if want_space and space:
            layout["space"].split_row(*[Layout(name=n, ratio=1) for n in space])
        if bottom:
            layout["bottom"].split_row(*[Layout(name=n, ratio=1) for n in bottom])
        return layout

    # Wide layout
    top = _enabled(("system", "pipeline", "hardware", "anomaly"), panels)
    space = _enabled(("weather", "storm"), panels)
    bottom = _enabled(("logs", "notifications"), panels)

    rows: list[Layout] = []
    if show_banner:
        rows.append(Layout(name="banner", size=9))
    if top:
        rows.append(Layout(name="top", size=11))
    rows.append(Layout(name="middle"))
    if space:
        rows.append(Layout(name="space", size=12))
    if bottom:
        rows.append(Layout(name="bottom", size=12))
    rows.append(Layout(name="footer", size=4))
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
        wf_width = max(40 if self.compact else 60, shutil.get_terminal_size().columns - 6)
        if getattr(cfg.panels, "waterfall", True):
            self.wf_p = WaterfallPanel(
                width=wf_width,
                history=wf_cfg.history,
                mode=wf_cfg.mode,
                center_hz=wf_cfg.center_hz,
                span_hz=wf_cfg.span_hz,
                border_style=cfg.theme.waterfall_border,
            )
            self._panels["waterfall"] = self.wf_p
            # Anomaly depends on waterfall metrics
            self.anom_p = RFAnomalyPanel(self.wf_p)
            self._panels["anomaly"] = self.anom_p
        if getattr(cfg.panels, "weather", True):
            self.weather_p = SpaceWeatherPanel()
            self._panels["weather"] = self.weather_p
        if getattr(cfg.panels, "storm", True):
            self.storm_p = StormPanel()
            self._panels["storm"] = self.storm_p
        if getattr(cfg.panels, "logs", True):
            self.log_p = LogPanel(
                unit=cfg.service_unit,
                max_lines=cfg.logs.max_lines,
                border_style=cfg.theme.logs_border,
            )
            self._panels["logs"] = self.log_p
        if getattr(cfg.panels, "notifications", True):
            self.note_p = NotificationPanel(
                max_items=cfg.notifications.max_items,
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
    def _render(self):
        if self.waterfall_only:
            if "waterfall" in self._panels:
                self.layout["middle"].update(self._panels["waterfall"].render())
            return

        if self.show_banner:
            self.layout["banner"].update(
                compact_banner() if self.compact else full_banner()
            )
        for name, panel in self._panels.items():
            if self.layout.get(name) is not None:
                self.layout[name].update(panel.render())
        self.layout["footer"].update(footer_panel(self.compact))

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
            self.note_p.push("INFO", "paused" if self.paused else "resumed")
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
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"banner: {'shown' if self.show_banner else 'hidden'}")
        elif k in ("c", "C"):
            if not self.waterfall_only:
                self.compact = not self.compact
                self.show_banner = self._banner_pref
                panels = getattr(self, "_panels_cfg", None)
                self.layout = build_layout(self.show_banner, self.waterfall_only, self.compact, panels)
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
        elif k in ("+", "UP"):
            if "waterfall" in self._panels:
                self._panels["waterfall"].adjust_gain(1)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"lna gain: {self._panels['waterfall'].lna_gain}dB")
        elif k in ("-", "DOWN"):
            if "waterfall" in self._panels:
                self._panels["waterfall"].adjust_gain(-1)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"lna gain: {self._panels['waterfall'].lna_gain}dB")
        elif k in ("g", "G"):
            if "waterfall" in self._panels:
                self._panels["waterfall"].cycle_gain()
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"lna gain: {self._panels['waterfall'].lna_gain}dB")
        elif k in ("a", "A"):
            if "waterfall" in self._panels:
                self._panels["waterfall"].toggle_amp()
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"amp: {'ON' if self._panels['waterfall'].amp_enabled else 'OFF'}")
        elif k == "<":
            if "waterfall" in self._panels:
                self._panels["waterfall"].tune(-int(self._panels["waterfall"].span_hz * 0.1))
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"tune: {self._panels['waterfall'].center_hz / 1e6:.1f}MHz")
        elif k == ">":
            if "waterfall" in self._panels:
                self._panels["waterfall"].tune(int(self._panels["waterfall"].span_hz * 0.1))
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"tune: {self._panels['waterfall'].center_hz / 1e6:.1f}MHz")
        elif k in ("z", "Z"):
            if "waterfall" in self._panels:
                self._panels["waterfall"].zoom(2.0)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"zoom: {self._panels['waterfall'].span_hz / 1e6:.1f}MHz")
        elif k in ("x", "X"):
            if "waterfall" in self._panels:
                self._panels["waterfall"].zoom(0.5)
                if "notifications" in self._panels:
                    self._panels["notifications"].push("INFO", f"zoom: {self._panels['waterfall'].span_hz / 1e6:.1f}MHz")

    def run(self):
        self._boot_animation()
        if "logs" in self._panels:
            self._panels["logs"].start()
        if "notifications" in self._panels:
            self._panels["notifications"].push("INFO", "dashboard online")
        self._enter_raw()
        try:
            with Live(self.layout, console=self.console, refresh_per_second=max(1, int(1 / self.refresh)), screen=True) as live:
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
    parser.add_argument("--compact", action="store_true", help="force compact layout (5\" DSI)")
    parser.add_argument("--wide", action="store_true", help="force wide layout (disable compact auto-detect)")
    parser.add_argument("--real-sdr", action="store_true", help="start with real-SDR mode already on")
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

    if args.real_sdr:
        os.environ["DSLV_DASHBOARD_REAL_SDR"] = "1"

    show_banner = False if args.no_banner else cfg.show_banner
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
