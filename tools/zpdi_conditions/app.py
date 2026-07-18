"""Rich TUI for the ZPDI_CONDITIONS local dashboard.

Keyboard controls:
    [space]  force an immediate refresh of every metric
    q        quit
    Ctrl+C   quit

The layout is optimized for a 10" touchscreen (≈1280×800) by default: a tight
two-column grid of metric cards with large values, clear labels, and a
scroll-aware legend. It uses only ``rich`` (already a project dependency) and
standard-library keyboard handling.
"""

from __future__ import annotations

import select
import shutil
import signal
import sys
import termios
import threading
import time
import tty
from datetime import datetime, timezone
from typing import Any

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from zpdi_conditions.collectors import Metric, MetricStore, start_collectors
from zpdi_conditions.config import ZpdiConditionsConfig, load_config

# Order in which metrics appear on the dashboard.
METRIC_ORDER = [
    "kp",
    "vsw",
    "bt",
    "bz",
    "ionosphere",
    "temperature",
    "wind",
    "humidity",
    "pressure",
    "pm25",
    "gamma",
    "cosmic",
]


def _fmt_timestamp(ts: datetime | None) -> str:
    if ts is None:
        return "never"
    # Prefer local time for readability; append UTC if it was sourced as UTC.
    local = ts.astimezone()
    return local.strftime("%H:%M:%S")


def _age_style(seconds: float | None) -> str:
    if seconds is None:
        return "dim"
    if seconds < 120:
        return "bright_green"
    if seconds < 600:
        return "bright_yellow"
    return "bright_red"


def _render_metric(metric: Metric, compact: bool = False) -> Panel:
    """Render a single metric card."""
    age = metric.age_seconds()
    age_style = _age_style(age)

    # Title bar: label + source icon.
    title = Text()
    title.append(metric.label, style="bold bright_white")
    if metric.error:
        title.append("  ⚠", style="bold bright_red")

    # Main value line.
    if metric.error:
        value_text = Text(metric.error, style="bold bright_red", no_wrap=True)
        value_text.overflow = "ellipsis"
    else:
        value_text = Text(no_wrap=True, overflow="ellipsis")
        value_text.append(metric.value, style="bold bright_cyan")
        if metric.unit:
            value_text.append(" ", style="default")
            value_text.append(metric.unit, style="bright_white")

    # Metadata lines.
    meta = Text(no_wrap=True, overflow="ellipsis")
    if metric.error:
        meta.append(f"src: {metric.source}", style="dim")
    else:
        meta.append(metric.trend, style="bright_yellow")
        meta.append("  •  ", style="dim")
        meta.append(f"refresh: {metric.interval_seconds // 60}m", style="dim")

    ts_text = Text(no_wrap=True, overflow="ellipsis")
    ts_text.append("last: ", style="dim")
    ts_text.append(_fmt_timestamp(metric.last_refresh), style=age_style)
    if age is not None:
        if age < 60:
            age_label = f"{age:.0f}s ago"
        elif age < 3600:
            age_label = f"{age / 60:.0f}m ago"
        else:
            age_label = f"{age / 3600:.1f}h ago"
        ts_text.append(f" ({age_label})", style="dim")

    body = Group(value_text, meta, ts_text)
    border = "bright_red" if metric.error else "bright_black"
    return Panel(body, title=title, border_style=border, padding=(0, 1))


def _build_grid(metrics: dict[str, Metric], columns: int = 2) -> Table:
    """Arrange metric cards into a grid."""
    table = Table.grid(expand=True)
    for _ in range(columns):
        table.add_column(ratio=1)

    row: list[Panel] = []
    for key in METRIC_ORDER:
        metric = metrics.get(key)
        if metric is None:
            metric = Metric(key=key, label=key, category="Missing")
        row.append(_render_metric(metric))
        if len(row) == columns:
            table.add_row(*row)
            row = []
    if row:
        while len(row) < columns:
            row.append(Panel("", border_style="black"))
        table.add_row(*row)
    return table


