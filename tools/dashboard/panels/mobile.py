"""SPEC-021.2 — Pixel 9 Pro XL Tier 2 mobile node panel."""

import time
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class MobilePanel:
    """Pixel link status, magnetometer magnitude, GPS fix, camera hash tail, uplink."""

    def __init__(self, border_style: str = "bright_blue"):
        self.border_style = border_style
        self._last_telem: dict = {}
        self._last_ts: float = 0.0

    def update(self, telem: dict):
        self._last_telem = telem
        self._last_ts = time.time()

    def render(self, compact: bool = False):
        t = self._last_telem
        if not t:
            content = Text("NO DATA — PIXEL OFF GRID", style="dim italic")
            return Panel(content, title="[MOBILE/T2]", border_style=self.border_style)

        age_s = time.time() - t.get("timestamp_utc", 0)
        age_str = f"{age_s:.0f}s" if age_s < 120 else f"{age_s/60:.0f}m"

        mag = t.get("magnetometer_ut")
        mag_str = f"{sum(v*v for v in mag)**0.5:.1f} µT" if mag else "—"

        gps = t.get("gps", {})
        fix = gps.get("accuracy")
        fix_style = "bright_green" if fix and fix <= 10 else "bright_yellow" if fix and fix <= 50 else "bright_red"
        fix_str = f"{fix:.1f}m" if fix else "NO FIX"

        cam = t.get("camera_frame_hash", "")
        cam_str = cam[-6:] if cam else "—"

        trust = t.get("trust_score", 0.0)
        trust_style = "bright_green" if trust >= 0.7 else "bright_yellow" if trust >= 0.5 else "bright_red"

        if compact:
            line = Text()
            line.append(f"MAG:{mag_str} ", style="bright_cyan")
            line.append(f"GPS:{fix_str} ", style=fix_style)
            line.append(f"T:{trust:.2f}", style=trust_style)
            return Panel(line, title="[MOBILE/T2]", border_style=self.border_style)

        table = Table(show_header=False, box=None, padding=0)
        table.add_column("key", style="dim", justify="right")
        table.add_column("val", style="bright_white")
        table.add_row("Mag", mag_str, style="bright_cyan")
        table.add_row("GPS fix", f"[{fix_style}]{fix_str}")
        table.add_row("Cam hash", cam_str)
        table.add_row("Trust", f"[{trust_style}]{trust:.2f}")
        table.add_row("Age", age_str)
        flags = t.get("trust_flags", [])
        if flags:
            table.add_row("Flags", ", ".join(flags), style="bright_yellow")

        return Panel(table, title="[MOBILE/T2]", border_style=self.border_style)
