"""
SPEC-007 | Trust Tier: Routed (Layer 3) — Mobile Variant
Dual-Stream Protocol enforcer for Tier-2 Swarm nodes.

All mobile packets are SECONDARY_QUARANTINED by hardware definition.
The router categorises them by coherence score:
  r_smooth >= 0.40       → anomalous_candidate_tier2
  0.15 <= r_smooth < 0.40 → structured_background_tier2
  r_smooth < 0.15         → noise_tier2
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger("zpdi.router")


def route_packet(payload_dict: dict[str, Any]) -> dict[str, Any]:
    """SPEC-007 mobile router — Tier-2 quarantine enforcement.

    Returns a routing decision dict with keys:
      stream: "PRIMARY" | "SECONDARY" | "PRIMARY_CANDIDATE"
      reason: human-readable routing reason
      trust_state: final trust state string
    """
    hardware_tier = payload_dict.get("hardware_tier", 1)
    trust_state = payload_dict.get("trust_state", "UNKNOWN")
    r_smooth = payload_dict.get("r_smooth", 0.0)

    # Tier-2 hardware can NEVER produce primary institutional data
    if hardware_tier == 2:
        if r_smooth >= 0.40:
            return {
                "stream": "SECONDARY",
                "reason": "anomalous_candidate_tier2",
                "trust_state": "SECONDARY_QUARANTINED",
            }
        elif r_smooth >= 0.15:
            return {
                "stream": "SECONDARY",
                "reason": "structured_background_tier2",
                "trust_state": "SECONDARY_QUARANTINED",
            }
        else:
            return {
                "stream": "SECONDARY",
                "reason": "noise_tier2",
                "trust_state": "SECONDARY_QUARANTINED",
            }

    # Tier-1 logic (not reachable on mobile, preserved for correctness)
    if trust_state in ("KILLED", "SECONDARY_QUARANTINED"):
        return {
            "stream": "SECONDARY",
            "reason": "trust_failure",
            "trust_state": trust_state,
        }

    if r_smooth >= 0.40 and payload_dict.get("event_window_id"):
        return {
            "stream": "PRIMARY",
            "reason": "confirmed_event",
            "trust_state": "PRIMARY_ACCEPTED",
        }
    elif r_smooth >= 0.15:
        return {
            "stream": "PRIMARY_CANDIDATE",
            "reason": "structured_background",
            "trust_state": "PRIMARY_CANDIDATE",
        }
    else:
        return {
            "stream": "SECONDARY",
            "reason": "below_threshold",
            "trust_state": "SECONDARY_QUARANTINED",
        }


class SecondaryLog:
    """JSONL sink for all SECONDARY_QUARANTINED / PRIMARY_CANDIDATE packets.

    Rotates at 10 MB, gzipping old chunks.  Keeps up to 5 backups.
    """

    ROTATE_SIZE_BYTES = 10 * 1024 * 1024
    MAX_BACKUPS = 5

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()

    def prepare(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    async def write(self, p: Any) -> None:
        async with self._lock:
            await asyncio.to_thread(self._write_sync, p)

    def _rotate_if_needed(self) -> None:
        if not self._path.exists():
            return
        if self._path.stat().st_size < self.ROTATE_SIZE_BYTES:
            return
        # Rotate existing backups upward
        for i in range(self.MAX_BACKUPS - 1, 0, -1):
            src = self._path.parent / f"{self._path.name}.{i}.gz"
            dst = self._path.parent / f"{self._path.name}.{i + 1}.gz"
            if src.exists():
                src.replace(dst)
        # Gzip current file to .1.gz
        import gzip
        rotated = self._path.parent / f"{self._path.name}.1.gz"
        with self._path.open("rb") as f_in:
            with gzip.open(rotated, "wb") as f_out:
                f_out.write(f_in.read())
        self._path.unlink()

    def _write_sync(self, p: Any) -> None:
        body = p.body if hasattr(p, "body") else p
        full_raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self._rotate_if_needed()
        with self._path.open("ab") as fh:
            fh.write(full_raw)
            fh.write(b"\n")