def _footer(last_render: datetime, paused: bool = False) -> Panel:
    pulse = "●" if int(time.time() * 2) % 2 == 0 else "○"
    status = Text(no_wrap=True, overflow="ellipsis")
    if paused:
        status.append("⏸ PAUSED  ", style="bold yellow")
    else:
        status.append(f"{pulse} LIVE  ", style="bold bright_cyan")
    status.append("ZPDI_CONDITIONS", style="bold bright_white")
    status.append("  |  ", style="dim")
    status.append("space", style="bold bright_yellow")
    status.append("=refresh  ", style="dim")
    status.append("q", style="bold bright_yellow")
    status.append("=quit", style="dim")
    status.append("  |  ", style="dim")
    status.append(last_render.strftime("%Y-%m-%d %H:%M:%S UTC"), style="dim")
    return Panel(status, border_style="bright_black", padding=(0, 1))


def _header(cfg: ZpdiConditionsConfig) -> Panel:
    text = Text(justify="center")
    text.append("ZPDI_CONDITIONS", style="bold bright_cyan")
    text.append("  —  ", style="dim")
    text.append(cfg.location_name, style="bright_white")
    text.append("  —  ", style="dim")
    text.append("Live Local & Space Weather", style="italic bright_white")
    return Panel(text, border_style="bright_black", padding=(0, 1))


# ---------------------------------------------------------------------------
# Keyboard handling
# ---------------------------------------------------------------------------

class _Keyboard:
    def __init__(self):
        self._orig_attrs: Any = None
        self._fd: int | None = None

    def enter_raw(self) -> None:
        if not sys.stdin.isatty():
            return
        self._fd = sys.stdin.fileno()
        self._orig_attrs = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)

    def exit_raw(self) -> None:
        if self._orig_attrs is not None and self._fd is not None:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._orig_attrs)

    def read_key(self) -> str | None:
        if self._fd is None or not sys.stdin.isatty():
            return None
        r, _, _ = select.select([sys.stdin], [], [], 0.0)
        if not r:
            return None
        try:
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                seq = ""
                while True:
                    r2, _, _ = select.select([sys.stdin], [], [], 0.0)
                    if not r2:
                        break
                    seq += sys.stdin.read(1)
                return f"\x1b{seq}"
            return ch
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------------------------

class ConditionsDashboard:
    def __init__(self, cfg: ZpdiConditionsConfig | None = None):
        self.cfg = cfg if cfg is not None else load_config()
        self.console = Console(force_terminal=True)
        self.store = MetricStore(self.cfg)
        self._keyboard = _Keyboard()
        self._collectors: list[threading.Thread] = []
        self._stop = threading.Event()
        self._manual_refresh_pending = False

    def _columns(self) -> int:
        layout = self.cfg.card_layout
        if layout == "one_column":
            return 1
        if layout == "two_column":
            return 2
        # Auto: use 1 column only on very narrow displays.
        try:
            cols, _ = shutil.get_terminal_size()
        except Exception:
            cols = 120
        return 1 if cols < 80 else 2

    def _render(self) -> Group:
        metrics = self.store.all()
        grid = _build_grid(metrics, columns=self._columns())
        footer = _footer(datetime.now(timezone.utc))
        return Group(_header(self.cfg), grid, footer)

    def _signal_handler(self, _sig: int, _frame: Any) -> None:
        self._stop.set()
        self.store.stop()

    def run(self) -> None:
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self._collectors = start_collectors(self.cfg, self.store)
        # Give collectors a moment to prime before first render.
        time.sleep(0.5)

        self._keyboard.enter_raw()
        try:
            refresh_per_second = max(1, int(self.cfg.tui_refresh_hz))
            with Live(
                self._render(),
                console=self.console,
                refresh_per_second=refresh_per_second,
                screen=True,
            ) as live:
                while not self._stop.is_set():
                    key = self._keyboard.read_key()
                    if key == " ":
                        self.store.request_refresh()
                        self._manual_refresh_pending = True
                    elif key in ("q", "Q"):
                        break

                    live.update(self._render())

                    if self._manual_refresh_pending:
                        # Leave the manual-refresh indicator up briefly.
                        self._manual_refresh_pending = False

                    time.sleep(1.0 / refresh_per_second)
        except KeyboardInterrupt:
            pass
        finally:
            self._keyboard.exit_raw()
            self.store.stop()
            for t in self._collectors:
                t.join(timeout=2.0)
            self.console.print(
                "\n[bold bright_cyan]ZPDI_CONDITIONS offline. DSLV-ZPDI stack is unaffected.[/]\n"
            )


def main() -> None:
    cfg = load_config()
    dash = ConditionsDashboard(cfg)
    dash.run()


if __name__ == "__main__":
    main()
