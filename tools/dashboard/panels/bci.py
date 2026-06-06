"""SPEC-021.3 — Barometric Coherence Index (BCI) panel."""

import time
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class BCIPanel:
    """Current χ, pilot-threshold state, review-flag status."""

    def __init__(self, border_style: str = "bright_magenta"):
        self.border_style = border_style
        self._last_result: dict = {}
        self._last_ts: float = 0.0

    def update(self, result: dict):
        self._last_result = result
        self._last_ts = time.time()

    def render(self, compact: bool = False):
        r = self._last_result
        if not r:
            content = Text("BCI IDLE — DARCY'S LAW IS PUMPING", style="dim italic")
            return Panel(content, title="[BCI]", border_style=self.border_style)

        chi = r.get("chi", 0.0)
        threshold = r.get("pilot_threshold", 0.65)
        review = r.get("review_flag", False)

        chi_style = (
            "bold bright_red" if review else
            "bold bright_yellow" if chi >= threshold * 0.8 else
            "bold bright_green"
        )

        if compact:
            line = Text()
            line.append(f"χ={chi:.2f} ", style=chi_style)
            line.append(f"thr={threshold:.2f}", style="dim")
            if review:
                line.append(" REVIEW", style="bold bright_red")
            return Panel(line, title="[BCI]", border_style=self.border_style)

        table = Table(show_header=False, box=None, padding=0)
        table.add_column("key", style="dim", justify="right")
        table.add_column("val", style="bright_white")
        table.add_row("χ (BCI)", f"[{chi_style}]{chi:.3f}")
        table.add_row("Threshold", f"{threshold:.2f} (pilot)")
        table.add_row("Review", "[bold bright_red]FLAGGED" if review else "[bright_green]CLEAR")
        table.add_row("N", str(r.get("n_samples", 0)))
        reason = r.get("review_reason", "")
        if reason:
            table.add_row("Note", reason, style="bright_yellow")

        return Panel(table, title="[BCI]", border_style=self.border_style)
