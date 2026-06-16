"""Space-weather panel — NOAA SWPC live feed.

Renders Kp, solar wind, IMF Bz, X-ray flare class, F10.7 flux, and
derived ionosphere/magnetosphere status. Data comes from the shared
SpaceWeatherFeed singleton — this panel never blocks on HTTP.
"""

from __future__ import annotations

import math
import time

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from dashboard.noaa import get_feed


def _kp_style(kp: float) -> str:
    if math.isnan(kp):
        return "dim"
    if kp >= 7:
        return "bright_red"
    if kp >= 5:
        return "bright_yellow"
    if kp >= 4:
        return "yellow"
    return "bright_green"


def _flare_style(flare: str) -> str:
    if not flare or flare == "—":
        return "dim"
    head = flare[0]
    return {
        "X": "bright_red",
        "M": "bright_yellow",
        "C": "yellow",
        "B": "bright_green",
        "A": "bright_green",
    }.get(head, "white")


def _bz_style(bz: float) -> str:
    """Southward (negative) Bz pumps energy into the magnetosphere."""
    if math.isnan(bz):
        return "dim"
    if bz <= -10:
        return "bright_red"
    if bz <= -5:
        return "bright_yellow"
    if bz <= 0:
        return "yellow"
    return "bright_green"


def _wind_style(speed: float) -> str:
    if math.isnan(speed):
        return "dim"
    if speed >= 700:
        return "bright_red"
    if speed >= 500:
        return "bright_yellow"
    if speed >= 400:
        return "yellow"
    return "bright_green"


_TREND_GLYPHS = {
    "RAMP_UP":   ("▲", "bright_red"),
    "PEAK":      ("⬢", "bright_red"),
    "RAMP_DOWN": ("▼", "yellow"),
    "STABLE":    ("◦", "bright_green"),
}


def _magneto_state(kp: float, bz: float, trend: str = "STABLE") -> tuple[str, str, str]:
    glyph, trend_sty = _TREND_GLYPHS.get(trend, ("?", "dim"))
    if math.isnan(kp):
        return "?", "dim", glyph
    if kp >= 7 or (not math.isnan(bz) and bz <= -15):
        return "COMPRESSED · STORM", "bright_red", glyph
    if kp >= 5 or (not math.isnan(bz) and bz <= -8):
        return "DISTURBED", "bright_yellow", glyph
    if kp >= 4:
        return "UNSETTLED", "yellow", glyph
    return "STABLE", "bright_green", glyph


def _iono_state(flare: str, kp: float, trend: str = "STABLE") -> tuple[str, str, str]:
    glyph, trend_sty = _TREND_GLYPHS.get(trend, ("?", "dim"))
    head = flare[0] if flare and flare != "—" else ""
    if head == "X":
        return "BLACKOUT (HF)", "bright_red", glyph
    if head == "M":
        return "DEGRADED (sunlit)", "bright_yellow", glyph
    if not math.isnan(kp) and kp >= 6:
        return "TID / SCINTILLATION", "bright_yellow", glyph
    if head == "C":
        return "MINOR ABSORPTION", "yellow", glyph
    return "NOMINAL", "bright_green", glyph


def _f107_style(sfu: float) -> str:
    if math.isnan(sfu):
        return "dim"
    if sfu >= 200:
        return "bright_red"
    if sfu >= 150:
        return "bright_yellow"
    if sfu >= 100:
        return "yellow"
    return "bright_green"


def _spark(values: list[float], width: int = 16) -> Text:
    """Tiny braille/block sparkline from the most recent `width` samples."""
    chars = "▁▂▃▄▅▆▇█"
    clean = [v for v in values if not (v is None or math.isnan(v))]
    if not clean:
        return Text("·" * width, style="dim")
    sample = clean[-width:]
    lo = min(sample)
    hi = max(sample)
    rng = hi - lo if hi > lo else 1.0
    out = Text()
    for v in sample:
        idx = int((v - lo) / rng * (len(chars) - 1))
        idx = max(0, min(len(chars) - 1, idx))
        if v >= 7:
            sty = "bright_red"
        elif v >= 5:
            sty = "bright_yellow"
        elif v >= 4:
            sty = "yellow"
        else:
            sty = "bright_green"
        out.append(chars[idx], style=sty)
    if len(sample) < width:
        out.append(" " * (width - len(sample)), style="dim")
    return out


