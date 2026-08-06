#!/usr/bin/env python3
"""
DSLV-ZPDI Boot Orchestrator — Retro-terminal startup sequence.

Verifies and (if needed) starts the systemd service chain in order, then
launches the Operations Dashboard. Designed for the Tier-1 Pi 5 touchscreen
autostart path.

Usage:
    tools/boot_orchestrator.py [--dashboard|--no-dashboard]

Exit codes:
    0  all critical services ready, dashboard launched (if requested)
    1  a critical service failed to start
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time

from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

console = Console(force_terminal=True, color_system="truecolor")

# ── ASCII art banners ────────────────────────────────────────────────────────

LOGO_SMALL = r"""
    ( )    ____  ____  _     ___      ____ ____   ___ ____
  ( )( )  |  _ \|  _ \| |   / _ \    |  _ \\___ \ |_ _|  _ \
    ( )   | | | | |_) | |  | | | |   | | | |__) | | || |_) |
   ATOMS  | |_| |  __/| |__| |_| |   | |_| / __/ _| ||  __/
 FOR PEACE|____/|_|   |_____\___/    |____/_____|____|_|
"""

LOGO_LARGE = r"""
        .oO0Oo.
      .o0      0o.      ATOMIC METROLOGY DIVISION
     .o0        0o.
    .o0   ( )    0o.   ██████╗ ███████╗██╗     ██╗   ██╗    ███████╗██████╗ ██████╗ ██╗
    .o0 ( ) ( )  0o.   ██╔══██╗██╔════╝██║     ██║   ██║    ╚══███╔╝██╔══██╗██╔══██╗██║
    .o0   ( )    0o.   ██║  ██║███████╗██║     ██║   ██║      ███╔╝ ██████╔╝██║  ██║██║
     .o0        0o.    ██║  ██║╚════██║██║     ╚██╗ ██╔╝     ███╔╝  ██╔═══╝ ██║  ██║██║
      .o0      0o.     ██████╔╝███████║███████╗ ╚████╔╝     ███████╗██║     ██████╔╝███████╗
        .oO0Oo.        ╚═════╝ ╚══════╝╚══════╝  ╚═══╝      ╚══════╝╚═╝     ╚═════╝ ╚══════╝
"""

# ── Snarky boot messages ─────────────────────────────────────────────────────

BOOT_MESSAGES = [
    "WARMING UP THE VACUUM TUBES...",
    "CALIBRATING THE CATHODE RAY TUBE...",
    "INSERTING PUNCH CARDS FOR BOOT SEQUENCE...",
    "ALIGNING THE ATOMIC PILE...",
    "STAND CLEAR OF THE RADIATION SHIELD...",
    "ISOTOPE CENTRIFUGE SPINNING AT NOMINAL RPS",
    "RUTHERFORD ATOM SMASHER ONLINE...",
    "COMMENCING OPERATION CROSSROADS...",
    "PLASMOID DETECTOR ////LOADING////... ... ...",
    "REDLINE THE SPINE",
    "NOT LOS ALAMOS METROLOGY... ////SORRY///",
    "BOOTING OBSERVATIONAL AWARENESS",
    "DON'T MEASURE TOO CLOSELY NOW",
    "PUT YOUR RODNEY-PIPER-BATMANS ON",
    "GAMMA DRIVES R, BUT THEY DON'T WANNA SEE",
    "COHERENCE IS THE CURRENCY, THE THRESHOLD IS THE GATE",
    "RECURSIVE OBSERVATION FORCING SYSTEMIC FATE",
    "CALIBRATING THE UNCALIBRABLE",
    "SPINNING UP THE COHERENCE CANNON",
    "IF IT MOVES, IT GETS COHERENCE-SCORED",
    "SYNCHRONIZING CHAOS TO A PULSE PER SECOND",
    "HOLD MY PHASE-LOCKED LOOP",
    "THE RODNEY-PIPER-BATMANS ARE WARMING UP",
    "METROLOGY FIRST, APOLOGIES LATER",
]

# ── Startup stages ───────────────────────────────────────────────────────────

STAGES = [
    ("TUNING", "dslv-zpdi-tuning.service", True, "Performance governor & USB power"),
    ("PREFLIGHT", "dslv-zpdi-preflight.service", True, "Hardware sanity checks"),
    ("TIMING", "chrony.service", False, "PPS discipline & Stratum 1"),
    ("GPSDO", "gpsd.service", False, "LBE-1421 NMEA feed"),
    ("SDR", "dslv-zpdi.service", True, "PlutoSDR+ pipeline backend"),
    ("UPS", "dslv-zpdi-ups.service", True, "X-1202 power telemetry"),
    ("WEBDASH", "dslv-zpdi-webdash.service", True, "Flask dashboard on :8080"),
    ("TIER1", "dslv-zpdi-tier1.service", True, "Tier-1 WSS server on :8443"),
]

# ── Helpers ──────────────────────────────────────────────────────────────────


def is_active(unit: str) -> bool:
    """Return True if a systemd unit is active."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", unit],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        return result.stdout.strip() == "active"
    except Exception:
        return False


