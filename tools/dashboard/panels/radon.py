"""SPEC-021.1 — RadonEye Pro live telemetry panel."""

import time
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class RadonPanel:
    """Live pCi/L, transport, serial tail, sample age, and quality."""

    def __init__(self, border_style: str = "bright_green"):
        self.border_style = border_style
        self._last_sample: dict = {}
        self._last_ts: float = 0.0

    def update(self, sample: dict):
        self._last_sample = sample
        self._last_ts = time.time()

    def render(self, compact: bool = False):
        s = self._last_sample
        if not s:
            content = Text("NO DATA — SNIFFING NOBLE GASES...", style="dim italic")
            return Panel(content, title="[RADON]", border_style=self.border_style)

        age_s = time.time() - s.get("timestamp_utc", 0)
        age_str = f"{age_s:.0f}s" if age_s < 120 else f"{age_s/60:.0f}m"

        transport = s.get("transport", "?").upper()
        transport_style = {
            "BLE": "bold bright_cyan",
            "HTTP": "bold bright_yellow",
            "SIM": "dim",
        }.get(transport, "bright_white")

        quality = s.get("sample_quality", "?")
        quality_style = "bright_green" if quality == "good" else "bright_yellow" if quality == "suspect" else "bright_red"

        if compact:
            line = Text()
            line.append(f"{s.get('radon_pCiL', 0):.2f} pCi/L ", style="bold bright_green")
            line.append(f"({transport}) ", style=transport_style)
            line.append(f"age:{age_str}", style="dim")
            return Panel(line, title="[RADON]", border_style=self.border_style)

        table = Table(show_header=False, box=None, padding=0)
        table.add_column("key", style="dim", justify="right")
        table.add_column("val", style="bright_white")
        table.add_row("pCi/L", f"[bold bright_green]{s.get('radon_pCiL', 0):.2f}")
        table.add_row("Bq/m³", f"{s.get('radon_Bqm3', 0):.1f}")
        table.add_row("Transport", f"[{transport_style}]{transport}")
        table.add_row("Serial", s.get("device_serial", "?")[-8:] or "?")
        table.add_row("Quality", f"[{quality_style}]{quality}")
        table.add_row("Age", age_str)

        return Panel(table, title="[RADON]", border_style=self.border_style)
