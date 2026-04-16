#!/usr/bin/env python3
"""
SPEC-009.1 — Field baseline capture script (Rev 4.4.0).
72 h passive ingest; scorer.finalize_baseline() on exit.
"""

import argparse
import os
import signal
import sys
import time

from dslv_zpdi.layer1_ingestion.hal_factory import get_hal
from dslv_zpdi.layer2_core.coherence import CoherenceScorer
from dslv_zpdi.layer3_telemetry.hdf5_writer import HDF5Writer
from dslv_zpdi.watchdog.timing_monitor import TimingMonitor

BASELINE_PATH = "/var/lib/dslv_zpdi/baseline.json"


def main():
    """SPEC-009.1 — Capture 72 h passive baseline."""
    parser = argparse.ArgumentParser(description="DSLV-ZPDI Baseline Capture")
    parser.add_argument("--simulator", action="store_true", help="Force simulated HAL")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)
    hal = get_hal(simulator=args.simulator or os.getenv("DEV_SIMULATOR") == "1")
    scorer = CoherenceScorer(baseline_state_path=BASELINE_PATH)
    writer = HDF5Writer()
    monitor = TimingMonitor()
    monitor.start()

    scorer.start_baseline()
    print("[BASELINE] 72 h capture started. Press Ctrl+C to finalize early.")

    running = True

    def _sig_handler(_signum, _frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    try:
        while running:
            payload = hal.ingest_sdr()
            if (
                monitor.healthy
                and payload.trust_state != "SECONDARY_QUARANTINED"
            ):
                json_payload = payload.to_json()
                writer.ingest(json_payload)
                if payload.extracted_phases:
                    scorer.update(json.loads(json_payload), payload.extracted_phases)
            time.sleep(0.5)
    finally:
        monitor.stop()
        writer.close()
        scorer.finalize_baseline(force=True)
        print("[BASELINE] Finalized. State:", scorer.get_baseline_status())


if __name__ == "__main__":
    main()
