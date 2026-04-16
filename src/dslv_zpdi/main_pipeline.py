"""
SPEC-011 — Production pipeline loop (Rev 4.4.0).
Top-level integration: HAL → Coherence → HDF5 persistence.
"""

import argparse
import json
import os
import signal
import sys
import time

from dslv_zpdi.layer1_ingestion.hal_factory import get_hal
from dslv_zpdi.layer2_core.coherence import CoherenceScorer
from dslv_zpdi.layer3_telemetry.hdf5_writer import HDF5Writer
from dslv_zpdi.watchdog.timing_monitor import TimingMonitor


def main():
    """SPEC-011.1 — Run the production data pipeline."""
    parser = argparse.ArgumentParser(description="DSLV-ZPDI Production Pipeline")
    parser.add_argument(
        "--field", action="store_true", help="72 h baseline capture mode"
    )
    parser.add_argument(
        "--simulator", action="store_true", help="Force simulated HAL"
    )
    parser.add_argument(
        "--mode",
        choices=["sdr", "pps", "alternate"],
        default="sdr",
        help="Ingestion mode",
    )
    args = parser.parse_args()

    hal = get_hal(simulator=args.simulator or os.getenv("DEV_SIMULATOR") == "1")
    scorer = CoherenceScorer(
        baseline_state_path="/var/lib/dslv_zpdi/baseline.json"
    )
    writer = HDF5Writer()
    monitor = TimingMonitor()  # SPEC-004A.3 thread
    monitor.start()

    if args.field:
        scorer.start_baseline()
        print("[FIELD] Baseline capture started. Run for 72 h.")

    running = True

    # SPEC-011
    def _sig_handler(_signum, _frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    try:
        while running:
            if args.mode == "sdr":
                payload = hal.ingest_sdr()
            elif args.mode == "pps":
                payload = hal.ingest_gps_pps()
            else:
                payload = (
                    hal.ingest_sdr()
                    if int(time.time()) % 2 == 0
                    else hal.ingest_gps_pps()
                )

            if (
                monitor.healthy
                and payload.trust_state != "SECONDARY_QUARANTINED"
            ):
                json_payload = payload.to_json()
                decision = writer.ingest(json_payload)
                if payload.extracted_phases:
                    scorer.update(json.loads(json_payload), payload.extracted_phases)

            time.sleep(0.1)
    finally:
        monitor.stop()
        writer.close()
        if args.field:
            scorer.finalize_baseline(force=True)
            print("[FIELD] Baseline finalized.")


if __name__ == "__main__":
    main()
