"""Hardware status panel: HackRF, PPS, GPSDO, chrony.

Expensive probes (hackrf_info, chronyc) are cached for a few seconds so
they don't dominate the dashboard refresh loop.
"""

import os
import re
import subprocess
import time

from rich.markup import escape as _esc
from rich.panel import Panel
from rich.table import Table


_HACKRF_TTL = 3.0   # seconds
_CHRONY_TTL = 1.5   # seconds


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
        }
    except Exception:
        return {"detected": False, "serial": "-", "fw": "-", "rev": "-", "board": "-"}


def _pps_device() -> bool:
    return os.path.exists("/dev/pps0")


def _pps_module_loaded() -> bool:
    try:
        with open("/proc/modules", "r", encoding="utf-8") as f:
            return "pps_gpio" in f.read()
    except Exception:
        return False


def _gpsdo_serial() -> str | None:
    for p in ("/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0", "/dev/ttyUSB1"):
        if os.path.exists(p):
            return p
    return None


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


class HardwarePanel:
    def __init__(self, border_style: str = "yellow"):
        self.border_style = border_style
        self._hackrf = _Cache(_HACKRF_TTL)
        self._chrony = _Cache(_CHRONY_TTL)

    def render(self) -> Panel:
        hrf = self._hackrf.get(_hackrf_info)
        pps_dev = _pps_device()
        pps_mod = _pps_module_loaded()
        gpsdo = _gpsdo_serial()
        chr_ = self._chrony.get(_chrony_stats)

        t = Table.grid(padding=(0, 2), expand=True)
        t.add_column(style="bright_cyan", justify="right")
        t.add_column()

        hrf_style = "bright_green" if hrf["detected"] else "bright_red"
        hrf_glyph = "◉" if hrf["detected"] else "○"
        t.add_row(
            "HackRF",
            f"[{hrf_style}]{hrf_glyph} {_esc(hrf['board'])} "
            f"{_esc(hrf['rev'])} fw={_esc(hrf['fw'])}[/]",
        )
        t.add_row("S/N", f"[dim]{_esc(hrf['serial'][-12:])}[/]")

        pps_ok = pps_dev and pps_mod
        pps_style = "bright_green" if pps_ok else "yellow"
        pps_text = "/dev/pps0" if pps_dev else "absent"
        if pps_dev and not pps_mod:
            pps_text += " (pps_gpio not loaded)"
        t.add_row("PPS GPIO", f"[{pps_style}]{'◉' if pps_ok else '○'} {pps_text}[/]")

        gpsdo_style = "bright_green" if gpsdo else "bright_red"
        gpsdo_text = gpsdo if gpsdo else "AWAITING LBE-1420"
        t.add_row(
            "GPSDO",
            f"[{gpsdo_style}]{'◉' if gpsdo else '○'} {_esc(gpsdo_text)}[/]",
        )

        rms = chr_["rms_ns"]
        if rms != rms:  # NaN
            rms_txt = "[dim]--[/]"
        elif rms < 1_000:
            rms_txt = f"[bright_green]{rms:6.0f}ns[/]"
        elif rms < 1_000_000:
            rms_txt = f"[yellow]{rms/1000:6.1f}µs[/]"
        else:
            rms_txt = f"[bright_red]{rms/1_000_000:6.1f}ms[/]"

        t.add_row(
            "Chrony",
            f"stratum {_esc(chr_['stratum'])}  "
            f"ref {_esc(chr_['ref'])}  rms {rms_txt}",
        )
        t.add_row("Leap", f"[dim]{_esc(chr_['leap'])}[/]")

        return Panel(
            t,
            title=f"[bold {self.border_style}]▓ HARDWARE ▓[/]",
            border_style=self.border_style,
            padding=(0, 1),
        )
