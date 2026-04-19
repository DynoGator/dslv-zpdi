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

from dashboard.banner import full_banner, startup_animation_frames
from dashboard.panels.hardware import HardwarePanel
from dashboard.panels.logs import LogPanel
from dashboard.panels.notifications import NotificationPanel
from dashboard.panels.pipeline import PipelinePanel
from dashboard.panels.system import SystemPanel
from dashboard.panels.waterfall import WaterfallPanel


def footer_panel() -> Panel:
    t = Text()
    keys = [
        ("q", "quit"),
        ("space", "pause"),
        ("m", "wf-mode"),
        ("r", "real-sdr"),
        ("h", "help"),
    ]
    for k, desc in keys:
        t.append(" [ ", style="dim")
        t.append(k, style="bold bright_yellow on black")
        t.append(" ] ", style="dim")
        t.append(desc, style="bright_white")
        t.append("  ", style="dim")
    t.append("\n")
    t.append(
        "DSLV-ZPDI :: DynoGatorLabs :: Tier 1 Anchor :: "
        "If it moves, it gets coherence-scored.",
        style="italic dim bright_white",
    )
    return Panel(t, border_style="bright_black", padding=(0, 1))


def build_layout(show_banner: bool) -> Layout:
    layout = Layout()

    layout.split_column(
        Layout(name="banner", size=9 if show_banner else 0),
        Layout(name="top", size=10),
        Layout(name="middle"),
        Layout(name="bottom", size=12),
        Layout(name="footer", size=4),
    )

    layout["top"].split_row(
        Layout(name="system", ratio=1),
        Layout(name="pipeline", ratio=1),
        Layout(name="hardware", ratio=1),
    )
    layout["bottom"].split_row(
        Layout(name="logs", ratio=3),
        Layout(name="notifications", ratio=2),
    )
    return layout


class Dashboard:
    def __init__(self, refresh: float = 0.5, show_banner: bool = True):
        self.console = Console()
        self.refresh = refresh
        self.show_banner = show_banner

        self.sys_p = SystemPanel()
        self.pipe_p = PipelinePanel()
        self.hw_p = HardwarePanel()
        self.wf_p = WaterfallPanel(width=max(60, shutil.get_terminal_size().columns - 6))
        self.log_p = LogPanel()
        self.note_p = NotificationPanel()

        self.paused = False
        self.layout = build_layout(self.show_banner)
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
        if self.show_banner:
            self.layout["banner"].update(full_banner())
        self.layout["system"].update(self.sys_p.render())
        self.layout["pipeline"].update(self.pipe_p.render())
        self.layout["hardware"].update(self.hw_p.render())
        self.layout["middle"].update(self.wf_p.render())
        self.layout["logs"].update(self.log_p.render())
        self.layout["notifications"].update(self.note_p.render())
        self.layout["footer"].update(footer_panel())

    def _boot_animation(self):
        frames = startup_animation_frames(self.console)
        for line in frames:
            self.console.print("  " + line)
            time.sleep(0.28)
        time.sleep(0.4)

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
            self.show_banner = not self.show_banner
            self.layout = build_layout(self.show_banner)
            self.note_p.push("INFO", f"banner: {'shown' if self.show_banner else 'hidden'}")

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
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    dash = Dashboard(refresh=args.refresh, show_banner=not args.no_banner)
    if args.no_boot:
        dash._boot_animation = lambda: None  # type: ignore
    dash.run()


if __name__ == "__main__":
    main()
