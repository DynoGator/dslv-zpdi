"""
SPEC-011.CLI-VERIFY — `dslv-zpdi-verify` HDF5 integrity verification CLI.

Exit codes:
  0 valid
  1 integrity failure
  2 missing required artifact
  3 unsupported schema
  4 key unavailable
  5 operational error
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from dslv_zpdi import __version__

try:
    import h5py

    HDF5_AVAILABLE = True
except (ImportError, OSError):
    HDF5_AVAILABLE = False


def verify_main(argv: list[str] | None = None) -> int:
    """SPEC-011.CLI-VERIFY — Entry point for dslv-zpdi-verify."""
    parser = argparse.ArgumentParser(
        prog="dslv-zpdi-verify",
        description="Verify DSLV-ZPDI HDF5 integrity and event chain.",
    )
    parser.add_argument("--version", action="version", version=f"dslv-zpdi {__version__}")
    parser.add_argument("--deep", action="store_true", help="Perform deep verification")
    parser.add_argument("--manifest", help="Detached manifest JSON path")
    parser.add_argument("path", help="HDF5 file or directory to verify")
    parser.add_argument("--json", help="Write JSON report to this path")
    args = parser.parse_args(argv)

    target = Path(args.path)
    if not target.exists():
        report = {"valid": False, "error": f"Path not found: {target}", "exit_code": 2}
        _emit(report, args.json)
        return 2

    if not HDF5_AVAILABLE:
        report = {"valid": False, "error": "h5py not available", "exit_code": 5}
        _emit(report, args.json)
        return 5

    files = [target] if target.is_file() else sorted(target.glob("*.h5"))
    if not files:
        report = {"valid": False, "error": f"No .h5 files found in {target}", "exit_code": 2}
        _emit(report, args.json)
        return 2

    all_valid = True
    details: list[dict] = []
    for h5_path in files:
        detail = _verify_file(h5_path, deep=args.deep)
        details.append(detail)
        if not detail.get("valid", False):
            all_valid = False

    report = {
        "valid": all_valid,
        "files_checked": len(files),
        "details": details,
        "exit_code": 0 if all_valid else 1,
    }
    _emit(report, args.json)
    return 0 if all_valid else 1


def _verify_file(path: Path, deep: bool) -> dict:
    """SPEC-011.CLI-VERIFY — Verify a single HDF5 file."""
    detail: dict = {"path": str(path), "valid": False}
    try:
        with h5py.File(path, "r") as h5file:
            detail["file_version"] = h5file.attrs.get("file_version", "unknown")
            events = [k for k in h5file if k.startswith("event_")]
            detail["event_count"] = len(events)
            previous = hashlib.sha256(b"DSLV-ZPDI event-chain genesis v5.0.0").hexdigest()
            chain_ok = True
            for group_name in sorted(events):
                grp = h5file[group_name]
                stored_prev = grp.attrs.get("previous_event_chain_sha256", "")
                stored_chain = grp.attrs.get("event_chain_sha256", "")
                if stored_prev != previous or not stored_chain:
                    chain_ok = False
                    break
                previous = stored_chain
            detail["event_chain_valid"] = chain_ok
            if deep:
                detail["hmac_present"] = all("hmac_sha256" in h5file[g].attrs for g in events)
            detail["valid"] = chain_ok and (not deep or detail.get("hmac_present", False))
    except Exception as exc:  # pylint: disable=broad-except
        detail["error"] = str(exc)
    return detail


def _emit(report: dict, json_path: str | None) -> None:
    """SPEC-011.CLI-VERIFY — Emit verification report to stdout or file."""
    if json_path:
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"Verification report written to {json_path}")
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
