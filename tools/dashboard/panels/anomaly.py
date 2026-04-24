"""RF anomaly / signal-strength panel.

Reads live spectrum metrics from the WaterfallPanel's last raw dBm row:
peak power (dBm), peak frequency, noise floor, SNR, and number of bins
exceeding noise floor + 10 dB. Tracks running peak-of-peaks across the
session so operators can see the strongest anomaly observed.
"""

from __future__ import annotations

import math
import time

from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def _fmt_freq(hz: float) -> str:
    if math.isnan(hz):
        return "—"
    if hz >= 1e9:
        return f"{hz / 1e9:7.4f} GHz"
    if hz >= 1e6:
        return f"{hz / 1e6:7.3f} MHz"
    if hz >= 1e3:
        return f"{hz / 1e3:7.2f} kHz"
    return f"{hz:7.0f}  Hz"


def _dbm_style(dbm: float) -> str:
    if math.isnan(dbm):
        return "dim"
    if dbm >= -30:
        return "bright_red"
    if dbm >= -50:
        return "bright_yellow"
    if dbm >= -70:
        return "yellow"
    return "bright_green"


def _snr_style(snr: float) -> str:
    if math.isnan(snr):
        return "dim"
    if snr >= 30:
        return "bright_red"
    if snr >= 20:
        return "bright_yellow"
    if snr >= 10:
        return "yellow"
    return "bright_green"


class RFAnomalyPanel:
    """Live RF metrics. Pass the WaterfallPanel instance — we read its last row."""

    def __init__(self, waterfall, border_style: str = "bright_yellow"):
        self.waterfall = waterfall
        self.border_style = border_style
        self.session_peak_dbm = float("-inf")
        self.session_peak_freq_hz = float("nan")
        self.session_peak_at = 0.0
        self.last_anomaly_at = 0.0

    def render(self) -> Panel:
        m = self.waterfall.metrics()
        peak = m["peak_dbm"]
        floor = m["noise_floor_dbm"]
        snr = m["snr_db"]
        freq = m["peak_freq_hz"]
        anomalies = m["anomaly_count"]
        source = m["source"]

        # Update session peak
        if m["have_data"] and not math.isnan(peak) and peak > self.session_peak_dbm:
            self.session_peak_dbm = peak
            self.session_peak_freq_hz = freq
            self.session_peak_at = time.time()
        if anomalies > 0:
            self.last_anomaly_at = time.time()

        t = Table.grid(padding=(0, 2), expand=True)
        t.add_column(style="bright_cyan", justify="right", no_wrap=True)
        t.add_column(no_wrap=True)

        if not m["have_data"]:
            t.add_row("Status", Text("waiting for spectrum data…", style="dim italic"))
            return Panel(
                t,
                title=f"[bold {self.border_style}]▓ RF ANOMALY ▓[/]",
                border_style=self.border_style,
                padding=(0, 1),
            )

        # Peak now
        peak_line = Text()
        peak_line.append(f"{peak:6.1f} dBm", style="bold " + _dbm_style(peak))
        peak_line.append("  @ ", style="dim")
        peak_line.append(_fmt_freq(freq), style="bright_white")
        t.add_row("Peak", peak_line)

        # Noise floor
        floor_line = Text(f"{floor:6.1f} dBm", style="bright_white")
        t.add_row("Noise", floor_line)

        # SNR
        snr_line = Text(f"{snr:5.1f} dB", style="bold " + _snr_style(snr))
        t.add_row("SNR", snr_line)

        # Anomaly count (this sweep)
        anom_line = Text()
        anom_sty = "bright_red" if anomalies >= 5 else "bright_yellow" if anomalies >= 1 else "bright_green"
        anom_line.append(f"{anomalies}", style=f"bold {anom_sty}")
        anom_line.append(" bins > floor+10dB", style="dim")
        t.add_row("Anomalies", anom_line)

        # Session peak
        if self.session_peak_dbm > float("-inf"):
            age = int(time.time() - self.session_peak_at)
            sess = Text()
            sess.append(f"{self.session_peak_dbm:6.1f} dBm", style="bold " + _dbm_style(self.session_peak_dbm))
            sess.append(f"  @ ", style="dim")
            sess.append(_fmt_freq(self.session_peak_freq_hz), style="bright_white")
            sess.append(f"  ({age}s ago)", style="dim")
            t.add_row("Sess. Peak", sess)

        # Source + sweeps
        src_line = Text()
        src_sty = "bright_green" if source == "HACKRF" else "yellow" if source == "HACKRF-WAIT" else "magenta"
        src_glyph = "◉" if source == "HACKRF" else "◌"
        src_line.append(f"{src_glyph} {source}", style=src_sty)
        if m["sweeps"]:
            src_line.append(f"  · {m['sweeps']} sweeps", style="dim")
        t.add_row("Source", src_line)

        # Last anomaly age
        if self.last_anomaly_at > 0:
            age = int(time.time() - self.last_anomaly_at)
            last_line = Text(f"{age}s ago" if age > 0 else "live now",
                             style="bright_yellow" if age < 5 else "dim")
        else:
            last_line = Text("none observed", style="dim")
        t.add_row("Last hit", last_line)

        return Panel(
            t,
            title=f"[bold {self.border_style}]▓ RF ANOMALY ▓[/]",
            border_style=self.border_style,
            padding=(0, 1),
        )