class SpaceWeatherPanel:
    def __init__(self, border_style: str = "bright_blue"):
        self.border_style = border_style
        self.feed = get_feed()

    def render(self, compact: bool = False) -> Panel:
        snap = self.feed.snapshot()
        kp = snap.get("kp_now", float("nan"))
        bz = snap.get("bz_nt", float("nan"))
        bt = snap.get("bt_nt", float("nan"))
        speed = snap.get("speed_kms", float("nan"))
        flare = snap.get("flare", "—")
        f107 = snap.get("f107_sfu", float("nan"))
        g_scale = snap.get("g_scale", "G0")

        speed_trend = snap.get("speed_trend", "STABLE")
        bt_trend = snap.get("bt_trend", "STABLE")
        flux_trend = snap.get("flux_trend", "STABLE")

        magneto_text, magneto_sty, mag_glyph = _magneto_state(kp, bz, bt_trend)
        iono_text, iono_sty, iono_glyph = _iono_state(flare, kp, flux_trend)
        wind_glyph, _ = _TREND_GLYPHS.get(speed_trend, ("?", "dim"))

        t = Table.grid(padding=(0, 1), expand=True)
        t.add_column(style="bright_cyan", justify="right", no_wrap=True)
        t.add_column(no_wrap=True)

        # Kp + sparkline
        kp_str = f"{kp:4.1f}" if not math.isnan(kp) else " --"
        kp_line = Text()
        kp_line.append(f"{kp_str}", style=_kp_style(kp))
        kp_line.append(f" [{g_scale}]", style="bold " + _kp_style(kp))
        if not compact:
            kp_line.append(" ")
            kp_line.append_text(_spark(snap.get("kp_history", []), width=12))
        if compact:
            # Row 1: Kp + Flare + F10.7
            f107_s = f"{f107:3.0f}" if not math.isnan(f107) else " --"
            t.add_row("Kp", f"[{_kp_style(kp)}]{kp_str} [{g_scale}][/] [dim]•[/] {f107_s}f")
            # Row 2: Wind + IMF + Flare
            bz_str = f"{bz:+2.0f}" if not math.isnan(bz) else "--"
            bt_str = f"{bt:2.0f}" if not math.isnan(bt) else "--"
            speed_str = f"{speed:4.0f}k" if not math.isnan(speed) else "--"
            t.add_row("Wnd", f"{speed_str} [dim]•[/] Bt{bt_str} Bz{bz_str}")
            # Row 3: Mag + Ion + Flare
            t.add_row(
                "Env", f"[{magneto_sty}]{magneto_text[:6]}[/] [dim]•[/] [{iono_sty}]{iono_text[:6]}[/] [{_flare_style(flare)}]{flare[:2]}[/]")
        else:
            t.add_row("Magneto", Text(f"{mag_glyph} {magneto_text}", style="bold " + magneto_sty))
            t.add_row("Ionosph", Text(f"{iono_glyph} {iono_text}", style="bold " + iono_sty))

            # Status footer (compact)
            last = snap.get("last_update", 0.0)
            if last == 0.0:
                stat_txt = "[dim]poll...[/]"
            else:
                age = int(time.time() - last)
                err = snap.get("last_error")
                ok_glyph = "◉" if not err else "○"
                ok_sty = "bright_green" if not err else "yellow"
                stat_txt = f"[{ok_sty}]{ok_glyph}[/] [dim]NOAA {age}s"
                if err:
                    stat_txt += " !"
                stat_txt += "[/]"
            t.add_row("", Text.from_markup(stat_txt))

        title = f"[bold {self.border_style}]▓ WX ▓[/]" if compact else f"[bold {self.border_style}]▓ WEATHER ▓[/]"
        return Panel(
            t,
            title=title,
            border_style=self.border_style,
            padding=(0, 1),
        )
