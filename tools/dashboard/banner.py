"""ASCII banners — DynoGatorLabs / DSLV-ZPDI."""

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


def render_dynogatorlabs() -> Text:
    """Small-font top label."""
    art = pyfiglet.figlet_format("DynoGatorLabs", font="small")
    return Text(art.rstrip(), style=f"bold {NEON_CYAN}")


def render_dslv_zpdi() -> Text:
    """Big-font primary banner."""
    art = pyfiglet.figlet_format("DSLV-ZPDI", font="ansi_shadow")
    return Text(art.rstrip(), style=f"bold {NEON_GREEN}")


def render_tagline() -> Text:
    """Rotating subtitle."""
    return Text(
        "  Distributed Sensor Locational Vectoring  ::  "
        "Zero-Point Data Integration  ::  GPS-Disciplined RF Metrology",
        style=f"italic {DIM_GREEN}",
    )


def render_hud_border() -> Text:
    """Cyberpunk divider line."""
    return Text(
        "═" * 78 + "\n"
        "▓▒░ ANCHOR NODE — TIER 1 ░▒▓  "
        "▓▒░ KCET-ATLAS RUNTIME ░▒▓  "
        "▓▒░ 2026 DYNOGATORLABS ░▒▓\n"
        "═" * 78,
        style=f"bold {NEON_MAGENTA}",
    )


def full_banner() -> Panel:
    """Return composed banner Panel."""
    group = Group(
        Align.center(render_dynogatorlabs()),
        Align.center(render_dslv_zpdi()),
        Align.center(render_tagline()),
        Align.center(render_hud_border()),
    )
    return Panel(
        group,
        border_style=NEON_GREEN,
        padding=(0, 1),
    )


def startup_animation_frames(console):
    """Yield frames of a boot animation."""
    stages = [
        (f"[{AMBER}]▶ INITIALIZING KCET-ATLAS RUNTIME..."),
        (f"[{AMBER}]▶ CALIBRATING THE AETHER..."),
        (f"[{AMBER}]▶ LOCKING ONTO GPS CONSTELLATION..."),
        (f"[{NEON_CYAN}]▶ CHECKING HACKRF PERMISSIONS..."),
        (f"[{NEON_CYAN}]▶ ASKING THE PI 5 NICELY..."),
        (f"[{NEON_MAGENTA}]▶ IGNITING THE PIPELINE..."),
        (f"[{NEON_GREEN}]✔ DSLV-ZPDI OPERATIONAL"),
    ]
    return stages
