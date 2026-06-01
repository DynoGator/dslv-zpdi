"""CME / Geomagnetic-storm tracker panel.

Surfaces NOAA storm progression — escalation, peak, recession — derived
from the planetary K-index trend, plus the most recent NOAA alerts
(CME warnings, geomagnetic storm watches, radio blackouts).
"""

from __future__ import annotations

import time

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from dashboard.noaa import get_feed

_PHASE_STYLES = {
    "QUIET":      ("◯", "bright_green",  "no active geomagnetic disturbance"),
    "ESCALATING": ("▲", "bright_yellow", "Kp climbing — storm onset"),
    "PEAK":       ("⬢", "bright_red",    "elevated Kp sustained — storm at peak"),
    "RECEDING":   ("▼", "yellow",        "Kp falling — storm receding"),
    "UNKNOWN":    ("?", "dim",           "no recent Kp data"),
}


def _g_intensity_label(g: str) -> str:
    return {
        "G0": "none",
        "G1": "minor",
        "G2": "moderate",
        "G3": "strong",
        "G4": "severe",
        "G5": "extreme",
    }.get(g, "?")


def _alert_priority(headline: str) -> tuple[str, str]:
    """Return (icon, style) for an alert headline by keyword."""
    s = headline.lower()
    if "g4" in s or "g5" in s or "extreme" in s or "x-class" in s:
        return ("⬢", "bright_red")
    if "warning" in s or "g3" in s or "severe" in s or "m-class" in s:
        return ("▲", "bright_red")
    if "watch" in s or "g2" in s or "g1" in s or "alert" in s:
        return ("△", "bright_yellow")
    if "summary" in s or "report" in s:
        return ("·", "dim")
    return ("◦", "bright_white")


def _alert_is_relevant(headline: str) -> bool:
    """Filter alerts down to space-weather relevant ones."""
    s = headline.lower()
    keys = (
        "geomagnetic", "kp", "g1", "g2", "g3", "g4", "g5",
        "cme", "coronal mass", "solar flare", "x-ray", "x-class", "m-class",
        "radio blackout", "r1", "r2", "r3", "r4", "r5",
        "radiation", "s1", "s2", "s3", "s4", "s5",
        "proton", "solar wind", "storm",
    )
    return any(k in s for k in keys)


class StormPanel:
    def __init__(self, border_style: str = "bright_red"):
        self.border_style = border_style
        self.feed = get_feed()

    def render(self, compact: bool = False) -> Panel:
        snap = self.feed.snapshot()
        phase = snap.get("phase", "UNKNOWN")
        g = snap.get("g_scale", "G0")
        alerts = snap.get("alerts", []) or []

        glyph, phase_sty, phase_desc = _PHASE_STYLES.get(phase, _PHASE_STYLES["UNKNOWN"])

        t = Table.grid(padding=(0, 1), expand=True)
        t.add_column(style="bright_cyan", justify="right", no_wrap=True)
        t.add_column()

        if compact:
            # Row 1: Phase + G-Scale
            t.add_row("Strm", f"[{phase_sty}]{glyph} {phase[:8]}[/] [dim]•[/] {g}")
            # Row 2: Alert
            relevant = [a for a in alerts if _alert_is_relevant(a.get("headline", ""))]
            if relevant:
                icon, sty = _alert_priority(relevant[0].get("headline", ""))
                t.add_row("Alrt", f"[{sty}]{icon} {relevant[0].get('headline', '')[:12]}[/]")
            else:
                t.add_row("Alrt", "[dim]none[/]")
        else:
            # Status footer
            last = snap.get("last_update", 0.0)
            if last == 0.0:
                footer_txt = Text("poll...", style="dim")
            else:
                age = int(time.time() - last)
                footer_txt = Text(f"NOAA {age}s", style="dim")
            t.add_row("", footer_txt)

        title = f"[bold {self.border_style}]▓ STORM ▓[/]" if compact else f"[bold {self.border_style}]▓ STORM / CME ▓[/]"
        return Panel(
            t,
            title=title,
            border_style=self.border_style,
            padding=(0, 1),
        )

