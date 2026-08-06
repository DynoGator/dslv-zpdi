"""Demodulation and MIMO module panel for the DSLV-ZPDI dashboard.
Provides UI for selecting and managing signal demodulation profiles (ADS-B, Audio, Video)
as well as MIMO RX/TX toggling.
"""

from __future__ import annotations

from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class DemodPanel:
    def __init__(self, border_style: str = "bright_red"):
        self.border_style = border_style
        # Default state
        self.profiles = [
            ("1", "ADS-B", "Data / 1090 MHz"),
            ("2", "FM Radio", "Audio / 88-108 MHz"),
            ("3", "AM Radio", "Audio / 530-1700 kHz"),
            ("4", "EMS/Fire", "Audio / NFM P25"),
            ("5", "Broadcast TV", "Video / ATSC"),
        ]

    def render(self, compact: bool = False, state: dict | None = None) -> Panel:
        s = state or {}
        active_profile = s.get("demod_profile", "None")
        demod_active = s.get("demod_active", False)
        tx_enabled = s.get("mimo_tx", False)

        t = Table.grid(padding=(0, 1 if compact else 2), expand=True)
        t.add_column(style="bright_cyan", justify="right")
        t.add_column()

        status_style = "bold bright_green" if demod_active else "bold bright_black"
        status_text = "ACTIVE" if demod_active else "INACTIVE"
        t.add_row("Status", f"[{status_style}]{status_text}[/] | Profile: [bright_white]{active_profile}[/]")

        mimo_style = "bold bright_red" if tx_enabled else "bold bright_green"
        mimo_text = "TX/RX ENABLED (WARNING: RESTRICTED)" if tx_enabled else "LISTEN ONLY (RX)"
        t.add_row("MIMO Mode", f"[{mimo_style}]{mimo_text}[/]")

        # Spacer
        t.add_row("", "")

        if not compact:
            keys = Text()
            keys.append("PROFILES:\n", style="bold bright_white")
            for key, name, desc in self.profiles:
                keys.append(f"[{key}] ", style="bold bright_yellow")
                keys.append(f"{name:<15}", style="bright_cyan")
                keys.append(f"{desc}\n", style="dim")

            keys.append("\nCONTROLS:\n", style="bold bright_white")
            keys.append("[Enter] ", style="bold bright_yellow")
            keys.append("Start/Stop Demod   ", style="bright_white")
            keys.append("[T] ", style="bold bright_yellow")
            keys.append("Toggle MIMO TX\n", style="bright_white")
            keys.append("[f] ", style="bold bright_yellow")
            keys.append("Freq Input (Numeric)", style="bright_white")

            content = Table.grid(expand=True)
            content.add_row(t)
            content.add_row(keys)
        else:
            content = t

        title = f"[bold {self.border_style}]▓ DEMODULATION & MIMO ▓[/]"
        return Panel(content, title=title, border_style=self.border_style, padding=(0, 1))
