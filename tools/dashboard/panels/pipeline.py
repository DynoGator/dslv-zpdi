"""Pipeline status panel: systemd service, PID, uptime, packet count."""

import json
import os
import subprocess
import time

from rich.panel import Panel
from rich.table import Table


def _systemctl_show(unit: str) -> dict:
    try:
        out = subprocess.check_output(
            ["systemctl", "show", unit, "--no-pager"],
            text=True,
            timeout=2,
        )
        d = {}
        for line in out.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                d[k] = v
        return d
    except Exception:
        return {}


def _proc_uptime_seconds(pid: int) -> float:
    try:
        with open(f"/proc/{pid}/stat", "r", encoding="utf-8") as f:
            parts = f.read().split()
        starttime_clk = int(parts[21])
        hz = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
        with open("/proc/uptime", "r", encoding="utf-8") as f:
            sys_up = float(f.read().split()[0])
        return sys_up - starttime_clk / hz
    except Exception:
        return 0.0


def _count_primary_pkts() -> int:
    try:
        out = subprocess.check_output(
            ["find", "/home/dynogator/dslv-zpdi/output/primary", "-type", "f"],
            text=True, timeout=2,
        )
        return len([l for l in out.splitlines() if l.strip()])
    except Exception:
        return 0


def _count_secondary_lines() -> int:
    path = "/home/dynogator/dslv-zpdi/output/secondary/quarantine.jsonl"
    try:
        if not os.path.exists(path):
            return 0
        with open(path, "rb") as f:
            # cheap estimate
            count = 0
            for _ in f:
                count += 1
            return count
    except Exception:
        return 0


class PipelinePanel:
    def __init__(self, unit: str = "dslv-zpdi"):
        self.unit = unit
        self._last_pkt = 0
        self._last_t = time.time()

    def render(self) -> Panel:
        info = _systemctl_show(self.unit)
        state = info.get("ActiveState", "?")
        substate = info.get("SubState", "?")
        pid = int(info.get("MainPID", "0") or 0)
        exec_main = info.get("ExecMainStartTimestampMonotonic", "0")

        uptime = _proc_uptime_seconds(pid) if pid > 0 else 0.0
        prim = _count_primary_pkts()
        sec = _count_secondary_lines()

        now = time.time()
        total_pkts = prim + sec
        dt = now - self._last_t
        rate = (total_pkts - self._last_pkt) / dt if dt > 0 else 0.0
        self._last_pkt = total_pkts
        self._last_t = now

        state_style = (
            "bright_green" if state == "active" else
            "yellow" if state == "reloading" else
            "bright_red"
        )
        heartbeat = "◉" if state == "active" else "○"

        t = Table.grid(padding=(0, 2), expand=True)
        t.add_column(style="bright_cyan", justify="right")
        t.add_column()

        h_m, h_s = divmod(int(uptime), 60)
        h_h, h_m = divmod(h_m, 60)
        up_s = f"{h_h}h{h_m}m{h_s}s" if h_h else f"{h_m}m{h_s}s"

        t.add_row("State", f"[bold {state_style}]{heartbeat} {state}/{substate}[/]")
        t.add_row("PID", f"[bright_green]{pid}[/]" if pid else "[bright_red]n/a[/]")
        t.add_row("Up", f"[dim]{up_s}[/]")
        t.add_row("HDF5", f"[bright_green]{prim}[/] files")
        t.add_row("Quarantine", f"[yellow]{sec}[/] pkts")
        t.add_row("Rate", f"[bright_magenta]{rate:5.1f}[/] pkt/s")

        return Panel(
            t,
            title="[bold bright_green]▓ PIPELINE ▓[/]",
            border_style="bright_green",
            padding=(0, 1),
        )
