"""
SPEC-011.CLI-PREFLIGHT — `dslv-zpdi-preflight` unified preflight command.

Checks host environment, timing authority, SDR backend, and trust configuration.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dslv_zpdi import __version__
from dslv_zpdi.config_models import NodeProfile
from dslv_zpdi.layer1_ingestion.hal_factory import get_tier1_hal


def preflight_main(argv: list[str] | None = None) -> int:
    """SPEC-011.CLI-PREFLIGHT — Entry point for dslv-zpdi-preflight."""
    parser = argparse.ArgumentParser(
        prog="dslv-zpdi-preflight",
        description="Run Tier-1 deployment preflight checks.",
    )
    parser.add_argument("--version", action="version", version=f"dslv-zpdi {__version__}")
    parser.add_argument("--profile", required=True, help="Node profile YAML path")
    parser.add_argument(
        "--strict", action="store_true", help="Fail if any mandatory check is not PASS"
    )
    parser.add_argument("--simulator", action="store_true", help="Force simulator backend")
    parser.add_argument("--json", help="Write JSON report to this path")
    args = parser.parse_args(argv)

    report: dict = {"version": __version__, "profile": args.profile, "checks": []}
    ok = True

    try:
        profile = NodeProfile.from_yaml(args.profile)
        report["profile_id"] = profile.identity.profile_id
        report["checks"].append({"name": "profile_load", "status": "PASS"})
    except Exception as exc:  # pylint: disable=broad-except
        report["checks"].append({"name": "profile_load", "status": "FAIL", "message": str(exc)})
        ok = False
        _emit(report, args.json)
        return 1 if args.strict else 0

    try:
        hal = get_tier1_hal(profile, simulator=args.simulator)
        report["checks"].append({"name": "hal_initialization", "status": "PASS"})
    except Exception as exc:  # pylint: disable=broad-except
        report["checks"].append(
            {"name": "hal_initialization", "status": "FAIL", "message": str(exc)}
        )
        ok = False
        _emit(report, args.json)
        return 1 if args.strict else 0

    try:
        timing = hal.timing_authority.attest()
        report["timing_attestation"] = timing.summary()
        report["checks"].append({"name": "timing_attestation", "status": "PASS"})
        report["checks"].append(
            {
                "name": "gps_fix",
                "status": "PASS" if timing.gps_fix_valid else "FAIL",
                "message": "GPS fix valid" if timing.gps_fix_valid else "No GPS fix",
            }
        )
        report["checks"].append(
            {
                "name": "pps_health",
                "status": "PASS" if timing.pps_present else "FAIL",
                "message": f"PPS present={timing.pps_present}, jitter={timing.pps_rms_jitter_ns:.0f} ns",
            }
        )
        if not timing.gps_fix_valid or not timing.pps_present:
            ok = False
    except Exception as exc:  # pylint: disable=broad-except
        report["checks"].append(
            {"name": "timing_attestation", "status": "FAIL", "message": str(exc)}
        )
        ok = False

    try:
        health = hal.sdr_backend.health()
        caps = hal.sdr_backend.discover()
        report["sdr_health"] = health.summary()
        report["sdr_capabilities"] = caps.summary()
        report["checks"].append({"name": "sdr_backend", "status": "PASS"})
    except Exception as exc:  # pylint: disable=broad-except
        report["checks"].append({"name": "sdr_backend", "status": "FAIL", "message": str(exc)})
        ok = False

    try:
        hal.close()
        report["checks"].append({"name": "hal_close", "status": "PASS"})
    except Exception as exc:  # pylint: disable=broad-except
        report["checks"].append({"name": "hal_close", "status": "FAIL", "message": str(exc)})

    report["overall"] = "PASS" if ok else "FAIL"
    _emit(report, args.json)
    return 0 if ok else (1 if args.strict else 0)


def _emit(report: dict, json_path: str | None) -> None:
    """SPEC-011.CLI-PREFLIGHT — Emit preflight report to stdout or file."""
    if json_path:
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"Preflight report written to {json_path}")
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
