"""Settings / keybindings reference panel.

Lists the current SDR and dashboard settings alongside the active keyboard
shortcuts so a user at the terminal (especially on a 10" touchscreen) can see
what the dashboard is doing without memorising the help banner.
"""

from __future__ import annotations

import os

from rich.markup import escape as _esc
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class SettingsPanel:
    """Live settings and keybindings panel."""

    def __init__(self, border_style: str = "bright_blue") -> None:
        self.border_style = border_style

    def render(self, compact: bool = False, state: dict | None = None) -> Panel:
        s = state or {}
        uri = os.environ.get("DSLV_SDR_URI", "auto")
        real_sdr = s.get("real_sdr", False)
        source = s.get("sdr_source", "SIM")
        center_hz = s.get("center_hz", 100_000_000)
        span_hz = s.get("span_hz", 20_000_000)
        lna_gain = s.get("lna_gain", 24)
        vga_gain = s.get("vga_gain", 20)
        mode = s.get("wf_mode", "SWEEP")
        palette = s.get("palette_name", "HEAT")
        modulation = s.get("modulation", "RAW-SWEEP")
        floor_db = s.get("dbm_floor", -90.0)
        ceil_db = s.get("dbm_ceil", -20.0)
        refresh = s.get("refresh", 0.5)
        paused = s.get("paused", False)
        compact_state = s.get("compact", False)
        banner = s.get("banner", True)

        t = Table.grid(padding=(0, 1 if compact else 2), expand=True)
        t.add_column(style="bright_cyan", justify="right")
        t.add_column()

        src_style = "bright_green" if real_sdr else "bright_yellow"
        src_label = source if real_sdr else "SIM"
        t.add_row("SDR", f"[{src_style}]{src_label}[/]  uri={_esc(uri)}")
        t.add_row("Freq", f"{center_hz / 1e6:.3f} MHz  span {span_hz / 1e6:.1f} MHz")
        t.add_row("Gain", f"LNA {lna_gain}dB  VGA {vga_gain}dB")
        t.add_row("Mode", f"{mode} · {modulation} · {palette}")
        t.add_row("Range", f"floor {floor_db:.0f}  ceil {ceil_db:.0f}")
        t.add_row("UI", f"refresh {refresh}s  {'paused' if paused else 'live'}  compact={'on' if compact_state else 'off'}  banner={'on' if banner else 'off'}")

        keys = Text()
        groups = [
            ("SDR", [("r", "real/SIM"), ("g", "gain"), ("a", "amp lockout")]),
            ("Tune", [("</>", "coarse"), (",/.", "fine"), ("z/x", "zoom")]),
            ("View", [("m", "mode"), ("p", "palette"), ("s", "spectrum"), ("c", "compact"), ("h", "banner")]),
            ("Control", [("space", "pause"), ("q", "quit")]),
        ]
        for group_name, bindings in groups:
            keys.append(f"{group_name}:", style="dim")
            for k, desc in bindings:
                keys.append(" [", style="dim")
                keys.append(k, style="bold bright_yellow")
                keys.append("]", style="dim")
                keys.append(f"{desc}", style="bright_white")
            keys.append("  ", style="dim")

        content = Table.grid(expand=True)
        content.add_row(t)
        content.add_row(keys)

        title = f"[bold {self.border_style}]▓ SETTINGS ▓[/]" if not compact else f"[bold {self.border_style}]▓ SET ▓[/]"
        return Panel(content, title=title, border_style=self.border_style, padding=(0, 1))
