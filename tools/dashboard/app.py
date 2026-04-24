"""
DSLV-ZPDI Operations Dashboard — main Live application.

Keyboard:
    q / Ctrl+C   quit
    [space]      pause / resume
    h            help banner toggle
    m            cycle waterfall mode
    r            toggle REAL SDR data (sets DSLV_DASHBOARD_REAL_SDR env)
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

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from dashboard.banner import compact_banner, full_banner, startup_animation_frames
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


def build_layout(show_banner: bool, waterfall_only: bool = False, compact: bool = False) -> Layout:
    layout = Layout()

    if waterfall_only:
        layout.split_column(
            Layout(name="middle"),
        )
        return layout

    if compact:
        # 5" DSI (800x480) layout — stacked for vertical real estate. Row
        # sizes scale with total_rows so the waterfall always gets useful
        # height. At >= 32 rows we add the space-weather strip back in.
        try:
            total_rows = shutil.get_terminal_size().lines
        except Exception:
            total_rows = 24
        roomy = total_rows >= 30
        want_space = total_rows >= 32
        # Fixed rows ...
        status_sz = 8 if roomy else 7
        bottom_sz = 6 if roomy else 5
        footer_sz = 3          # 3 is the minimum that shows the keys + borders
        banner_sz = (4 if roomy else 3) if show_banner else 0
        rows = [
            Layout(name="banner", size=banner_sz),
            Layout(name="status_a", size=status_sz),
            Layout(name="status_b", size=status_sz),
            Layout(name="middle"),
            Layout(name="bottom", size=bottom_sz),
            Layout(name="footer", size=footer_sz),
        ]
        if want_space:
            rows.insert(4, Layout(name="space", size=8))
        layout.split_column(*rows)
        layout["status_a"].split_row(
            Layout(name="system", ratio=1),
            Layout(name="pipeline", ratio=1),
        )
        layout["status_b"].split_row(
            Layout(name="hardware", ratio=1),
            Layout(name="anomaly", ratio=1),
        )
        if want_space:
            layout["space"].split_row(
                Layout(name="weather", ratio=1),
                Layout(name="storm", ratio=1),
            )
        layout["bottom"].split_row(
            Layout(name="logs", ratio=3),
            Layout(name="notifications", ratio=2),
        )
        return layout

    # Wide layout — row sizing banner tier-aware, status rows sized for densest panel.
    layout.split_column(
        Layout(name="banner", size=9 if show_banner else 0),
        Layout(name="top", size=11),
        Layout(name="middle"),
        Layout(name="space", size=12),
        Layout(name="bottom", size=12),
        Layout(name="footer", size=4),
    )

    layout["top"].split_row(
        Layout(name="system", ratio=1),
        Layout(name="pipeline", ratio=1),
        Layout(name="hardware", ratio=1),
        Layout(name="anomaly", ratio=1),
    )
    layout["space"].split_row(
        Layout(name="weather", ratio=1),
        Layout(name="storm", ratio=1),
    )
    layout["bottom"].split_row(
        Layout(name="logs", ratio=3),
        Layout(name="notifications", ratio=2),
    )
    return layout


class Dashboard:
    def __init__(self, refresh: float = 0.5, show_banner: bool = True, waterfall_only: bool = False,
                 compact: bool | None = None):
        self.console = Console()
        self.refresh = refresh
        self.compact = _is_compact() if compact is None else compact
        # The user's banner preference is independent of compact mode — we
        # render a small banner in compact, the full banner in wide. Toggling
        # compact should never forget the user's "show/hide" choice.
        self._banner_pref = show_banner
        self.show_banner = show_banner
        self.waterfall_only = waterfall_only

        self.sys_p = SystemPanel()
        self.pipe_p = PipelinePanel()
        self.hw_p = HardwarePanel()
        wf_width = max(40 if self.compact else 60, shutil.get_terminal_size().columns - 6)
        self.wf_p = WaterfallPanel(width=wf_width)
        self.anom_p = RFAnomalyPanel(self.wf_p)
        self.weather_p = SpaceWeatherPanel()
        self.storm_p = StormPanel()
        self.log_p = LogPanel()
        self.note_p = NotificationPanel()

        self.paused = False
        self.layout = build_layout(self.show_banner, self.waterfall_only, self.compact)
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
        if r:
            try:
                return sys.stdin.read(1)
            except Exception:
                return None
        return None

    # render ---
    def _render(self):
        if self.waterfall_only:
            self.layout["middle"].update(self.wf_p.render())
            return

        if self.show_banner:
            self.layout["banner"].update(
                compact_banner() if self.compact else full_banner()
            )
        self.layout["system"].update(self.sys_p.render())
        self.layout["pipeline"].update(self.pipe_p.render())
        self.layout["hardware"].update(self.hw_p.render())
        self.layout["middle"].update(self.wf_p.render())
        # Anomaly panel reads waterfall metrics — render after waterfall ticks.
        self.layout["anomaly"].update(self.anom_p.render())
        # "space" is optional in compact mode on short screens — skip the
        # weather/storm render when those slots don't exist.
        try:
            self.layout["weather"].update(self.weather_p.render())
            self.layout["storm"].update(self.storm_p.render())
        except KeyError:
            pass
        self.layout["logs"].update(self.log_p.render())
        self.layout["notifications"].update(self.note_p.render())
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
            self._wf_idx = (self._wf_idx + 1) % len(self._wf_modes)
            self.wf_p.set_mode(self._wf_modes[self._wf_idx])
            self.note_p.push("INFO", f"waterfall mode: {self._wf_modes[self._wf_idx]}")
        elif k in ("r", "R"):
            cur = os.getenv("DSLV_DASHBOARD_REAL_SDR", "0")
            new = "0" if cur == "1" else "1"
            os.environ["DSLV_DASHBOARD_REAL_SDR"] = new
            self.note_p.push("INFO", f"real SDR mode: {'ON' if new == '1' else 'OFF'}")
        elif k in ("h", "H"):
            if not self.waterfall_only:
                self._banner_pref = not self._banner_pref
                self.show_banner = self._banner_pref
                self.layout = build_layout(self.show_banner, self.waterfall_only, self.compact)
                self.note_p.push("INFO", f"banner: {'shown' if self.show_banner else 'hidden'}")
        elif k in ("c", "C"):
            if not self.waterfall_only:
                self.compact = not self.compact
                self.show_banner = self._banner_pref
                self.layout = build_layout(self.show_banner, self.waterfall_only, self.compact)
                self.note_p.push("INFO", f"compact: {'ON' if self.compact else 'OFF'}")
        elif k == "[":
            self.wf_p.adjust_floor(-5.0)
            self.note_p.push("INFO", f"floor: {self.wf_p.dbm_floor} dBm")
        elif k == "]":
            self.wf_p.adjust_floor(5.0)
            self.note_p.push("INFO", f"floor: {self.wf_p.dbm_floor} dBm")
        elif k == "{":
            self.wf_p.adjust_ceil(-5.0)
            self.note_p.push("INFO", f"ceil: {self.wf_p.dbm_ceil} dBm")
        elif k == "}":
            self.wf_p.adjust_ceil(5.0)
            self.note_p.push("INFO", f"ceil: {self.wf_p.dbm_ceil} dBm")
        elif k in ("p", "P"):
            self.wf_p.cycle_palette()
            self.note_p.push("INFO", "palette cycled")
        elif k in ("s", "S"):
            self.wf_p.show_spectrum = not self.wf_p.show_spectrum
            self.note_p.push("INFO", f"spectrum: {'ON' if self.wf_p.show_spectrum else 'OFF'}")

    def run(self):
        self._boot_animation()
        self.log_p.start()
        self.note_p.push("INFO", "dashboard online")
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
            self.log_p.stop()
            self.console.print("\n[bold bright_cyan]Dashboard offline. Pipeline continues in background.[/]\n")


def _signal_handler(sig, frame):
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description="DSLV-ZPDI Operations Dashboard")
    parser.add_argument("--refresh", type=float, default=0.5, help="refresh interval (s)")
    parser.add_argument("--no-banner", action="store_true", help="hide startup banner")
    parser.add_argument("--no-boot", action="store_true", help="skip boot animation")
    parser.add_argument("--waterfall-only", action="store_true", help="render only the waterfall panel")
    parser.add_argument("--compact", action="store_true", help="force compact layout (5\" DSI)")
    parser.add_argument("--wide", action="store_true", help="force wide layout (disable compact auto-detect)")
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    compact: bool | None = None
    if args.compact:
        compact = True
    elif args.wide:
        compact = False
    dash = Dashboard(refresh=args.refresh, show_banner=not args.no_banner,
                     waterfall_only=args.waterfall_only, compact=compact)
    if args.no_boot:
        dash._boot_animation = lambda: None  # type: ignore
    dash.run()


if __name__ == "__main__":
    main()
