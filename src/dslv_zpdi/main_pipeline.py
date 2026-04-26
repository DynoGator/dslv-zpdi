"""
SPEC-011 | Production pipeline loop (Rev 4.6.0)
Top-level integration: HAL -> Coherence -> HDF5 persistence.
"""

import argparse
import json
import logging
import os
import queue
import signal
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from dslv_zpdi.config_loader import load_config
from dslv_zpdi.layer1_ingestion.hal_factory import get_hal
from dslv_zpdi.layer2_core.wiring import coherence_engine as scorer
from dslv_zpdi.layer3_telemetry.hdf5_writer import HDF5Writer
from dslv_zpdi.watchdog.health_reporter import HealthReporter
from dslv_zpdi.watchdog.pi_watchdog import PiWatchdog
from dslv_zpdi.watchdog.timing_monitor import TimingMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pipeline")

class PipelineState:
    """SPEC-011.2 | Thread-safe state container."""
    def __init__(self):
        """SPEC-011.2 | Initialize state."""
        self.running = True
        self.tick = 0
        self.primary_events = 0
        self.quarantine_reasons = {}

def _ingest_loop(hal, args, state, ingest_q):
    """SPEC-011.2 | Ingestion producer thread."""
    while state.running:
        try:
            # SPEC-004A.4-SYNC | PPS-edge alignment
            if not args.simulator:
                hal.wait_for_pps_edge()

            if args.mode == "sdr":
                payload = hal.ingest_sdr()
            elif args.mode == "pps":
                payload = hal.ingest_gps_pps()
            else:
                payload = hal.ingest_sdr() if int(time.time()) % 2 == 0 else hal.ingest_gps_pps()

            ingest_q.put(payload, timeout=1.0)
            state.tick += 1
            if args.simulator:
                time.sleep(args.interval)
        except Exception as e:
            logger.error(f"Ingest error: {e}")
            time.sleep(0.1)

def _process_loop(monitor, writer, ingest_q, state):
    """SPEC-011.2 | Processing consumer thread."""
    while state.running:
        try:
            payload = ingest_q.get(timeout=1.0)
            # SPEC-004A.3 | Timing health check
            if not monitor.healthy:
                payload.trust_state = "SECONDARY_QUARANTINED"
                payload.quarantine_reason = "timing_unhealthy"
            
            decision = writer.ingest(payload.to_json())
            if decision.stream == "PRIMARY":
                state.primary_events += 1
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Process error: {e}")

def main():
    """SPEC-011.1 | Main entry point."""
    parser = argparse.ArgumentParser(description="DSLV-ZPDI Production Pipeline")
    parser.add_argument("--simulator", action="store_true")
    parser.add_argument("--mode", choices=["sdr", "pps", "alternate"], default="sdr")
    parser.add_argument("--interval", type=float, default=0.1)
    parser.add_argument("--config", type=str, default="config/deployment.yaml")
    args = parser.parse_args()

    state = PipelineState()
    hal = get_hal(simulator=args.simulator)
    writer = HDF5Writer()
    monitor = TimingMonitor(simulated=args.simulator)
    monitor.start()

    def _sig_handler(_signum, _frame):
        """SPEC-011.1 | Shutdown handler."""
        state.running = False
        logger.info("Shutdown initiated.")
        os._exit(0)

    signal.signal(signal.SIGINT, _sig_handler)

    ingest_q = queue.Queue(maxsize=1024)

    t_ingest = threading.Thread(target=_ingest_loop, args=(hal, args, state, ingest_q), daemon=True)
    t_process = threading.Thread(target=_process_loop, args=(monitor, writer, ingest_q, state), daemon=True)

    t_ingest.start()
    t_process.start()

    logger.info(f"Pipeline running. Mode={args.mode}")
    while state.running:
        time.sleep(1)

if __name__ == "__main__":
    main()
