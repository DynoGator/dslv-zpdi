import json
import os
import tempfile
import time
import uuid

from src.layer2_core.coherence import CoherenceScorer
from src.layer3_telemetry.router import DualStreamRouter


def test_baseline_lifecycle_and_persistence():
    with tempfile.TemporaryDirectory() as td:
        state_path = os.path.join(td, "baseline.json")
        scorer = CoherenceScorer(
            baseline_state_path=state_path,
            min_baseline_samples=10,
            baseline_duration_hours=72,
        )
        scorer.start_baseline(started_utc=time.time() - (73 * 3600))
        for i in range(20):
            scorer.update_baseline(0.05 + (i * 0.002), time.time())
        threshold = scorer.finalize_baseline(force=True)
        assert scorer.get_baseline_status()["ready"] is True
        assert threshold is not None and threshold > 0.0
        assert os.path.exists(state_path)

        scorer2 = CoherenceScorer(baseline_state_path=state_path)
        status2 = scorer2.get_baseline_status()
        assert status2["ready"] is True
        assert status2["threshold"] == threshold


def test_router_blocks_primary_during_baseline_learning():
    from src.layer2_core.wiring import coherence_engine

    coherence_engine.start_baseline()

    payload = {
        "node_id": "BASELINE-NODE",
        "sensor_id": "S1",
        "payload_uuid": str(uuid.uuid4()),
        "timestamp_utc": time.time(),
        "modality": "rf_sdr",
        "trust_state": "CAL_TRUSTED",
        "extracted_phases": [0.1] * 64,
    }
    router = DualStreamRouter()
    decision = router.route(json.dumps(payload))

    coherence_engine.finalize_baseline(force=True)  # cleanup

    assert decision.stream == "SECONDARY"
    assert decision.reason in {
        "baseline_learning_active",
        "wiring_rejected",
        "below_adaptive_threshold",
    }
