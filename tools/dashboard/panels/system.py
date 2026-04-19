"""System stats panel: CPU, memory, temp, throttling."""

import os
import subprocess
import time

from rich.panel import Panel
from rich.table import Table


def _read(path: str, default: str = "") -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return default


def _cpu_temp_c() -> float:
    raw = _read("/sys/class/thermal/thermal_zone0/temp", "0")
    try:
        return int(raw) / 1000.0
    except Exception:
        return 0.0


def _cpu_usage_percent(prev_state: dict) -> float:
    """Compute CPU % since last call. prev_state is a mutable dict."""
    try:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            fields = f.readline().split()[1:8]
        vals = [int(x) for x in fields]
        idle = vals[3] + vals[4]
        total = sum(vals)
        last_idle = prev_state.get("idle", 0)
        last_total = prev_state.get("total", 0)
        d_idle = idle - last_idle
        d_total = total - last_total
        prev_state["idle"] = idle
        prev_state["total"] = total
        if d_total <= 0:
            return 0.0
        return (1.0 - d_idle / d_total) * 100.0
    except Exception:
        return 0.0


def _mem() -> tuple:
    try:
        meminfo = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                k, v = line.split(":", 1)
                meminfo[k] = int(v.split()[0])  # kB
        total = meminfo.get("MemTotal", 1) / 1024 / 1024  # GiB
        avail = meminfo.get("MemAvailable", 0) / 1024 / 1024
        used = total - avail
        return used, total
    except Exception:
        return 0.0, 0.0


def _load_avg() -> tuple:
    try:
        with open("/proc/loadavg", "r", encoding="utf-8") as f:
            parts = f.read().split()
        return float(parts[0]), float(parts[1]), float(parts[2])
    except Exception:
        return 0.0, 0.0, 0.0


def _governor() -> str:
    return _read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor", "?")


def _throttle_status() -> str:
    try:
        out = subprocess.check_output(
            ["vcgencmd", "get_throttled"], timeout=1, text=True
        ).strip()
        v = int(out.split("=")[1], 16)
        flags = []
        if v & 1:
            flags.append("UV!")
        if v & 4:
            flags.append("THR!")
        if not flags:
            if v & (1 << 16):
                flags.append("uv-past")
            if v & (1 << 18):
                flags.append("thr-past")
        return ",".join(flags) if flags else "clean"
    except Exception:
        return "?"


def _uptime() -> str:
    try:
        up = float(_read("/proc/uptime", "0").split()[0])
        h, rem = divmod(int(up), 3600)
        m, s = divmod(rem, 60)
        d, h = divmod(h, 24)
        if d:
            return f"{d}d {h}h {m}m"
        if h:
            return f"{h}h {m}m"
        return f"{m}m {s}s"
    except Exception:
        return "?"


class SystemPanel:
    def __init__(self):
        self._cpu_state = {}

    def render(self) -> Panel:
        cpu_pct = _cpu_usage_percent(self._cpu_state)
        mem_used, mem_total = _mem()
        load = _load_avg()
        temp = _cpu_temp_c()
        gov = _governor()
        thr = _throttle_status()
        up = _uptime()

        t = Table.grid(padding=(0, 2), expand=True)
        t.add_column(style="bright_cyan", justify="right")
        t.add_column(style="bright_green")

        temp_style = "bright_green" if temp < 65 else "yellow" if temp < 75 else "bright_red"
        cpu_style = "bright_green" if cpu_pct < 60 else "yellow" if cpu_pct < 85 else "bright_red"
        thr_style = "bright_green" if thr in ("clean",) else "yellow" if "past" in thr else "bright_red"

        t.add_row("CPU", f"[{cpu_style}]{cpu_pct:5.1f}%[/] @ [magenta]{gov}[/]")
        t.add_row("Mem", f"{mem_used:4.1f}/{mem_total:4.1f} GiB")
        t.add_row("Load", f"{load[0]:.2f} {load[1]:.2f} {load[2]:.2f}")
        t.add_row("Temp", f"[{temp_style}]{temp:4.1f}°C[/]")
        t.add_row("Power", f"[{thr_style}]{thr}[/]")
        t.add_row("Uptime", f"[dim]{up}[/]")

        return Panel(
            t,
            title="[bold bright_cyan]▓ SYSTEM ▓[/]",
            border_style="bright_cyan",
            padding=(0, 1),
        )
