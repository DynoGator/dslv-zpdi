"""ASCII banners — DynoGatorLabs / DSLV-ZPDI.

The banner scales itself to the current terminal width — `ansi_shadow`
at 110+ cols, `standard` at 80–109 cols, `mini` below that. Everything
flows through ``full_banner()`` and ``banner_height()`` so the Live
layout always reserves exactly the row count the chosen tier needs.
"""

from __future__ import annotations

import shutil

import pyfiglet
from rich.align import Align
from rich.console import Group
from rich.panel import Panel
from rich.text import Text


NEON_GREEN = "bright_green"
NEON_CYAN = "bright_cyan"
NEON_MAGENTA = "bright_magenta"
DIM_GREEN = "green"
AMBER = "yellow"


# Tier table: (min_cols, font, tagline, hud, brand_right)
_TIERS = (
    (
        110,
        "ansi_shadow",
        (
            "Distributed Sensor Locational Vectoring  ::  "
            "Zero-Point Data Integration  ::  GPS-Disciplined RF Metrology"
        ),
        "ANCHOR NODE  ::  KCET-ATLAS RUNTIME  ::  2026 DYNOGATORLABS",
        "RF METROLOGY · COHERENCE ENGINE · TIER 1 ANCHOR",
    ),
    (
        80,
        "standard",
        "GPS-Disciplined RF Metrology · Coherence Engine",
        "ANCHOR · KCET-ATLAS · 2026 DYNOGATORLABS",
        "RF METROLOGY · TIER 1 ANCHOR",
    ),
    (
        0,
        "mini",
        "RF Metrology · Coherence Engine",
        "KCET-ATLAS · 2026",
        "TIER 1 ANCHOR",
    ),
)


def _pick_tier(cols: int | None = None):
    c = cols if cols is not None else shutil.get_terminal_size((80, 24)).columns
    for min_cols, font, tagline, hud, brand_right in _TIERS:
        if c >= min_cols:
            return font, tagline, hud, brand_right
    return _TIERS[-1][1:]


def _figlet(text: str, font: str) -> tuple[Text, int]:
    lines = [
        line for line in pyfiglet.figlet_format(text, font=font).splitlines()
        if line.strip()
    ]
    art = "\n".join(lines)
    return Text(art, style=f"bold {NEON_GREEN}", no_wrap=True), len(lines)


def banner_height(cols: int | None = None) -> int:
    """Total panel height (figlet rows + brand + tagline + hud + 2 borders)."""
    font, _, _, _ = _pick_tier(cols)
    _, rows = _figlet("DSLV-ZPDI", font)
    return rows + 3 + 2


# Preserved for imports that expect a module-level constant — reflects the
# tier most terminals will land in so static callers still get a sane default.
BANNER_HEIGHT = banner_height()


def _brand_line(brand_right: str) -> Text:
    t = Text(no_wrap=True, justify="center", overflow="ellipsis")
    t.append("◤ ", style=f"bold {NEON_CYAN}")
    t.append("DynoGatorLabs", style=f"bold {NEON_CYAN}")
    t.append(" ◢  ", style=f"bold {NEON_CYAN}")
    t.append(brand_right, style=f"bold {AMBER}")
    return t


def _tagline(text: str) -> Text:
    return Text(text, style=f"italic {DIM_GREEN}", no_wrap=True, overflow="ellipsis")


def _hud_line(text: str) -> Text:
    return Text(
        f"▓▒░ {text} ░▒▓",
        style=f"bold {NEON_MAGENTA}",
        no_wrap=True,
        overflow="ellipsis",
    )


def full_banner() -> Panel:
    """Composed banner Panel, sized to current terminal width."""
    font, tagline, hud, brand_right = _pick_tier()
    figlet_text, _ = _figlet("DSLV-ZPDI", font)
    group = Group(
        Align.center(_brand_line(brand_right)),
        Align.center(figlet_text),
        Align.center(_tagline(tagline)),
        Align.center(_hud_line(hud)),
    )
    return Panel(
        group,
        border_style=NEON_GREEN,
        padding=(0, 1),
    )


def compact_banner() -> Panel:
    """2-row banner for the 5\" DSI compact layout.

    A figlet banner does not fit in a 4-row layout slot once borders and
    padding are accounted for, so the compact mode renders a single-line
    brand bar + a single-line status-ish tagline instead.
    """
    line1 = Text(no_wrap=True, justify="center", overflow="ellipsis")
    line1.append("◤ ", style=f"bold {NEON_CYAN}")
    line1.append("DSLV-ZPDI", style=f"bold {NEON_GREEN}")
    line1.append(" ◢ ", style=f"bold {NEON_CYAN}")
    line1.append("DynoGatorLabs", style=f"bold {NEON_CYAN}")
    line1.append(" · ", style="dim")
    line1.append("Tier 1 Anchor", style=f"bold {AMBER}")

    line2 = Text(
        "RF Metrology · Coherence Engine · KCET-ATLAS",
        style=f"italic {DIM_GREEN}",
        no_wrap=True,
        overflow="ellipsis",
        justify="center",
    )
    return Panel(
        Group(Align.center(line1), Align.center(line2)),
        border_style=NEON_GREEN,
        padding=(0, 1),
    )


def startup_animation_frames(console):
    """Boot sequence lines, colour-tagged for direct Rich printing."""
    return [
        f"[{AMBER}]▶ INITIALIZING KCET-ATLAS RUNTIME...",
        f"[{AMBER}]▶ CALIBRATING THE AETHER...",
        f"[{AMBER}]▶ LOCKING ONTO GPS CONSTELLATION...",
        f"[{NEON_CYAN}]▶ CHECKING HACKRF PERMISSIONS...",
        f"[{NEON_CYAN}]▶ ASKING THE PI 5 NICELY...",
        f"[{NEON_MAGENTA}]▶ IGNITING THE PIPELINE...",
        f"[{NEON_GREEN}]✔ DSLV-ZPDI OPERATIONAL",
    ]
