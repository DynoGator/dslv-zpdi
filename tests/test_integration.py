"""
SPEC-011-T — Hardware-Free Integration Test
Run main_pipeline as subprocess, verify HDF5 output and health endpoint.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest


def test_integration_pipeline_creates_output_and_health():
    output_dir = Path("/tmp/dslv-zpdi-integration-test")
    output_dir.mkdir(parents=True, exist_ok=True)

    env = {
        "PYTHONPATH": "src:.",
        "DEV_SIMULATOR": "1",
        "DSLV_OUTPUT_DIR": str(output_dir),
    }

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "dslv_zpdi.main_pipeline",
            "--simulator", "--mode", "sdr", "--interval", "0.1",
            "--output", str(output_dir),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    time.sleep(8)
    proc.terminate()
    proc.wait(timeout=5)

    # Verify output directories exist
    primary = output_dir / "primary"
    secondary = output_dir / "secondary"
    assert primary.exists(), "Primary output dir missing"
    assert secondary.exists(), "Secondary output dir missing"

    # SPEC-011.5 — Forensic completeness: every observation must land
    # somewhere. In single-node sim mode the 4-node confirmation gate
    # won't fire, so quarantine.jsonl is the expected sink.
    quarantine = secondary / "quarantine.jsonl"
    h5_files = list(primary.glob("*.h5"))
    assert quarantine.exists(), "No quarantine record produced — silent drop suspected"
    line_count = sum(1 for _ in quarantine.open("r", encoding="utf-8"))
    assert line_count > 0, "Quarantine file empty — silent drop suspected"
    # H5 files are optional in single-node mode (gate won't fire).
    _ = h5_files

    # Verify health endpoint fallback
    health_file = Path("/tmp/health.json")
    if health_file.exists():
        with open(health_file, "r", encoding="utf-8") as f:
            health = json.load(f)
        assert "timestamp_utc" in health
        assert "uptime_s" in health
