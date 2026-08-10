"""
DSLV-ZPDI Unified SDR State Manager
Provides IPC synchronization between app.py (Main Dashboard), demod_app.py (Demod Interface),
and external services via atomic JSON file operations in RAM-disk (/dev/shm).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict

SHM_STATE_PATH = Path("/dev/shm/dslv_sdr_state.json")
FALLBACK_STATE_PATH = Path("/tmp/dslv_sdr_state.json")


def get_state_path() -> Path:
    """Return /dev/shm path if available and writable, else /tmp path."""
    if Path("/dev/shm").exists() and os.access("/dev/shm", os.W_OK):
        return SHM_STATE_PATH
    return FALLBACK_STATE_PATH


DEFAULT_SDR_STATE: Dict[str, Any] = {
    "center_hz": 98_100_000.0,
    "bandwidth_hz": 200_000.0,
    "gain_db": 30.0,
    "squelch_db": -40.0,
    "demod_profile": "FM Radio",
    "audio_active": False,
    "mimo_tx": False,
    "paused": False,
    "updated_by": "initialization",
    "timestamp": 0.0,
}


class SDRStateManager:
    """
    Manages atomic shared RAM-disk state synchronization between processes.
    Guarantees that tuning, gain, squelch, and profile changes in one TUI
    are immediately reflected in all active dashboard processes.
    """

    def __init__(self, owner_name: str = "unknown"):
        self.owner_name = owner_name
        self.state_path = get_state_path()
        self.last_seen_timestamp: float = 0.0
        self._ensure_initial_state()

    def _ensure_initial_state(self) -> None:
        """Create the state file with default values if it doesn't exist yet."""
        if not self.state_path.exists():
            state = dict(DEFAULT_SDR_STATE)
            state["timestamp"] = time.time()
            state["updated_by"] = self.owner_name
            self.write_state(state)

    def read_state(self) -> Dict[str, Any]:
        """Atomically read shared state from RAM disk."""
        if not self.state_path.exists():
            return dict(DEFAULT_SDR_STATE)
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception:
            return dict(DEFAULT_SDR_STATE)

    def write_state(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atomically write updated state to RAM disk using temporary file replacement.
        """
        current = self.read_state()
        current.update(updates)
        current["timestamp"] = time.time()
        current["updated_by"] = self.owner_name

        tmp_path = self.state_path.with_suffix(f".tmp.{os.getpid()}")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2)
            os.replace(tmp_path, self.state_path)
            self.last_seen_timestamp = current["timestamp"]
        except Exception:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
        return current

    def update_key(self, key: str, value: Any) -> None:
        """Convenience helper to update a single state parameter."""
        self.write_state({key: value})

    def sync_from_disk(self, target_obj: Any, force: bool = False) -> bool:
        """
        Poll disk state. If updated by another process (or if force=True), copy attributes onto target_obj.
        Returns True if state was applied.
        """
        state = self.read_state()
        ts = state.get("timestamp", 0.0)
        if ts > self.last_seen_timestamp or force:
            self.last_seen_timestamp = ts
            if state.get("updated_by") != self.owner_name or force:
                self.apply_to_object(target_obj, state)
                return True
        return False

    def apply_to_object(self, target_obj: Any, state: Dict[str, Any]) -> None:
        """Map shared state keys to target object attributes."""
        # For demod_app.py (DemodApp)
        if hasattr(target_obj, "freq_hz") and "center_hz" in state:
            target_obj.freq_hz = float(state["center_hz"])
        if hasattr(target_obj, "bandwidth_hz") and "bandwidth_hz" in state:
            target_obj.bandwidth_hz = float(state["bandwidth_hz"])
        if hasattr(target_obj, "gain_db") and "gain_db" in state:
            target_obj.gain_db = float(state["gain_db"])
        if hasattr(target_obj, "squelch") and "squelch_db" in state:
            target_obj.squelch = float(state["squelch_db"])
        if hasattr(target_obj, "profile") and "demod_profile" in state:
            target_obj.profile = str(state["demod_profile"])
        if hasattr(target_obj, "rx_only") and "mimo_tx" in state:
            target_obj.rx_only = not bool(state["mimo_tx"])
        if hasattr(target_obj, "paused") and "paused" in state:
            target_obj.paused = bool(state["paused"])

        # For app.py (Dashboard) Waterfall & Demod Panels
        if hasattr(target_obj, "wf_p") and target_obj.wf_p:
            wf = target_obj.wf_p
            if "center_hz" in state and wf.center_hz != int(state["center_hz"]):
                wf.center_hz = int(state["center_hz"])
                if hasattr(wf, "_restart_stream_if_running"):
                    wf._restart_stream_if_running()
            if "bandwidth_hz" in state and hasattr(wf, "span_hz") and wf.span_hz != int(state["bandwidth_hz"]):
                wf.span_hz = int(state["bandwidth_hz"])
            if "gain_db" in state and hasattr(wf, "lna_gain"):
                wf.lna_gain = int(state["gain_db"])

        if hasattr(target_obj, "demod_p") and target_obj.demod_p:
            dp = target_obj.demod_p
            if "demod_profile" in state:
                dp.active_profile = state["demod_profile"]
            if "audio_active" in state:
                dp.is_active = state["audio_active"]
            if "mimo_tx" in state:
                dp.mimo_tx = state["mimo_tx"]
