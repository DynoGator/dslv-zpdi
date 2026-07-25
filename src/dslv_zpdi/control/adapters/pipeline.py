"""SPEC-022 — Pipeline state and control adapter.

Reads pipeline state from PID files and the supervisor log.
Sends SIGTERM to the supervisor process for pipeline.stop.
No arbitrary shell execution is permitted; all operations are bounded.
"""

from __future__ import annotations

import os
import signal
from pathlib import Path
from typing import Any

REPO_ROOT = Path(os.environ.get("DSLV_REPO_ROOT", "/root/dslv-zpdi"))

_PID_FILES: dict[str, Path] = {
    "mobile_node": REPO_ROOT / ".zpdi_daemon.pid",
    "tier1_server": REPO_ROOT / ".zpdi_tier1.pid",
    "web_dashboard": REPO_ROOT / ".zpdi_webdash.pid",
}
_SUPERVISOR_LOG = REPO_ROOT / "logs/supervisor.log"
_ROTATE_MARKER = REPO_ROOT / "logs/.rotate_output_requested"
_START_MARKER = REPO_ROOT / "logs/.start_pipeline_requested"


def _read_pid(path: Path) -> tuple[int | None, bool]:  # SPEC-022
    """Return (pid, is_alive) from a PID file."""
    try:
        pid = int(path.read_text().strip())
    except (OSError, ValueError):
        return None, False
    try:
        os.kill(pid, 0)
        return pid, True
    except ProcessLookupError:
        return pid, False
    except PermissionError:
        return pid, True  # Process exists but we can't signal it


def _find_supervisor_pid() -> int | None:  # SPEC-022
    """Locate the supervisor bash PID by scanning /proc cmdline entries."""
    try:
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                cmdline = Path(f"/proc/{entry}/cmdline").read_bytes()
                if b"supervisor.sh" in cmdline:
                    return int(entry)
            except (OSError, ValueError):
                continue
    except OSError:
        pass
    return None


def _last_log_line() -> str:  # SPEC-022
    try:
        lines = [ln for ln in _SUPERVISOR_LOG.read_text().splitlines() if ln.strip()]
        return lines[-1] if lines else ""
    except OSError:
        return ""


class PipelineAdapter:
    """SPEC-022 — Pipeline state and control adapter."""

    def status(self) -> dict[str, Any]:
        """Read current pipeline process state from supervisor PID files."""
        services: dict[str, Any] = {}
        any_alive = False
        for name, pid_file in _PID_FILES.items():
            pid, alive = _read_pid(pid_file)
            services[name] = {"pid": pid, "alive": alive}
            if alive:
                any_alive = True
        return {
            "pipeline": "dslv-zpdi-mobile-stack",
            "active": any_alive,
            "services": services,
            "last_supervisor_log": _last_log_line(),
        }

    def stop(self) -> dict[str, Any]:
        """Stop the pipeline by sending SIGTERM to the supervisor process.

        Prefers signalling the supervisor (which cascades a clean shutdown
        via its _stop trap).  Falls back to individually signalling each
        managed PID if the supervisor cannot be found.
        """
        sup_pid = _find_supervisor_pid()
        if sup_pid is not None:
            try:
                os.kill(sup_pid, signal.SIGTERM)
                return {
                    "acknowledged": True,
                    "signal": "SIGTERM",
                    "target": "supervisor",
                    "pid": sup_pid,
                }
            except (ProcessLookupError, PermissionError):
                pass

        killed: list[int] = []
        errors: list[str] = []
        for name, pid_file in _PID_FILES.items():
            pid, alive = _read_pid(pid_file)
            if pid is not None and alive:
                try:
                    os.kill(pid, signal.SIGTERM)
                    killed.append(pid)
                except (ProcessLookupError, PermissionError) as exc:
                    errors.append(f"{name}/{pid}: {exc}")

        if not killed and not errors:
            return {"acknowledged": False, "error": "no pipeline processes found"}
        return {
            "acknowledged": True,
            "signal": "SIGTERM",
            "target": "individual_processes",
            "pids_signaled": killed,
            "errors": errors,
        }

    def start(self) -> dict[str, Any]:
        """Request pipeline start by writing a marker file.

        Direct launch from within the C2 plane is not supported — doing so
        would create an orphaned proot session.  The boot script
        (99-start-zpdi.sh) or an operator must act on the marker.
        """
        try:
            _START_MARKER.parent.mkdir(parents=True, exist_ok=True)
            _START_MARKER.touch()
            return {
                "acknowledged": True,
                "marker": str(_START_MARKER),
                "note": "start-request written; operator or boot script must act",
            }
        except OSError as exc:
            return {"acknowledged": False, "error": str(exc)}

    def rotate_output(self) -> dict[str, Any]:
        """Request HDF5/JSONL output rotation via a marker file."""
        try:
            _ROTATE_MARKER.parent.mkdir(parents=True, exist_ok=True)
            _ROTATE_MARKER.touch()
            return {"acknowledged": True, "marker": str(_ROTATE_MARKER)}
        except OSError as exc:
            return {"acknowledged": False, "error": str(exc)}
