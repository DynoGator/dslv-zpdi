"""
SPEC-011.CLI-PROBE — `dslv-zpdi-probe` hardware discovery CLI.

Read-only by default. Discovers IIO contexts and reports device identity.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dslv_zpdi import __version__
from dslv_zpdi.layer1_ingestion.sdr.pluto_iio import PlutoIioBackend


def _discover() -> dict:
    """SPEC-011.CLI-PROBE — Return discovered IIO context URIs without opening a device."""
    try:
        import iio  # pylint: disable=import-outside-toplevel

        contexts = iio.scan_contexts()
    except Exception as exc:  # pylint: disable=broad-except
        return {"iio_available": False, "error": str(exc), "contexts": {}}
    return {
        "iio_available": True,
        "context_count": len(contexts),
        "contexts": {uri: attrs for uri, attrs in contexts.items()},
    }


def _probe_uri(uri: str) -> dict:
    """SPEC-011.CLI-PROBE — Open a specific URI and return capabilities."""
    try:
        backend = PlutoIioBackend(uri=uri)
        caps = backend.discover()
        backend.close()
        return {"success": True, "capabilities": caps.summary()}
    except Exception as exc:  # pylint: disable=broad-except
        return {"success": False, "error": str(exc)}


def probe_main(argv: list[str] | None = None) -> int:
    """SPEC-011.CLI-PROBE — Entry point for dslv-zpdi-probe."""
    parser = argparse.ArgumentParser(
        prog="dslv-zpdi-probe",
        description="Discover and probe Pluto-family SDR hardware.",
    )
    parser.add_argument("--version", action="version", version=f"dslv-zpdi {__version__}")
    parser.add_argument("--discover", action="store_true", help="List discovered IIO contexts")
    parser.add_argument("--uri", default="auto", help="libiio URI to probe")
    parser.add_argument("--json", help="Write JSON report to this path")
    args = parser.parse_args(argv)

    if args.discover:
        report = {"mode": "discover", **_discover()}
    else:
        report = {"mode": "probe", "uri": args.uri, **_probe_uri(args.uri)}

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"Report written to {args.json}")
    else:
        print(json.dumps(report, indent=2, sort_keys=True))

    return 0 if report.get("success", True) else 1
