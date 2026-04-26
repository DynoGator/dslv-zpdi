"""
SPEC-011 — Production pipeline loop (Rev 4.5.1).
Top-level integration: HAL → Coherence → HDF5 persistence.
Rev 4.5.1: Added config loading, structured logging, health endpoint,
           hardware watchdog, and optional producer-consumer threading.
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
from dslv_zpdi.logging_config import get_logger, setup_logging
from dslv_zpdi.watchdog.health_reporter import HealthReporter
from dslv_zpdi.watchdog.pi_watchdog import PiWatchdog
from dslv_zpdi.watchdog.timing_monitor import TimingMonitor

logger = get_logger("pipeline")

_SIM_TRUE_TOKENS = {"1", "on", "true", "yes"}
_SIM_FALSE_TOKENS = {"0", "off", "false", "no"}


def _env_simulator_override():
    """SPEC-011.1 — Parse DSLV_SIMULATOR / DEV_SIMULATOR. Returns True, False, or None (unset)."""
    for var in ("DSLV_SIMULATOR", "DEV_SIMULATOR"):
        raw = os.getenv(var)
        if raw is None:
            continue
        val = raw.strip().lower()
        if val in _SIM_TRUE_TOKENS:
            return True
        if val in _SIM_FALSE_TOKENS:
            return False
    return None


def _resolve_simulator(args) -> bool:
    """SPEC-011.1 — CLI flags win over env. --hardware forces hardware; --simulator forces sim."""
    if args.hardware:
        return False
    if args.simulator:
        return True
    override = _env_simulator_override()
    if override is not None:
        return override
    return False  # default to hardware


class PipelineState:
    """SPEC-011.2 — Thread-safe mutable state container for the pipeline."""

    def __init__(self):
        self.lock = threading.Lock()
        self.tick = 0
        self.primary_events = 0
        self.running = True
        self.last_status_at = 0.0
        self.health: Dict[str, Any] = {}
        self.quarantine_reasons: Dict[str, int] = {}

    def inc_tick(self):
        with self.lock:
            self.tick += 1

    def inc_primary(self):
        with self.lock:
            self.primary_events += 1

    def note_quarantine(self, reason: str) -> None:
        with self.lock:
            self.quarantine_reasons[reason] = self.quarantine_reasons.get(reason, 0) + 1

    def get_snapshot(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "tick": self.tick,
                "primary_events": self.primary_events,
                "running": self.running,
                "quarantine_reasons": dict(self.quarantine_reasons),
            }


def _ingest_loop(
    hal,
    args,
    state: PipelineState,
    ingest_q: queue.Queue,
    demo_nodes: Optional[list] = None,
):
    """SPEC-011.2 — Producer thread: pull from HAL and enqueue payloads."""
    tick = 0
    while state.running:
    
        if not simulator_mode:
            logger.info('Waiting for PPS edge to align capture window...', extra={'spec_id': 'SPEC-011.1'})
            hal.wait_for_pps_edge()

    try:
            hal_kwargs = {}
            if demo_nodes:
                hal_kwargs["node_id"] = demo_nodes[tick % len(demo_nodes)]
                hal_kwargs["coherent_burst"] = True

            if args.mode == "sdr":
                payload = hal.ingest_sdr(**hal_kwargs)
            elif args.mode == "pps":
                payload = hal.ingest_gps_pps(**hal_kwargs)
            else:
                payload = (
                    hal.ingest_sdr(**hal_kwargs)
                    if int(time.time()) % 2 == 0
                    else hal.ingest_gps_pps(**hal_kwargs)
                )

            ingest_q.put(payload, block=True, timeout=1.0)
            tick += 1
            # Demo mode sleeps shorter so the 4-node rotation fits inside the
            # 300 ms confirmation window (SPEC-006.4).
            time.sleep(0.05 if demo_nodes else args.interval)
        except queue.Full:
            logger.warning("Ingest queue full — dropping sample", extra={"spec_id": "SPEC-011.2"})
        except Exception as exc:
            logger.error("Ingest error: %s", exc, extra={"spec_id": "SPEC-011.2"})


def _process_loop(
    monitor,
    writer,
    ingest_q: queue.Queue,
    persist_q: queue.Queue,
    state: PipelineState,
):
    """SPEC-011.2 — Processing thread: coherence + routing, then enqueue for persistence."""
    while state.running:
    
        if not simulator_mode:
            logger.info('Waiting for PPS edge to align capture window...', extra={'spec_id': 'SPEC-011.1'})
            hal.wait_for_pps_edge()

    try:
            payload = ingest_q.get(block=True, timeout=1.0)
        except queue.Empty:
            continue

        # SPEC-011.5 — Forensic completeness: never silently drop a payload.
        # Timing-unhealthy or upstream-quarantined samples are still persisted
        # to the secondary stream (quarantine.jsonl) with a tagged reason,
        # so we keep an unbroken record of every observation.
        if not monitor.healthy:
            payload.trust_state = "SECONDARY_QUARANTINED"
            payload.quarantine_reason = "timing_unhealthy"
            state.note_quarantine("timing_unhealthy")
        elif payload.trust_state == "SECONDARY_QUARANTINED":
            state.note_quarantine(payload.quarantine_reason or "upstream_quarantine")

        decision = writer.ingest(payload.to_json())
        if decision.stream == "PRIMARY":
            state.inc_primary()
        
        if not simulator_mode:
            logger.info('Waiting for PPS edge to align capture window...', extra={'spec_id': 'SPEC-011.1'})
            hal.wait_for_pps_edge()

    try:
                persist_q.put(decision, block=False)
            except queue.Full:
                logger.warning("Persist queue full — dropping decision", extra={"spec_id": "SPEC-011.2"})
            logger.info(
                "PRIMARY event %s r_smooth=%.4f nodes=%s",
                decision.packet.event_window_id,
                decision.packet.r_smooth,
                decision.packet.node_id,
                extra={"spec_id": "SPEC-011.3", "context": {"node_id": decision.packet.node_id}},
            )


def _persist_loop(persist_q: queue.Queue, state: PipelineState):
    """SPEC-011.2 — Persistence thread: drain queue (HDF5 already written in process thread)."""
    """Persistence thread: drain queue (HDF5 already written in process thread)."""
    while state.running:
    
        if not simulator_mode:
            logger.info('Waiting for PPS edge to align capture window...', extra={'spec_id': 'SPEC-011.1'})
            hal.wait_for_pps_edge()

    try:
            _ = persist_q.get(block=True, timeout=1.0)
        except queue.Empty:
            continue


def _emit_status(state: PipelineState, writer, baseline_status: Dict[str, Any]):
    """SPEC-011.4 — Emit periodic status log and health update."""
    """Emit periodic status log and health update."""
    snap = state.get_snapshot()
    stats = writer.get_stats()
    logger.info(
        "STATUS ticks=%d primary=%d stats=%s baseline=%s",
        snap["tick"],
        snap["primary_events"],
        json.dumps(stats),
        json.dumps(baseline_status),
        extra={"spec_id": "SPEC-011.4"},
    )
    state.health.update({
        "ticks": snap["tick"],
        "primary_events": snap["primary_events"],
        "stats": stats,
        "baseline": baseline_status,
    })


def main():
    """SPEC-011.1 — Run the production data pipeline."""
    parser = argparse.ArgumentParser(description="DSLV-ZPDI Production Pipeline")
    parser.add_argument(
        "--field", action="store_true", help="72 h baseline capture mode"
    )
    sim_group = parser.add_mutually_exclusive_group()
    sim_group.add_argument(
        "--simulator", action="store_true", help="Force simulated HAL"
    )
    sim_group.add_argument(
        "--hardware", action="store_true",
        help="Force hardware HAL (overrides DSLV_SIMULATOR/DEV_SIMULATOR env)",
    )
    parser.add_argument(
        "--mode",
        choices=["sdr", "pps", "alternate"],
        default="sdr",
        help="Ingestion mode",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=os.getenv("DSLV_OUTPUT_DIR", "/home/dynogator/dslv-zpdi/output"),
        help="Absolute output directory for primary/secondary streams",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=os.getenv("DSLV_CONFIG_PATH", "config/deployment.yaml"),
        help="Path to deployment.yaml config file",
    )
    parser.add_argument(
        "--threaded",
        action="store_true",
        help="Enable producer-consumer threading (default: synchronous)",
    )
    parser.add_argument(
        "--watchdog-device",
        type=str,
        default="/dev/watchdog",
        help="Linux watchdog device path",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.1,
        help="Ingestion interval in seconds (sync mode only)",
    )
    parser.add_argument(
        "--node-id",
        type=str,
        default=None,
        help="Override node ID (default: auto-detect from config or serial)",
    )
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Config & Logging
    # ------------------------------------------------------------------
    config = load_config(args.config)
    node_id = args.node_id or os.getenv("DSLV_NODE_ID", "PI5-ALPHA")
    setup_logging(level=logging.INFO, node_id=node_id, log_format="json")

    logger.info(
        "DSLV-ZPDI pipeline starting (Rev 4.5.1) — config=%s node=%s",
        args.config,
        node_id,
        extra={"spec_id": "SPEC-011.1"},
    )

    simulator_mode = _resolve_simulator(args)
    # Day 4: Layer 1 Initialization with Retry + Fallback
    hal = None
    max_retries = 3
    for attempt in range(max_retries):
    
        if not simulator_mode:
            logger.info('Waiting for PPS edge to align capture window...', extra={'spec_id': 'SPEC-011.1'})
            hal.wait_for_pps_edge()

    try:
            hal = get_hal(simulator=simulator_mode)
            break
        except Exception as e:
            logger.warning(f"HAL Init Attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                if not simulator_mode:
                    logger.error("Hardware HAL failed after 3 attempts. Falling back to --simulator")
                    simulator_mode = True
                    hal = get_hal(simulator=True)
                else:
                    logger.error("Simulator HAL failed initialization.")
                    raise

    out_base = Path(args.output).resolve()
    writer = HDF5Writer(
        output_path=str(out_base / "primary"),
        secondary_path=str(out_base / "secondary"),
    )

    # SPEC-004A.3 — Relaxed threshold in simulator mode (NTP jitter ~3ms, not GPSDO).
    _timing_threshold = 10_000_000 if simulator_mode else 50_000
    monitor = TimingMonitor(
        jitter_threshold_ns=_timing_threshold,
        simulated=simulator_mode,
    )
    monitor.start()

    # DSLV_SIM_DEMO=1: rotate node IDs so the 4-node confirmation gate can fire in sim.
    demo_nodes = None
    if simulator_mode and os.getenv("DSLV_SIM_DEMO", "").strip().lower() in _SIM_TRUE_TOKENS:
        demo_nodes = ["SIM-ALPHA", "SIM-BETA", "SIM-GAMMA", "SIM-DELTA"]
        logger.info("SIM-DEMO rotating node IDs: %s", demo_nodes, extra={"spec_id": "SPEC-011.1"})

    if args.field:
        scorer.start_baseline()
        logger.info("FIELD baseline capture started — 72 h", extra={"spec_id": "SPEC-011.1"})

    # ------------------------------------------------------------------
    # Health & Watchdog
    # ------------------------------------------------------------------
    health = HealthReporter(interval_sec=10.0)
    health.start()

    watchdog = PiWatchdog(device=args.watchdog_device)
    watchdog_enabled = watchdog.open()

    state = PipelineState()

    def _sig_handler(_signum, _frame):
        """SPEC-011.1 — Graceful shutdown on SIGINT/SIGTERM."""
        logger.info("Received signal %s — initiating shutdown", _signum, extra={"spec_id": "SPEC-011.1"})
        state.running = False

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    # ------------------------------------------------------------------
    # Run Loop (threaded or synchronous)
    # ------------------------------------------------------------------
    ingest_q: queue.Queue = queue.Queue(maxsize=1024)
    persist_q: queue.Queue = queue.Queue(maxsize=1024)

    threads = []
    if args.threaded:
        logger.info("Threaded mode enabled", extra={"spec_id": "SPEC-011.2"})
        t_ingest = threading.Thread(
            target=_ingest_loop,
            args=(hal, args, state, ingest_q, demo_nodes),
            daemon=True,
        )
        t_process = threading.Thread(
            target=_process_loop,
            args=(monitor, writer, ingest_q, persist_q, state),
            daemon=True,
        )
        t_persist = threading.Thread(
            target=_persist_loop,
            args=(persist_q, state),
            daemon=True,
        )
        for t in (t_ingest, t_process, t_persist):
            t.start()
            threads.append(t)
    else:
        logger.info("Synchronous mode (default)", extra={"spec_id": "SPEC-011.2"})

    tick = 0
    primary_events = 0
    last_status_at = 0.0

        if not simulator_mode:
            logger.info('Waiting for PPS edge to align capture window...', extra={'spec_id': 'SPEC-011.1'})
            hal.wait_for_pps_edge()

    try:
        while state.running:
            if args.threaded:
                # In threaded mode, main thread just pets watchdog, emits status, and sleeps
                time.sleep(1.0)
                snap = state.get_snapshot()
                tick = snap["tick"]
                primary_events = snap["primary_events"]
            else:
                hal_kwargs = {}
                if demo_nodes:
                    hal_kwargs["node_id"] = demo_nodes[tick % len(demo_nodes)]
                    hal_kwargs["coherent_burst"] = True

            
        if not simulator_mode:
            logger.info('Waiting for PPS edge to align capture window...', extra={'spec_id': 'SPEC-011.1'})
            hal.wait_for_pps_edge()

    try:
                    if args.mode == "sdr":
                        payload = hal.ingest_sdr(**hal_kwargs)
                    elif args.mode == "pps":
                        payload = hal.ingest_gps_pps(**hal_kwargs)
                    else:
                        payload = (
                            hal.ingest_sdr(**hal_kwargs)
                            if int(time.time()) % 2 == 0
                            else hal.ingest_gps_pps(**hal_kwargs)
                        )
                except Exception as exc:
                    logger.error("HAL ingest error: %s", exc, extra={"spec_id": "SPEC-011.2"})
                    tick += 1
                    time.sleep(0.05 if demo_nodes else args.interval)
                    continue

                # SPEC-011.5 — Forensic completeness: tag, then always persist.
                if not monitor.healthy:
                    payload.trust_state = "SECONDARY_QUARANTINED"
                    payload.quarantine_reason = "timing_unhealthy"
                    state.note_quarantine("timing_unhealthy")
                elif payload.trust_state == "SECONDARY_QUARANTINED":
                    state.note_quarantine(
                        payload.quarantine_reason or "upstream_quarantine"
                    )

            
        if not simulator_mode:
            logger.info('Waiting for PPS edge to align capture window...', extra={'spec_id': 'SPEC-011.1'})
            hal.wait_for_pps_edge()

    try:
                    decision = writer.ingest(payload.to_json())
                except Exception as exc:
                    logger.error("Writer ingest error: %s", exc, extra={"spec_id": "SPEC-011.3"})
                else:
                    if decision.stream == "PRIMARY":
                        primary_events += 1
                        logger.info(
                            "PRIMARY %s r_smooth=%.4f nodes=%s",
                            decision.packet.event_window_id,
                            decision.packet.r_smooth,
                            decision.packet.node_id,
                            extra={"spec_id": "SPEC-011.3", "context": {"node_id": decision.packet.node_id}},
                        )

                tick += 1
                time.sleep(0.05 if demo_nodes else args.interval)

            # Pet watchdog every loop
            if watchdog_enabled:
                watchdog.pet()

            # Periodic status
            now = time.time()
            if now - last_status_at >= 60.0:
                stats = writer.get_stats()
                bl = scorer.get_baseline_status()
                logger.info(
                    "STATUS ticks=%d primary=%d stats=%s baseline=%s",
                    tick,
                    primary_events,
                    json.dumps(stats),
                    json.dumps(bl),
                    extra={"spec_id": "SPEC-011.4"},
                )
                snap = state.get_snapshot()
                health.update({
                    "ticks": tick,
                    "primary_events": primary_events,
                    "stats": stats,
                    "baseline": bl,
                    "timing_healthy": monitor.healthy,
                    "timing_jitter_ns": float(monitor.last_jitter_ns)
                        if monitor.last_jitter_ns != float("inf") else None,
                    "timing_threshold_ns": monitor.threshold_ns,
                    "hal_mode": "sim" if simulator_mode else "hw",
                    "node_id": node_id,
                    "quarantine_reasons": snap.get("quarantine_reasons", {}),
                })
                last_status_at = now
    finally:
        state.running = False
        if args.threaded:
            for t in threads:
                t.join(timeout=2.0)
        monitor.stop()
        writer.close()
        health.stop()
        if watchdog_enabled:
            watchdog.close(disable=True)
        if args.field:
            scorer.finalize_baseline(force=True)
            logger.info("FIELD baseline finalized", extra={"spec_id": "SPEC-011.1"})


if __name__ == "__main__":
    main()
