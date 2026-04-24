"""Space-weather panel — NOAA SWPC live feed.

Renders Kp, solar wind, IMF Bz, X-ray flare class, F10.7 flux, and
derived ionosphere/magnetosphere status. Data comes from the shared
SpaceWeatherFeed singleton — this panel never blocks on HTTP.
"""

from __future__ import annotations

import math
import time

from rich.markup import escape as _esc
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


def _magneto_state(kp: float, bz: float) -> tuple[str, str]:
    if math.isnan(kp):
        return "?", "dim"
    if kp >= 7 or (not math.isnan(bz) and bz <= -15):
        return "COMPRESSED · STORM", "bright_red"
    if kp >= 5 or (not math.isnan(bz) and bz <= -8):
        return "DISTURBED", "bright_yellow"
    if kp >= 4:
        return "UNSETTLED", "yellow"
    return "STABLE", "bright_green"


def _iono_state(flare: str, kp: float) -> tuple[str, str]:
    head = flare[0] if flare and flare != "—" else ""
    if head == "X":
        return "BLACKOUT (HF)", "bright_red"
    if head == "M":
        return "DEGRADED (sunlit)", "bright_yellow"
    if not math.isnan(kp) and kp >= 6:
        return "TID / SCINTILLATION", "bright_yellow"
    if head == "C":
        return "MINOR ABSORPTION", "yellow"
    return "NOMINAL", "bright_green"


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

    def render(self) -> Panel:
        snap = self.feed.snapshot()
        kp = snap.get("kp_now", float("nan"))
        bz = snap.get("bz_nt", float("nan"))
        bt = snap.get("bt_nt", float("nan"))
        speed = snap.get("speed_kms", float("nan"))
        density = snap.get("density", float("nan"))
        flare = snap.get("flare", "—")
        f107 = snap.get("f107_sfu", float("nan"))
        g_scale = snap.get("g_scale", "G0")
        r_scale = snap.get("r_scale", "R0")

        magneto_text, magneto_sty = _magneto_state(kp, bz)
        iono_text, iono_sty = _iono_state(flare, kp)

        t = Table.grid(padding=(0, 2), expand=True)
        t.add_column(style="bright_cyan", justify="right", no_wrap=True)
        t.add_column(no_wrap=True)

        # Kp + sparkline
        kp_str = f"{kp:4.2f}" if not math.isnan(kp) else "  --"
        kp_line = Text()
        kp_line.append(f"{kp_str}", style=_kp_style(kp))
        kp_line.append(f"  [{g_scale}]", style="bold " + _kp_style(kp))
        kp_line.append("  ")
        kp_line.append_text(_spark(snap.get("kp_history", []), width=16))
        t.add_row("Kp idx", kp_line)

        # Solar wind
        speed_str = f"{speed:4.0f} km/s" if not math.isnan(speed) else "    -- km/s"
        dens_str = f"{density:4.1f} p/cc" if not math.isnan(density) else "    -- p/cc"
        wind_line = Text()
        wind_line.append(speed_str, style=_wind_style(speed))
        wind_line.append("  ")
        wind_line.append(dens_str, style="bright_white")
        t.add_row("Sol. Wind", wind_line)

        # IMF
        bt_str = f"{bt:4.1f}" if not math.isnan(bt) else "  --"
        bz_str = f"{bz:+5.1f}" if not math.isnan(bz) else "   --"
        imf_line = Text()
        imf_line.append(f"Bt {bt_str} nT", style="bright_white")
        imf_line.append("  ")
        imf_line.append(f"Bz {bz_str} nT", style=_bz_style(bz))
        t.add_row("IMF", imf_line)

        # X-ray / flare class + R-scale
        xray_line = Text()
        xray_line.append(f"{flare}", style="bold " + _flare_style(flare))
        xray_line.append(f"  [{r_scale}]", style=_flare_style(flare))
        t.add_row("X-ray", xray_line)

        # F10.7
        f107_str = f"{f107:5.1f} sfu" if not math.isnan(f107) else "    -- sfu"
        t.add_row("F10.7", Text(f107_str, style=_f107_style(f107)))

        # Derived state
        t.add_row("Magneto", Text(magneto_text, style="bold " + magneto_sty))
        t.add_row("Ionos.", Text(iono_text, style="bold " + iono_sty))

        # Status footer
        last = snap.get("last_update", 0.0)
        if last == 0.0:
            stat_txt = "[dim]connecting to NOAA SWPC…[/]"
        else:
            age = int(time.time() - last)
            err = snap.get("last_error")
            ok_glyph = "◉" if not err else "○"
            ok_sty = "bright_green" if not err else "yellow"
            stat_txt = f"[{ok_sty}]{ok_glyph}[/] [dim]NOAA · {age}s ago"
            if err:
                stat_txt += f" · {_esc(str(err))[:40]}"
            stat_txt += "[/]"
        t.add_row("", Text.from_markup(stat_txt))

        return Panel(
            t,
            title=f"[bold {self.border_style}]▓ SPACE WEATHER ▓[/]",
            border_style=self.border_style,
            padding=(0, 1),
        )
