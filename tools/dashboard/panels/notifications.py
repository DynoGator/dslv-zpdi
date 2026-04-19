"""Notifications + dark-humor scan message ticker."""

import collections
import time

from rich.panel import Panel
from rich.text import Text

from dashboard.humor import pick_scan, pick_glitch


class NotificationPanel:
    def __init__(self, max_items: int = 8):
        self.max_items = max_items
        self.items: collections.deque[tuple[float, str, str]] = collections.deque(maxlen=max_items)
        self._last_humor = 0.0
        self._last_glitch = 0.0

    def push(self, level: str, msg: str):
        self.items.appendleft((time.time(), level.upper(), msg))

    def tick_humor(self):
        now = time.time()
        if now - self._last_humor >= 4.0:
            self._last_humor = now
            self.push("SCAN", pick_scan())
        # sprinkle occasional glitch
        if now - self._last_glitch >= 37.0:
            self._last_glitch = now
            self.push("GLITCH", pick_glitch())

    def render(self) -> Panel:
        self.tick_humor()
        t = Text()
        if not self.items:
            t.append("[dim]...[/]")
        else:
            for ts, lvl, msg in self.items:
                age = int(time.time() - ts)
                tag = f"[{age:3d}s]"
                if lvl == "ERROR" or lvl == "VIOLATION":
                    sty = "bright_red"
                    icon = "✗"
                elif lvl == "WARN":
                    sty = "yellow"
                    icon = "!"
                elif lvl == "GLITCH":
                    sty = "bright_magenta"
                    icon = "▓"
                elif lvl == "SCAN":
                    sty = "bright_cyan"
                    icon = "◎"
                else:
                    sty = "bright_green"
                    icon = "·"
                t.append(f" {icon} ", style=sty)
                t.append(f"{tag} ", style="dim")
                t.append(f"{lvl:<7} ", style=f"bold {sty}")
                t.append(f"{msg}\n", style=sty)
        return Panel(
            t,
            title="[bold bright_magenta]▓ NOTIFICATIONS ▓[/]",
            border_style="bright_magenta",
            padding=(0, 1),
        )
