"""Pipeline status panel: systemd service, PID, uptime, packet count.

Reads:
  • systemctl show <unit>  → process state + PID
  • /proc/<pid>/stat       → uptime
  • output/primary/*.h5    → primary file count + bytes
  • output/secondary/...   → quarantine line count
  • /run/dslv-zpdi/health.json (with /tmp fallback) → live router/integrity stats
"""

import json
import math
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
        with open(f"/proc/{pid}/stat", encoding="utf-8") as f:
            parts = f.read().split()
        starttime_clk = int(parts[21])
        hz = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
        with open("/proc/uptime", encoding="utf-8") as f:
            sys_up = float(f.read().split()[0])
        return sys_up - starttime_clk / hz
    except Exception:
        return 0.0


_PRIMARY_TTL = 2.0
_HEALTH_TTL = 1.5
_HEALTH_STALE_S = 12.0  # Health data older than this means pipeline is not updating


def _read_health() -> dict:
    """Read the pipeline health endpoint (with /tmp fallback). Adds _stale flag."""
    for p in ("/run/dslv-zpdi/health.json", "/tmp/health.json"):
        try:
            mtime = os.stat(p).st_mtime
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            data["_stale"] = (time.time() - mtime) > _HEALTH_STALE_S
            return data
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            continue
    return {"_stale": True}


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


class _MtimeCache:
    def __init__(self):
        self.mtime = 0.0
        self.val = 0

    def get(self, path: str, producer):
        try:
            st = os.stat(path)
            mtime = st.st_mtime
        except Exception:
            mtime = 0.0
        if mtime != self.mtime:
            self.val = producer()
            self.mtime = mtime
        return self.val


def _output_dir() -> str:
    return os.getenv("DSLV_OUTPUT_DIR", "/home/dynogator/dslv-zpdi/output")


def _primary_dir_stats() -> dict:
    """Count primary HDF5 files and total byte size."""
    try:
        path = os.path.join(_output_dir(), "primary")
        files = 0
        size = 0
        for f in os.listdir(path):
            full = os.path.join(path, f)
            if os.path.isfile(full):
                files += 1
                try:
                    size += os.path.getsize(full)
                except OSError:
                    pass
        return {"files": files, "bytes": size}
    except Exception:
        return {"files": 0, "bytes": 0}


def _count_secondary_lines() -> int:
    path = os.path.join(_output_dir(), "secondary", "quarantine.jsonl")
    try:
        if not os.path.exists(path):
            return 0
        with open(path, "rb") as f:
            count = 0
            for _ in f:
                count += 1
            return count
    except Exception:
        return 0


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024.0:
            return f"{n:6.1f}{unit}" if unit != "B" else f"{n:>4}B"
        n /= 1024.0
    return f"{n:6.1f}PB"


def _fmt_jitter(jitter_ns) -> str:
    if jitter_ns is None:
        return "[dim]--[/]"
    try:
        v = float(jitter_ns)
    except (TypeError, ValueError):
        return "[dim]--[/]"

    if not math.isfinite(v):
        return "[dim]--[/]"

    if v < 1_000:
        return f"[bright_green]{v:.0f}ns[/]"
    if v < 1_000_000:
        return f"[yellow]{v/1000:.1f}µs[/]"
    if v < 1_000_000_000:
        return f"[bright_red]{v/1_000_000:.1f}ms[/]"
    return "[bright_red]>1s[/]"