def start_unit(unit: str) -> bool:
    """Start a systemd unit and wait for it to become active."""
    try:
        subprocess.run(
            ["sudo", "systemctl", "start", unit],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        for _ in range(20):
            if is_active(unit):
                return True
            time.sleep(0.5)
        return False
    except Exception:
        return False


def get_terminal_size() -> tuple[int, int]:
    try:
        return shutil.get_terminal_size()
    except Exception:
        return 80, 24


def build_banner() -> Panel:
    """Build the retro header banner."""
    cols, _ = get_terminal_size()
    art = LOGO_LARGE if cols >= 80 else LOGO_SMALL
    content = Text(art, style="bold bright_cyan", no_wrap=True)
    return Panel(
        Align.center(content),
        border_style="bright_green",
        title="[bold bright_yellow]DSLV-ZPDI v5.0.0 — TIER-1 ANCHOR[/]",
        subtitle="[dim]DynoGatorLabs RF Metrology Node[/]",
    )


def build_stage_table(
    completed: list[str],
    current: str | None,
    upcoming: list[str],
    statuses: dict[str, str],
) -> Panel:
    """Render the sequential stage list."""
    text = Text()
    for name, unit, managed, desc in STAGES:
        if name in completed:
            text.append(f"[OK]    {name:10} ", style="bold bright_green")
            text.append(f"{desc}\n", style="dim")
        elif name == current:
            text.append(f"[...]   {name:10} ", style="bold bright_yellow")
            text.append(f"{desc}\n", style="bright_white")
        else:
            text.append(f"[WAIT]  {name:10} ", style="dim")
            text.append(f"{desc}\n", style="dim")
        if name in statuses:
            text.append(f"        └─ {statuses[name]}\n", style="italic dim")
    return Panel(text, title="[bold]BOOT SEQUENCE[/]", border_style="bright_blue")


def build_message(message: str, tick: int) -> Panel:
    """Render the snarky rotating status message with retro flair."""
    spinner = ["\\", "|", "/", "-"][tick % 4]
    styled = Text()
    styled.append(">> ", style="bold bright_magenta")
    styled.append(message, style="bold bright_cyan")
    styled.append(f" {spinner}", style="bold bright_yellow")
    return Panel(
        Align.center(styled),
        border_style="bright_magenta",
        title="[bold]SYSTEM DRONE[/]",
    )


def build_footer(stage: str | None, ok: bool) -> Panel:
    """Render the bottom status bar."""
    status = "ALL SYSTEMS NOMINAL" if ok else "DEGRADED — CHECK LOGS"
    color = "bright_green" if ok else "bright_red"
    text = Text()
    text.append(f"STAGE: {stage or 'IDLE':12} ", style="dim")
    text.append(f"STATUS: {status}", style=f"bold {color}")
    return Panel(text, border_style=color)


# ── Boot loop ────────────────────────────────────────────────────────────────


def run_boot_sequence(
    start_services: bool = True,
    launch_dashboard: bool = True,
) -> bool:
    """Run the animated boot sequence and return success state."""
    completed: list[str] = []
    statuses: dict[str, str] = {}
    current: str | None = None
    message_idx = 0

    layout = Layout()
    layout.split_column(
        Layout(name="banner", size=10),
        Layout(name="stages"),
        Layout(name="message", size=5),
        Layout(name="footer", size=3),
    )

    def render(tick: int) -> None:
        ok = all(s[0] in completed for s in STAGES if s[2])
        layout["banner"].update(build_banner())
        layout["stages"].update(build_stage_table(completed, current, [], statuses))
        msg = BOOT_MESSAGES[(message_idx + tick) % len(BOOT_MESSAGES)]
        layout["message"].update(build_message(msg, tick))
        layout["footer"].update(build_footer(current, ok))

    with Live(layout, console=console, screen=True, refresh_per_second=12):
        for tick in range(60):
            render(tick)
            time.sleep(0.08)

        for name, unit, managed, desc in STAGES:
            current = name
            statuses[name] = "checking..."
            for tick in range(30):
                render(tick)
                time.sleep(0.05)

            if is_active(unit):
                statuses[name] = f"{unit} already active"
                completed.append(name)
                continue

            if not managed:
                statuses[name] = f"{unit} not managed — verify manually"
                completed.append(name)  # optional service
                continue

            if start_services:
                statuses[name] = f"starting {unit}..."
                for tick in range(20):
                    render(tick + 30)
                    time.sleep(0.05)
                if start_unit(unit):
                    statuses[name] = f"{unit} started"
                    completed.append(name)
                else:
                    statuses[name] = f"FAILED to start {unit}"
                    render(0)
                    time.sleep(2)
                    return False
            else:
                statuses[name] = f"{unit} inactive (start skipped)"
                completed.append(name)

            time.sleep(0.3)

        current = "READY"
        statuses["READY"] = "Boot sequence complete"
        for tick in range(40):
            render(tick)
            time.sleep(0.05)

    return True


def launch_dashboard(compact: bool = False) -> None:
    """Exec the Rich TUI dashboard in wide/10-inch or compact mode."""
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tools = os.path.join(repo, "tools")
    python = os.path.join(repo, ".venv", "bin", "python")
    args = [python, "-m", "dashboard"]
    if compact:
        args.append("--compact")
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["LANG"] = os.environ.get("LANG", "en_US.UTF-8")
    os.environ["LC_ALL"] = os.environ.get("LC_ALL", "en_US.UTF-8")
    os.chdir(tools)
    os.execvp(python, args)


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="DSLV-ZPDI retro boot orchestrator")
    parser.add_argument(
        "--no-start", action="store_true", help="verify only; do not start services"
    )
    parser.add_argument(
        "--no-dashboard", action="store_true", help="skip launching the TUI dashboard"
    )
    parser.add_argument("--compact", action="store_true", help="force compact dashboard layout")
    args = parser.parse_args()

    if os.geteuid() == 0:
        console.print("[bold red]Do not run the boot orchestrator as root.[/]")
        return 1

    ok = run_boot_sequence(
        start_services=not args.no_start,
        launch_dashboard=not args.no_dashboard,
    )

    if not ok:
        console.print("\n[bold red]BOOT FAILED — check journalctl -u dslv-zpdi[/]")
        return 1

    if not args.no_dashboard:
        launch_dashboard(compact=args.compact)

    console.print("\n[bold green]DSLV-ZPDI READY[/]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
