#!/usr/bin/env python3
"""
SPEC-009.1 — Field baseline capture script (Rev 4.4.0).
72 h passive ingest; scorer.finalize_baseline() on exit.
Logs to secondary only until baseline LOCKED.
"""

import argparse
import json
import logging
import os
import signal
import sys
import time

from dslv_zpdi.layer1_ingestion.hal_factory import get_hal
from dslv_zpdi.layer2_core.coherence import CoherenceScorer
from dslv_zpdi.layer3_telemetry.hdf5_writer import HDF5Writer
from dslv_zpdi.watchdog.timing_monitor import TimingMonitor

BASELINE_PATH = "/var/lib/dslv_zpdi/baseline.json"
LOG_PATH = "/var/log/dslv_zpdi_baseline.log"


def _setup_logging() -> logging.Logger:
    """SPEC-009.1 — Dual-stream logging for field baseline."""
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    logger = logging.getLogger("dslv-zpdi.baseline")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )
    fh = logging.FileHandler(LOG_PATH)
    fh.setFormatter(formatter)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def main():
    """SPEC-009.1 — Capture 72 h passive baseline."""
    parser = argparse.ArgumentParser(description="DSLV-ZPDI Baseline Capture")
    parser.add_argument("--simulator", action="store_true", help="Force simulated HAL")
    args = parser.parse_args()

    logger = _setup_logging()
    os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)

    hal = get_hal(simulator=args.simulator or os.getenv("DEV_SIMULATOR") == "1")
    scorer = CoherenceScorer(baseline_state_path=BASELINE_PATH)
    writer = HDF5Writer()
    monitor = TimingMonitor()
    monitor.start()

    scorer.start_baseline()
    logger.info("[BASELINE] 72 h capture started. Press Ctrl+C to finalize early.")

    running = True
    loop_count = 0
    last_status_time = time.time()

    # SPEC-011
    def _sig_handler(_signum, _frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    try:
        while running:
            loop_count += 1
            try:
                payload = hal.ingest_sdr()
            except Exception as e:
                logger.error("HAL ingest_sdr() failed: %s", e)
                time.sleep(1.0)
                continue

            if (
                monitor.healthy
                and payload.trust_state != "SECONDARY_QUARANTINED"
            ):
                json_payload = payload.to_json()
                decision = writer.ingest(json_payload)
                # Only primary writes after LOCKED; secondary logging is automatic
                if payload.extracted_phases:
                    scorer.update(json.loads(json_payload), payload.extracted_phases)

                if decision.stream == "PRIMARY" and scorer._baseline_state.value == "LOCKED":
                    logger.info("PRIMARY write accepted (baseline LOCKED).")

            # Emit heartbeat every 60 s
            if time.time() - last_status_time >= 60.0:
                status = scorer.get_baseline_status()
                logger.info(
                    "[HEARTBEAT] loops=%d baseline_state=%s samples=%d healthy=%s",
                    loop_count,
                    status["baseline_state"],
                    status["samples"],
                    monitor.healthy,
                )
                last_status_time = time.time()

            time.sleep(0.5)
    finally:
        monitor.stop()
        writer.close()
        scorer.finalize_baseline(force=True)
        logger.info("[BASELINE] Finalized. State: %s", scorer.get_baseline_status())


if __name__ == "__main__":
    main()