class PipelinePanel:
    def __init__(self, unit: str = "dslv-zpdi", border_style: str = "bright_green"):
        self.unit = unit
        self.border_style = border_style
        self._last_pkt: int | None = None
        self._last_t = time.time()
        self._prim_cache = _Cache(_PRIMARY_TTL)
        self._sec_cache = _MtimeCache()
        self._health_cache = _Cache(_HEALTH_TTL)

    def render(self, compact: bool = False) -> Panel:
        info = _systemctl_show(self.unit)
        state = info.get("ActiveState", "?")
        substate = info.get("SubState", "?")
        pid = int(info.get("MainPID", "0") or 0)

        uptime = _proc_uptime_seconds(pid) if pid > 0 else 0.0
        prim_stats = self._prim_cache.get(_primary_dir_stats)
        prim_files = prim_stats["files"]
        prim_bytes = prim_stats["bytes"]
        sec = self._sec_cache.get(
            os.path.join(_output_dir(), "secondary", "quarantine.jsonl"),
            _count_secondary_lines,
        )
        health = self._health_cache.get(_read_health)

        now = time.time()
        total_pkts = prim_files + sec
        dt = now - self._last_t
        if self._last_pkt is None or dt <= 0:
            rate = 0.0
        else:
            rate = max(0.0, (total_pkts - self._last_pkt) / dt)
        self._last_pkt = total_pkts
        self._last_t = now

        state_style = (
            "bright_green" if state == "active" else
            "yellow" if state == "reloading" else
            "bright_red"
        )
        heartbeat = "◉" if state == "active" else "○"

        t = Table.grid(padding=(0, 1), expand=True)
        t.add_column(style="bright_cyan", justify="right")
        t.add_column()

        h_m, h_s = divmod(int(uptime), 60)
        h_h, h_m = divmod(h_m, 60)
        up_s = f"{h_h}h{h_m}m" if h_h else f"{h_m}m{h_s}s"
        if compact and h_h:
            up_s = f"{h_h}h{h_m}m"

        # Stats from health endpoint
        stats = health.get("stats", {}) or {}
        baseline = health.get("baseline", {}) or {}
        coherence = health.get("coherence", {}) or {}
        health_stale = health.get("_stale", False)
        sim_fallback = health.get("sim_fallback", False)

        primary_written = stats.get("primary_written", 0)
        secondary_logged = stats.get("secondary_logged", 0)
        integrity_failed = stats.get("integrity_failed", 0)
        checksum_missing = stats.get("checksum_missing", 0)
        checksum_invalid = stats.get("checksum_invalid", 0)
        rejected = stats.get("rejected", 0)
        timing_healthy = health.get("timing_healthy")
        timing_jitter = health.get("timing_jitter_ns")
        baseline_state = baseline.get("baseline_state", "?")
        baseline_ready = baseline.get("ready")
        ticks = health.get("ticks", 0)
        hal_mode = health.get("hal_mode", "?")
        node_id = health.get("node_id", "?")

        r_smooth = coherence.get("r_smooth", 0.0)
        r_global = coherence.get("r_global", 0.0)

        sim_tag = " [yellow]SIM[/]" if sim_fallback else ""
        stale_tag = " [dim]stale[/]" if health_stale else ""

        if compact:
            # Row 1: Svc + Up
            t.add_row("Svc", f"[{state_style}]{heartbeat} {state}[/] [dim]•[/] {up_s}{sim_tag}")
            # Row 2: Node + Jitter
            jit_s = _fmt_jitter(timing_jitter).strip()
            t.add_row("Node", f"{node_id[:8]} [dim]•[/] {jit_s}{stale_tag}")
            # Row 3: Coherence
            coh_sty = "bright_green" if r_smooth >= 0.4 else "yellow" if r_smooth >= 0.15 else "dim"
            t.add_row("Coh", f"[{coh_sty}]r{r_smooth:.2f}[/] [magenta]R{r_global:.2f}[/]")
            # Row 4: Base + Rate
            bl_color = "bright_green" if baseline_ready else "yellow"
            thr = baseline.get('threshold', 0.0)
            t.add_row("Bl", f"[{bl_color}]{baseline_state[:5]}[/] [dim]t{thr:.2f}•[/][magenta]{rate:.1f}[/]p/s")
        else:
            # Row 1: service + node
            t.add_row(
                "Service",
                f"[bold {state_style}]{heartbeat} {state}/{substate}[/]  "
                f"[dim]pid={pid or 'n/a'}  up={up_s}[/]{sim_tag}",
            )
            hal_display = f"[yellow]{hal_mode}[/]" if sim_fallback else f"[dim]{hal_mode}[/]"
            t.add_row(
                "Node",
                f"[bright_white]{node_id}[/]  hal={hal_display}  [dim]ticks={ticks}[/]{stale_tag}",
            )

            # Row 2: Coherence
            coh_sty = "bright_green" if r_smooth >= 0.4 else "yellow" if r_smooth >= 0.15 else "bright_white"
            t.add_row(
                "Coherence",
                f"[{coh_sty}]r_smooth = {r_smooth:.4f}[/]  "
                f"[magenta]R_global = {r_global:.4f}[/]",
            )

            # Row 3: streams
            primary_color = "bright_green" if primary_written else "bright_white"
            sec_color = "yellow" if secondary_logged else "dim"
            t.add_row(
                "PRIMARY",
                f"[{primary_color}]{primary_written}[/] events  "
                f"[dim]{prim_files} files / {_fmt_bytes(prim_bytes)}[/]",
            )
            t.add_row(
                "SECONDARY",
                f"[{sec_color}]{secondary_logged}[/] logged  "
                f"[dim]{sec} on disk[/]",
            )

            # Row 4: integrity
            integrity_color = "bright_red" if (
                integrity_failed or checksum_missing or checksum_invalid
            ) else "bright_green"
            integrity_glyph = "◉" if integrity_color == "bright_green" else "✗"
            t.add_row(
                "Integrity",
                f"[{integrity_color}]{integrity_glyph}[/] "
                f"fail={integrity_failed} miss={checksum_missing} "
                f"inv={checksum_invalid} rej={rejected}",
            )

            # Row 5: baseline (SPEC-009)
            bl_color = "bright_green" if baseline_ready else "yellow"
            bl_glyph = "◉" if baseline_ready else "◌"
            t.add_row(
                "Baseline",
                f"[{bl_color}]{bl_glyph} {baseline_state}[/]  "
                f"[dim]thr={baseline.get('threshold', 0):.2f}[/]",
            )

            # Row 6: timing health (SPEC-004A.3)
            if timing_healthy is None:
                timing_text = "[dim]-- (no health data)[/]"
            else:
                tcolor = "bright_green" if timing_healthy else "bright_red"
                tglyph = "◉" if timing_healthy else "○"
                timing_text = (
                    f"[{tcolor}]{tglyph} {'healthy' if timing_healthy else 'UNHEALTHY'}[/]  "
                    f"jitter {_fmt_jitter(timing_jitter)}"
                )
            t.add_row("Timing", timing_text)

            # Row 7: throughput
            t.add_row("Rate", f"[bright_magenta]{rate:5.2f}[/] pkt/s")

        title = "[bold bright_green]▓ PIPE ▓[/]" if compact else "[bold bright_green]▓ PIPELINE ▓[/]"
        return Panel(
            t,
            title=title,
            border_style=self.border_style,
            padding=(0, 1),
        )
