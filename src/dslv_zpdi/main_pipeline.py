"""
SPEC-011 — Production pipeline loop (Rev 4.5.1).
Top-level integration: HAL → Coherence → HDF5 persistence.
"""

import argparse
import json
import os
import signal
import time
from pathlib import Path

from dslv_zpdi.layer1_ingestion.hal_factory import get_hal
from dslv_zpdi.layer2_core.wiring import coherence_engine as scorer
from dslv_zpdi.layer3_telemetry.hdf5_writer import HDF5Writer
from dslv_zpdi.watchdog.timing_monitor import TimingMonitor


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
    args = parser.parse_args()

    simulator_mode = _resolve_simulator(args)
    hal = get_hal(simulator=simulator_mode)

    out_base = Path(args.output).resolve()
    writer = HDF5Writer(
        output_path=str(out_base / "primary"),
        secondary_path=str(out_base / "secondary"),
    )

    # SPEC-004A.3 — Relaxed threshold in simulator mode (NTP jitter ~3ms, not GPSDO).
    _timing_threshold = 10_000_000 if simulator_mode else 50_000
    monitor = TimingMonitor(jitter_threshold_ns=_timing_threshold)
    monitor.start()

    # DSLV_SIM_DEMO=1: rotate node IDs so the 4-node confirmation gate can fire in sim.
    demo_nodes = None
    if simulator_mode and os.getenv("DSLV_SIM_DEMO", "").strip().lower() in _SIM_TRUE_TOKENS:
        demo_nodes = ["SIM-ALPHA", "SIM-BETA", "SIM-GAMMA", "SIM-DELTA"]
        print("[SIM-DEMO] Rotating node IDs across", demo_nodes)

    if args.field:
        scorer.start_baseline()
        print("[FIELD] Baseline capture started. Run for 72 h.")

    running = True

    def _sig_handler(_signum, _frame):
        """SPEC-011.1 — Graceful shutdown on SIGINT/SIGTERM."""
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    tick = 0
    primary_events = 0
    last_status_at = 0.0
    try:
        while running:
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

            if (
                monitor.healthy
                and payload.trust_state != "SECONDARY_QUARANTINED"
            ):
                decision = writer.ingest(payload.to_json())
                if decision.stream == "PRIMARY":
                    primary_events += 1
                    print(
                        f"[EVENT] PRIMARY {decision.packet.event_window_id} "
                        f"r_smooth={decision.packet.r_smooth:.4f} "
                        f"nodes={decision.packet.node_id}"
                    )

            tick += 1
            now = time.time()
            if now - last_status_at >= 60.0:
                stats = writer.get_stats()
                bl = scorer.get_baseline_status()
                print(
                    f"[STATUS] ticks={tick} primary={primary_events} "
                    f"stats={json.dumps(stats)} baseline={json.dumps(bl)}"
                )
                last_status_at = now

            # Demo mode sleeps shorter so the 4-node rotation fits inside the
            # 300 ms confirmation window (SPEC-006.4).
            time.sleep(0.05 if demo_nodes else 0.1)
    finally:
        monitor.stop()
        writer.close()
        if args.field:
            scorer.finalize_baseline(force=True)
            print("[FIELD] Baseline finalized.")


if __name__ == "__main__":
    main()
