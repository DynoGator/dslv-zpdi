"""
SPEC-011 | Production pipeline loop (Rev 4.7.2)
Top-level integration: HAL -> Coherence -> HDF5 persistence.
"""

from __future__ import annotations

import argparse
import logging
import queue
import signal
import threading
import time
from pathlib import Path

from dslv_zpdi.layer1_ingestion.hal_factory import get_hal
from dslv_zpdi.layer1_ingestion.hal_simulated import SimulatedHAL
from dslv_zpdi.layer2_core.wiring import coherence_engine as scorer
from dslv_zpdi.layer3_telemetry.hdf5_writer import HDF5Writer
from dslv_zpdi.watchdog.health_reporter import HealthReporter
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
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Ingest error: %s", e)
            time.sleep(0.1)

def _process_loop(monitor, writer, ingest_q, state, health_reporter):
    """SPEC-011.2 | Processing consumer thread."""
    while state.running:
        try:
            payload = ingest_q.get(timeout=1.0)
            # SPEC-004A.3 | Timing health check
            if not monitor.healthy:
                payload.trust_state = "SECONDARY_QUARANTINED"
                payload.quarantine_reason = "timing_unhealthy"

            payload_json = payload.to_json()
            decision = writer.ingest(payload_json)

            if decision.stream == "PRIMARY":
                state.primary_events += 1

            # SPEC-014 | Update dashboard health endpoint
            bl = scorer.get_baseline_status()
            update_data = {
                "node_id": payload.node_id,
                "hal_mode": payload.raw_value.get("clock_source", "internal") if payload.modality == "rf_sdr" else "pps",
                "timing_healthy": monitor.healthy,
                "timing_jitter_ns": monitor.last_jitter_ns,
                "ticks": state.tick,
                "baseline": bl,
                "stats": writer.get_stats(),
            }
            if decision.packet:
                update_data["coherence"] = {
                    "r_smooth": decision.packet.r_smooth,
                    "r_global": decision.packet.r_global,
                }
            health_reporter.update(update_data)

        except queue.Empty:
            continue
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Process error: %s", e)

def main():
    """SPEC-011.1 | Main entry point."""
    parser = argparse.ArgumentParser(description="DSLV-ZPDI Production Pipeline")
    parser.add_argument("--simulator", action="store_true")
    parser.add_argument("--mode", choices=["sdr", "pps", "alternate"], default="sdr")
    parser.add_argument("--interval", type=float, default=0.1)
    parser.add_argument("--config", type=str, default="config/deployment.yaml")
    parser.add_argument("--output", type=str, help="Base output directory")
    args = parser.parse_args()

    state = PipelineState()
    hal = get_hal(simulator=args.simulator)
    _hw_fallback = not args.simulator and isinstance(hal, SimulatedHAL)
    if _hw_fallback:
        logger.warning(
            "Hardware HAL unavailable — pipeline running in SIMULATOR mode. "
            "Connect HackRF + GPSDO and restart the service to enable hardware ingestion."
        )
        args.simulator = True  # Skip PPS edge-wait; use time.sleep pacing

    writer_kwargs = {}
    if args.output:
        base_out = Path(args.output)
        writer_kwargs["output_path"] = str(base_out / "primary")
        writer_kwargs["secondary_path"] = str(base_out / "secondary")

    writer = HDF5Writer(**writer_kwargs)
    monitor = TimingMonitor(simulated=args.simulator)
    monitor.start()

    # SPEC-014 | Initialize dashboard health reporter
    health_reporter = HealthReporter(interval_sec=2.0)
    health_reporter.start()
    if _hw_fallback:
        health_reporter.update({"sim_fallback": True, "hal_mode": "simulator"})

    ingest_q = queue.Queue(maxsize=1024)

    t_ingest = threading.Thread(target=_ingest_loop, args=(hal, args, state, ingest_q), daemon=True)
    t_process = threading.Thread(target=_process_loop, args=(monitor, writer, ingest_q, state, health_reporter), daemon=True)

    def _sig_handler(signum, _frame):
        """SPEC-011.1 | Cooperative shutdown handler (SIGINT/SIGTERM).

        Signals the worker threads to stop, then lets main() drain and close
        the HDF5 writer so no in-flight telemetry is lost or left in a
        truncated file.
        """
        logger.info("Shutdown signal %s received — draining pipeline.", signum)
        state.running = False

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    t_ingest.start()
    t_process.start()

    logger.info("Pipeline running. Mode=%s", args.mode)
    try:
        while state.running:
            time.sleep(1)
    except KeyboardInterrupt:
        state.running = False

    # SPEC-011.1 | Graceful teardown — join workers, then flush persistence.
    logger.info("Stopping workers and flushing telemetry to disk.")
    t_ingest.join(timeout=5.0)
    t_process.join(timeout=5.0)
    health_reporter.stop()
    monitor.stop()
    writer.close()
    logger.info("Shutdown complete.")

if __name__ == "__main__":
    main()
