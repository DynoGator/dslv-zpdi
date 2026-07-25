"""SPEC-022 — Read-only HDF5 telemetry query adapter.

Opens the live HDF5 file in SWMR read mode to avoid contention with the
writing mobile node.  All queries are bounded by MAX_EXPORT_RECORDS.

HDF5 schema (dataset: 'payloads'):
  wall_ns  uint64  — wall-clock nanoseconds since Unix epoch
  sha256   S64     — hex SHA-256 of the raw payload bytes
  payload  object  — JSON bytes containing sensor readings
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

try:
    import h5py
    _HAS_H5PY = True
except ImportError:  # pragma: no cover
    _HAS_H5PY = False

HDF5_PATH = Path(os.environ.get("ZPDI_HDF5_PATH", "/root/dslv-zpdi/data/zpdi_stream.h5"))
MAX_EXPORT_RECORDS = 1000


def _coerce(value: Any) -> Any:  # SPEC-022
    """Convert numpy / bytes values to JSON-serializable types."""
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return repr(value)
    return value


class Hdf5Adapter:
    """SPEC-022 — Bounded read-only HDF5 telemetry query adapter."""

    def summary(self) -> dict[str, Any]:
        """Return file metadata: size, record count, and timestamp range."""
        if not HDF5_PATH.exists():
            return {"error": "HDF5 file not found", "path": str(HDF5_PATH)}

        stat = HDF5_PATH.stat()
        result: dict[str, Any] = {
            "path": str(HDF5_PATH),
            "file_size_bytes": stat.st_size,
            "mtime": stat.st_mtime,
        }

        if not _HAS_H5PY:
            result["records"] = "h5py unavailable"
            return result

        try:
            with h5py.File(HDF5_PATH, "r", swmr=True) as f:
                result["datasets"] = list(f.keys())
                if "payloads" in f:
                    ds = f["payloads"]
                    n = len(ds)
                    result["records"] = n
                    if n > 0:
                        result["first_wall_ns"] = int(ds[0]["wall_ns"])
                        result["last_wall_ns"] = int(ds[-1]["wall_ns"])
                        result["first_ts"] = result["first_wall_ns"] / 1e9
                        result["last_ts"] = result["last_wall_ns"] / 1e9
                else:
                    result["records"] = sum(
                        len(f[k]) for k in result["datasets"] if hasattr(f[k], "__len__")
                    )
        except Exception as exc:
            result["read_error"] = str(exc)

        return result

    def export_segment(
        self,
        start_ts: float | None = None,
        end_ts: float | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Export a bounded time window of telemetry records.

        Args:
            start_ts: Start UTC timestamp in seconds (inclusive). None = earliest.
            end_ts:   End UTC timestamp in seconds (inclusive). None = now.
            limit:    Maximum records to return; hard-capped at MAX_EXPORT_RECORDS.

        Returns a dict with 'records' (list of dicts), 'count', and query metadata.
        """
        if not _HAS_H5PY:
            return {"error": "h5py unavailable", "records": []}
        if not HDF5_PATH.exists():
            return {"error": "HDF5 file not found", "records": []}

        limit = min(max(1, limit), MAX_EXPORT_RECORDS)
        end_ts = end_ts or time.time()
        start_ns = int(start_ts * 1e9) if start_ts is not None else 0
        end_ns = int(end_ts * 1e9)

        records: list[dict[str, Any]] = []
        try:
            with h5py.File(HDF5_PATH, "r", swmr=True) as f:
                if "payloads" not in f:
                    return {"error": "no 'payloads' dataset in HDF5 file", "records": []}
                ds = f["payloads"]
                for row in ds:
                    if len(records) >= limit:
                        break
                    wns = int(row["wall_ns"])
                    if wns < start_ns:
                        continue
                    if wns > end_ns:
                        break
                    entry: dict[str, Any] = {
                        "wall_ns": wns,
                        "wall_ts": wns / 1e9,
                        "sha256": _coerce(row["sha256"]),
                    }
                    raw = row["payload"]
                    payload_bytes = raw if isinstance(raw, (bytes, bytearray)) else bytes(raw)
                    try:
                        entry["payload"] = json.loads(payload_bytes)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        entry["payload"] = _coerce(payload_bytes)
                    records.append(entry)
        except Exception as exc:
            return {"error": str(exc), "records": records}

        return {
            "records": records,
            "count": len(records),
            "limit": limit,
            "start_ts": start_ts,
            "end_ts": end_ts,
        }
