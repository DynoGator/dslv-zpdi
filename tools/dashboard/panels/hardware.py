"""Hardware status panel: PlutoSDR+/SDR, PPS, GPSDO, chrony, UPS.

Expensive probes (iio_info, hackrf_info, chronyc) are cached for a few seconds so
they don't dominate the dashboard refresh loop. When the pipeline's health.json is
available, the panel reads live telemetry from there first and falls back to
direct probes only when needed.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path

from rich.markup import escape as _esc
from rich.panel import Panel
from rich.table import Table

_HACKRF_TTL = 3.0   # seconds
_CHRONY_TTL = 1.5   # seconds
_GPSDO_TTL = 5.0    # seconds
_HEALTH_JSON_PATHS = (Path("/run/dslv-zpdi/health.json"), Path("/tmp/health.json"))


class _Cache:
    def __init__(self, ttl: float):
        self.ttl = ttl
        self.t = 0.0
        self.val = None

    def get(self, producer):
        now = time.time()
        if self.val is None or now - self.t > self.ttl:
            self.val = producer()
            self.t = now
        return self.val


def _read_health_json() -> dict:
    """Read the pipeline health endpoint if available."""
    for path in _HEALTH_JSON_PATHS:
        try:
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
    return {}


def _hackrf_info() -> dict:
    try:
        out = subprocess.check_output(
            ["hackrf_info"], text=True, timeout=3, stderr=subprocess.STDOUT
        )
        serial = re.search(r"Serial number:\s+(\S+)", out)
        fw = re.search(r"Firmware Version:\s+(\S+)", out)
        rev = re.search(r"Hardware Revision:\s+(\S+)", out)
        board = re.search(r"Board ID Number:\s+\d+\s+\((.+)\)", out)
        return {
            "detected": "Found HackRF" in out,
            "serial": serial.group(1) if serial else "?",
            "fw": fw.group(1) if fw else "?",
            "rev": rev.group(1) if rev else "?",
            "board": board.group(1) if board else "HackRF",
            "source": "hackrf",
        }
    except Exception:
        return {"detected": False, "serial": "-", "fw": "-", "rev": "-", "board": "-", "source": "hackrf"}


def _pluto_info() -> dict:
    """Probe PlutoSDR+ via libiio (non-fatal)."""
    uri = os.environ.get("DSLV_SDR_URI", "ip:192.168.2.1")
    try:
        import iio  # pylint: disable=import-outside-toplevel

        ctx = iio.Context(uri)
        ad9361 = ctx.find_device("ad9361-phy")
        if ad9361 is None:
            return {"detected": False, "serial": "-", "fw": "-", "rev": "-", "board": "-", "source": "pluto"}
        board = ctx.attrs.get("hw_model", "PlutoSDR+")
        fw = ctx.attrs.get("fw_version", "?")
        serial = ctx.attrs.get("hw_serial", "?")
        return {
            "detected": True,
            "serial": serial,
            "fw": fw,
            "rev": "?",
            "board": board,
            "source": "pluto",
        }
    except Exception:
        return {"detected": False, "serial": "-", "fw": "-", "rev": "-", "board": "-", "source": "pluto"}


def _sdr_info() -> dict:
    """Return the first detected Tier-1/legacy SDR, preferring Pluto."""
    pluto = _pluto_info()
    if pluto["detected"]:
        return pluto
    hackrf = _hackrf_info()
    if hackrf["detected"]:
        return hackrf
    return pluto


def _pps_device() -> bool:
    return os.path.exists("/dev/pps0")


def _pps_module_loaded() -> bool:
    try:
        with open("/proc/modules", encoding="utf-8") as f:
            return "pps_gpio" in f.read()
    except Exception:
        return False


def _chrony_stats() -> dict:
    try:
        out = subprocess.check_output(
            ["chronyc", "tracking"], text=True, timeout=2
        )
        rms = re.search(r"RMS offset\s+:\s+([-+.\d]+)\s+(\w+)", out)
        stratum = re.search(r"Stratum\s+:\s+(\d+)", out)
        leap = re.search(r"Leap status\s+:\s+(.+)", out)
        src = re.search(r"Reference ID\s+:\s+(\S+)", out)
        if rms:
            val = float(rms.group(1))
            unit = rms.group(2)
            factor = {"ns": 1, "us": 1e3, "ms": 1e6, "s": 1e9}.get(unit, 1e9)
            rms_ns = abs(val) * factor
        else:
            rms_ns = float("nan")
        return {
            "stratum": stratum.group(1) if stratum else "?",
            "leap": (leap.group(1).strip() if leap else "?"),
            "ref": (src.group(1) if src else "?"),
            "rms_ns": rms_ns,
        }
    except Exception:
        return {"stratum": "?", "leap": "?", "ref": "?", "rms_ns": float("nan")}


def _format_ns(val: float) -> str:
    """Format a nanosecond value for human consumption."""
    if val != val:  # NaN
        return "--"
    if val < 1_000:
        return f"{val:.0f}ns"
    if val < 1_000_000:
        return f"{val/1000:.1f}µs"
    return f"{val/1_000_000:.1f}ms"


class HardwarePanel:
    def __init__(self, border_style: str = "yellow"):
        self.border_style = border_style
        self._sdr = _Cache(_HACKRF_TTL)
        self._chrony = _Cache(_CHRONY_TTL)
        self._health = _Cache(1.0)

    def render(self, compact: bool = False) -> Panel:
        health = self._health.get(_read_health_json)
        sdr = self._sdr.get(_sdr_info)
        pps_dev = _pps_device()
        pps_mod = _pps_module_loaded()
        chr_ = self._chrony.get(_chrony_stats)

        # Prefer pipeline health.json for live telemetry.
        sdr_health = health.get("sdr_health", {})
        ups = health.get("ups", {})
        pps = health.get("pps", {})
        timing = health.get("timing_healthy", False)

        # SDR status: use direct probe for metadata, health.json for reachability.
        sdr_detected = sdr_health.get("reachable", sdr["detected"])
        sdr_style = "bright_green" if sdr_detected else "bright_red"
        sdr_glyph = "◉" if sdr_detected else "○"
        sdr_board = sdr.get("board", "PlutoSDR+")
        sdr_fw = sdr.get("fw", "?")
        sdr_serial = sdr.get("serial", "?")

        # PPS status from health.json when available.
        pps_history = pps.get("history_len", 0)
        pps_jitter = pps.get("rms_jitter_ns", float("nan"))
        pps_ok = pps_dev and pps_mod and pps_history >= 2

        # Chrony / timing.
        rms = chr_["rms_ns"]
        if timing and pps_history >= 2:
            # Override with the live PPS jitter if health.json has it.
            rms = pps_jitter if pps_jitter == pps_jitter else rms
        rms_txt = _format_ns(rms)

        # GPSDO / NMEA fix from health.json (pipeline reads it via gpsd).
        nmea = health.get("nmea_fix", {})
        if not nmea:
            # Try to derive from timing evidence if present.
            evidence = health.get("evidence", {})
            nmea = evidence.get("nmea_fix", {})
        fix = nmea.get("fix_quality", 0)
        fix_map = {0: "None", 1: "GPS", 2: "DGPS", 4: "RTK", 5: "Float"}
        fix_txt = fix_map.get(fix, str(fix)) if fix else "acq…"
        sats = nmea.get("satellites_used", "?")

        t = Table.grid(padding=(0, 1 if compact else 2), expand=True)
        t.add_column(style="bright_cyan", justify="right")
        t.add_column()

        if compact:
            clk = "EXT" if sdr_health.get("external_reference_configured") else "INT"
            t.add_row("SDR", f"[{sdr_style}]{sdr_glyph}[/] {clk} [dim]•[/] PPS[{'G' if pps_ok else 'R'}]")
            t.add_row("Gps", f"[bright_green]◉[/] fix={fix_txt} sats={sats}")
            t.add_row("Chr", f"str={chr_['stratum']} [magenta]rms={rms_txt}[/]")
            if ups:
                ups_health = ups.get("health", "absent")
                ups_ok = ups_health == "healthy"
                ups_style = "bright_green" if ups_ok else "bright_red" if ups_health == "critical" else "bright_yellow"
                t.add_row("UPS", f"[{ups_style}]{'◉' if ups_ok else '○'}[/] {ups.get('battery_percent', '?')}% AC={'Y' if ups.get('ac_present') else 'N'}")
        else:
            source_label = "Pluto" if sdr.get("source") == "pluto" else "SDR"
            t.add_row(
                source_label,
                f"[{sdr_style}]{sdr_glyph} {_esc(sdr_board)} "
                f"fw={_esc(sdr_fw)}[/]",
            )
            t.add_row("S/N", f"[dim]{_esc(str(sdr_serial)[-12:])}[/]")

            pps_style = "bright_green" if pps_ok else "yellow"
            pps_text = "/dev/pps0"
            if pps_dev and not pps_mod:
                pps_text += " (pps_gpio not loaded)"
            elif not pps_dev:
                pps_text = "absent"
            jitter_line = f" jitter={rms_txt}" if pps_history >= 2 else ""
            t.add_row(
                "PPS GPIO",
                f"[{pps_style}]{'◉' if pps_ok else '○'} {pps_text}{jitter_line}[/]",
            )

            t.add_row(
                "GPSDO",
                f"[bright_green]◉[/] fix={fix_txt}  sats={sats}",
            )

            rms_styled = (
                f"[bright_green]{rms_txt}[/]" if (isinstance(rms, float) and rms < 1000)
                else f"[yellow]{rms_txt}[/]" if (isinstance(rms, float) and rms < 1000000)
                else f"[bright_red]{rms_txt}[/]"
            )
            if rms != rms:
                rms_styled = "[dim]--[/]"

            t.add_row(
                "Chrony",
                f"stratum {_esc(chr_['stratum'])}  "
                f"ref {_esc(chr_['ref'])}  rms {rms_styled}",
            )
            t.add_row("Leap", f"[dim]{_esc(chr_['leap'])}[/]")

            if ups:
                ups_health = ups.get("health", "absent")
                ups_ok = ups_health == "healthy"
                ups_style = "bright_green" if ups_ok else "bright_red" if ups_health == "critical" else "bright_yellow"
                ac = "YES" if ups.get("ac_present") is True else "NO" if ups.get("ac_present") is False else "?"
                charge = ups.get("charge_rate_percent_per_hour", 0.0)
                charge_dir = "▲" if charge > 0 else "▼" if charge < 0 else "─"
                t.add_row(
                    "UPS",
                    f"[{ups_style}]{'◉' if ups_ok else '○'}[/] "
                    f"{ups.get('battery_percent', '?')}%  "
                    f"{ups.get('battery_voltage_v', '?')}V  "
                    f"AC={ac}  {charge_dir}{abs(charge):.2f}%/h",
                )

        title = f"[bold {self.border_style}]▓ HW ▓[/]" if compact else f"[bold {self.border_style}]▓ HARDWARE ▓[/]"
        return Panel(
            t,
            title=title,
            border_style=self.border_style,
            padding=(0, 1),
        )
