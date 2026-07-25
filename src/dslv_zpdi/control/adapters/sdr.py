"""SPEC-022 — SDR status and configuration adapter.

Reads current SDR parameters from environment variables and a runtime
override JSON file.  Write operations persist new values to the runtime
override file; they are applied on the next daemon restart.

The authoritative SDR (HackRF / PlutoSDR on the Pi 5) is not touched
here.  This adapter reflects the Tier-2 mobile node's own sensor config.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(os.environ.get("DSLV_REPO_ROOT", "/root/dslv-zpdi"))
_RUNTIME_CONFIG = REPO_ROOT / "data/sdr_runtime_config.json"


def _load() -> dict[str, Any]:  # SPEC-022
    try:
        return json.loads(_RUNTIME_CONFIG.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save(config: dict[str, Any]) -> None:  # SPEC-022
    _RUNTIME_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    _RUNTIME_CONFIG.write_text(json.dumps(config, indent=2))


class SdrAdapter:
    """SPEC-022 — SDR status and configuration adapter."""

    def status(self) -> dict[str, Any]:
        """Return SDR configuration merged from environment and runtime overrides."""
        cfg = _load()
        return {
            "device": cfg.get("device", os.environ.get("ZPDI_SDR_DEVICE", "none")),
            "mode": cfg.get("mode", os.environ.get("ZPDI_SDR_MODE", "simulated")),
            "center_frequency_hz": cfg.get(
                "center_frequency_hz",
                int(os.environ.get("ZPDI_SDR_FREQ_HZ", "0")),
            ),
            "sample_rate_hz": cfg.get(
                "sample_rate_hz",
                int(os.environ.get("ZPDI_SDR_SAMPLE_RATE_HZ", "0")),
            ),
            "gain_db": cfg.get(
                "gain_db",
                float(os.environ.get("ZPDI_SDR_GAIN_DB", "0")),
            ),
            "pending_restart": bool(cfg),
            "note": "Tier-2 mobile node config; Tier-1 Pi 5 SDR is authoritative",
        }

    def set_mode(self, mode: str) -> dict[str, Any]:
        cfg = _load()
        cfg["mode"] = mode
        cfg["updated_at"] = time.time()
        _save(cfg)
        return {"mode": mode, "applied": "pending_restart"}

    def set_center_frequency(self, hz: int) -> dict[str, Any]:
        cfg = _load()
        cfg["center_frequency_hz"] = hz
        cfg["updated_at"] = time.time()
        _save(cfg)
        return {"center_frequency_hz": hz, "applied": "pending_restart"}

    def set_sample_rate(self, sample_rate_hz: int) -> dict[str, Any]:
        cfg = _load()
        cfg["sample_rate_hz"] = sample_rate_hz
        cfg["updated_at"] = time.time()
        _save(cfg)
        return {"sample_rate_hz": sample_rate_hz, "applied": "pending_restart"}

    def set_gain(self, gain_db: float) -> dict[str, Any]:
        cfg = _load()
        cfg["gain_db"] = gain_db
        cfg["updated_at"] = time.time()
        _save(cfg)
        return {"gain_db": gain_db, "applied": "pending_restart"}
