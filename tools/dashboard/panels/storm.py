"""CME / Geomagnetic-storm tracker panel.

Surfaces NOAA storm progression — escalation, peak, recession — derived
from the planetary K-index trend, plus the most recent NOAA alerts
(CME warnings, geomagnetic storm watches, radio blackouts).
"""

from __future__ import annotations

import math
import time

from rich.markup import escape as _esc
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

    def render(self) -> Panel:
        snap = self.feed.snapshot()
        phase = snap.get("phase", "UNKNOWN")
        kp = snap.get("kp_now", float("nan"))
        g = snap.get("g_scale", "G0")
        r = snap.get("r_scale", "R0")
        flare = snap.get("flare", "—")
        history = snap.get("kp_history", [])
        alerts = snap.get("alerts", []) or []

        glyph, phase_sty, phase_desc = _PHASE_STYLES.get(phase, _PHASE_STYLES["UNKNOWN"])

        t = Table.grid(padding=(0, 2), expand=True)
        t.add_column(style="bright_cyan", justify="right", no_wrap=True)
        t.add_column()

        # Phase headline
        head = Text()
        head.append(f"{glyph} {phase}", style=f"bold {phase_sty}")
        head.append(f"   {phase_desc}", style="dim")
        t.add_row("Phase", head)

        # Trend (recent Kp series compared to prior)
        clean = [v for v in history if not (v is None or math.isnan(v))]
        if len(clean) >= 6:
            recent = sum(clean[-3:]) / 3.0
            prior = sum(clean[-6:-3]) / 3.0
            delta = recent - prior
            arrow = "→"
            sty = "bright_white"
            if delta > 0.3:
                arrow = "↗"
                sty = "bright_yellow"
            elif delta < -0.3:
                arrow = "↘"
                sty = "yellow"
            trend_text = f"{arrow}  ΔKp = {delta:+.2f}  (now {recent:.2f}, prev {prior:.2f})"
        else:
            sty = "dim"
            trend_text = "insufficient samples"
        t.add_row("Trend", Text(trend_text, style=sty))

        # Storm scales
        scales = Text()
        scales.append(f"{g}", style=f"bold {phase_sty}")
        scales.append(f" {_g_intensity_label(g)}", style="dim")
        scales.append("   ")
        scales.append(f"{r}", style=f"bold {phase_sty if r != 'R0' else 'bright_green'}")
        scales.append("   ")
        scales.append(f"flare {flare}", style="bright_white")
        t.add_row("Scales", scales)

        # Peak in window
        if clean:
            peak_kp = max(clean[-12:])
            t.add_row("Peak Kp", Text(
                f"{peak_kp:.2f} (last hr)",
                style="bright_red" if peak_kp >= 7 else "bright_yellow" if peak_kp >= 5 else "bright_green"
            ))

        # Alerts
        relevant = [a for a in alerts if _alert_is_relevant(a.get("headline", ""))][:3]
        if not relevant:
            t.add_row("Alerts", Text("no active CME/geomagnetic alerts", style="dim"))
        else:
            for a in relevant:
                icon, sty = _alert_priority(a.get("headline", ""))
                line = Text()
                line.append(f"{icon} ", style=sty)
                line.append(_esc(a.get("headline", ""))[:96], style=sty)
                t.add_row("", line)

        # Status footer
        last = snap.get("last_update", 0.0)
        err = snap.get("last_error")
        if last == 0.0:
            footer_txt = Text("connecting to NOAA SWPC…", style="dim")
        else:
            age = int(time.time() - last)
            footer_txt = Text(f"NOAA · {age}s ago", style="dim")
            if err:
                footer_txt.append(f" · {_esc(str(err))[:40]}", style="yellow")
        t.add_row("", footer_txt)

        return Panel(
            t,
            title=f"[bold {self.border_style}]▓ CME / GEOMAGNETIC STORM ▓[/]",
            border_style=self.border_style,
            padding=(0, 1),
        )
