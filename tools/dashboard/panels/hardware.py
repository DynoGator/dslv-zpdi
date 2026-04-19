"""Hardware status panel: HackRF, PPS, GPSDO, chrony."""

import os
import re
import subprocess

from rich.panel import Panel
from rich.table import Table


def _hackrf_info() -> dict:
    try:
        out = subprocess.check_output(
            ["hackrf_info"], text=True, timeout=3, stderr=subprocess.STDOUT
        )
        serial = re.search(r"Serial number:\s+(\S+)", out)
        fw = re.search(r"Firmware Version:\s+(\S+)", out)
        rev = re.search(r"Hardware Revision:\s+(\S+)", out)
        return {
            "detected": "Found HackRF" in out,
            "serial": serial.group(1) if serial else "?",
            "fw": fw.group(1) if fw else "?",
            "rev": rev.group(1) if rev else "?",
        }
    except Exception:
        return {"detected": False, "serial": "-", "fw": "-", "rev": "-"}


def _pps_device() -> bool:
    return os.path.exists("/dev/pps0")


def _pps_module_loaded() -> bool:
    try:
        with open("/proc/modules", "r", encoding="utf-8") as f:
            return "pps_gpio" in f.read()
    except Exception:
        return False


def _gpsdo_serial() -> bool:
    return any(os.path.exists(p) for p in ("/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0"))


def _chrony_stats() -> dict:
    try:
        out = subprocess.check_output(
            ["chronyc", "tracking"], text=True, timeout=2
        )
        rms = re.search(r"RMS offset\s+:\s+([-+.\d]+)\s+(\w+)", out)
        stratum = re.search(r"Stratum\s+:\s+(\d+)", out)
        leap = re.search(r"Leap status\s+:\s+(.+)", out)
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
            "rms_ns": rms_ns,
        }
    except Exception:
        return {"stratum": "?", "leap": "?", "rms_ns": float("nan")}


class HardwarePanel:
    def render(self) -> Panel:
        hrf = _hackrf_info()
        pps_dev = _pps_device()
        pps_mod = _pps_module_loaded()
        gpsdo = _gpsdo_serial()
        chr_ = _chrony_stats()

        t = Table.grid(padding=(0, 2), expand=True)
        t.add_column(style="bright_cyan", justify="right")
        t.add_column()

        hrf_style = "bright_green" if hrf["detected"] else "bright_red"
        hrf_glyph = "◉" if hrf["detected"] else "○"
        t.add_row("HackRF", f"[{hrf_style}]{hrf_glyph} {hrf['rev']} fw={hrf['fw']}[/]")
        t.add_row("S/N", f"[dim]{hrf['serial'][-8:]}[/]")

        pps_ok = pps_dev and pps_mod
        pps_style = "bright_green" if pps_ok else "yellow"
        t.add_row("PPS GPIO", f"[{pps_style}]{'◉' if pps_ok else '○'} {'/dev/pps0' if pps_dev else 'not present'}[/]")

        gpsdo_style = "bright_green" if gpsdo else "bright_red"
        t.add_row("GPSDO", f"[{gpsdo_style}]{'◉' if gpsdo else '○'} {'ttyACM0' if gpsdo else 'AWAITING DELIVERY'}[/]")

        rms = chr_["rms_ns"]
        if rms != rms:  # NaN
            rms_txt = "[dim]--[/]"
        elif rms < 1_000:
            rms_txt = f"[bright_green]{rms:6.0f}ns[/]"
        elif rms < 1_000_000:
            rms_txt = f"[yellow]{rms/1000:6.1f}µs[/]"
        else:
            rms_txt = f"[bright_red]{rms/1_000_000:6.1f}ms[/]"

        t.add_row("Chrony", f"stratum {chr_['stratum']}  rms {rms_txt}")
        t.add_row("Leap", f"[dim]{chr_['leap']}[/]")

        return Panel(
            t,
            title="[bold yellow]▓ HARDWARE ▓[/]",
            border_style="yellow",
            padding=(0, 1),
        )
