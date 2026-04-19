"""Live log panel: tails journald for dslv-zpdi service."""

import collections
import subprocess
import threading
import time

from rich.panel import Panel
from rich.text import Text


class LogPanel:
    def __init__(self, unit: str = "dslv-zpdi", max_lines: int = 14):
        self.unit = unit
        self.max_lines = max_lines
        self.lines: collections.deque[str] = collections.deque(maxlen=max_lines)
        self._started = False
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self):
        if self._started:
            return
        self._started = True
        self._thread = threading.Thread(target=self._tail, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _tail(self):
        while not self._stop.is_set():
            try:
                proc = subprocess.Popen(
                    [
                        "journalctl", "-u", self.unit, "-f", "-n", "20",
                        "--no-pager", "-o", "short-iso",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                )
                assert proc.stdout is not None
                for line in proc.stdout:
                    if self._stop.is_set():
                        proc.terminate()
                        return
                    self.lines.append(line.rstrip())
            except Exception:
                time.sleep(1)

    def _style_line(self, line: str) -> Text:
        ll = line.lower()
        if "error" in ll or "fail" in ll or "violation" in ll:
            style = "bright_red"
        elif "warn" in ll or "quarantin" in ll:
            style = "yellow"
        elif "ok" in ll or "start" in ll or "healthy" in ll:
            style = "bright_green"
        else:
            style = "bright_white"
        # keep last 120 chars max
        txt = line[-120:]
        return Text(txt, style=style, no_wrap=True, overflow="ellipsis")

    def render(self) -> Panel:
        t = Text()
        if not self.lines:
            t.append("[dim]waiting for journald...[/]", style="dim")
        else:
            for ln in self.lines:
                t.append_text(self._style_line(ln))
                t.append("\n")
        return Panel(
            t,
            title="[bold bright_white]▓ LIVE LOG ▓[/] [dim](journalctl -u dslv-zpdi -f)[/]",
            border_style="bright_white",
            padding=(0, 1),
        )
