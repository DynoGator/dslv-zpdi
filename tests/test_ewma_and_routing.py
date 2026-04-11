"""Tests for EWMA smoothing (SPEC-006 Section 5.5.3),
weighted global R(t) (SPEC-006 Section 5.5.2),
and two-stream routing enforcement (SPEC-003/SPEC-007)."""

import json
import time
import uuid

from dslv_zpdi.core.states import RouteStream, TrustState
from dslv_zpdi.layer2_core.coherence import CoherenceScorer
from dslv_zpdi.layer3_telemetry.router import DualStreamRouter


def test_ewma_smoothing_dampens_spikes():
    """SPEC-006 Section 5.5.3: r_smooth uses EWMA with alpha=0.2."""
    scorer = CoherenceScorer(alpha=0.2)
    phases_zero = [0.0, 3.14159] * 50  # ~0 coherence
    phases_one = [0.0] * 100  # ~1.0 coherence

    # Feed zero-coherence first to establish baseline
    for _ in range(5):
        pkt = scorer.update({"node_id": "A", "timestamp_utc": time.time()}, phases_zero)
    assert pkt.r_smooth < 0.05  # r_smooth should be near 0

    # Spike to perfect coherence — r_smooth should NOT jump to 1.0
    pkt = scorer.update({"node_id": "A", "timestamp_utc": time.time()}, phases_one)
    assert pkt.r_local > 0.99  # r_local IS high
    assert pkt.r_smooth < 0.5  # r_smooth is dampened by EWMA


def test_ewma_converges_over_multiple_updates():
    """SPEC-006: EWMA converges toward r_local over repeated identical inputs."""
    scorer = CoherenceScorer(alpha=0.2)
    phases = [0.0] * 100  # r_local ≈ 1.0

    for i in range(30):
        pkt = scorer.update({"node_id": "A", "timestamp_utc": float(i)}, phases)

    # After 30 updates of r=1.0, EWMA should have converged close to 1.0
    assert pkt.r_smooth > 0.95


def test_global_r_weighted_by_modality():
    """SPEC-006 Section 5.5.2: RF nodes weighted 3x vs others."""
    scorer = CoherenceScorer()

    # Two nodes: one RF (w=3), one thermal (w=1), both at r=0.8
    scorer.fleet_state["RF-01"] = {
        "r_smooth": 0.8, "mean_phase": 0.0, "modality": "rf_sdr", "ts": 0,
    }
    scorer.fleet_state["THERM-01"] = {
        "r_smooth": 0.8, "mean_phase": 0.0, "modality": "thermal", "ts": 0,
    }

    # Same r_smooth, same phase → weighted average should still be 0.8
    r_global = scorer.compute_global_r()
    assert abs(r_global - 0.8) < 0.001

    # Different r_smooth values: RF=0.9, thermal=0.3
    scorer.fleet_state["RF-01"]["r_smooth"] = 0.9
    scorer.fleet_state["THERM-01"]["r_smooth"] = 0.3

    r_global = scorer.compute_global_r()
    # Expected: (3*0.9 + 1*0.3) / (3+1) = 3.0 / 4 = 0.75
    assert abs(r_global - 0.75) < 0.001


def test_router_only_two_streams():
    """SPEC-003/SPEC-007: Router must return only PRIMARY or SECONDARY."""
    from dslv_zpdi.layer2_core.wiring import coherence_engine
    coherence_engine.finalize_baseline(force=True)  # Ensure baseline is locked

    router = DualStreamRouter()

    # Craft a valid CAL_TRUSTED payload with low r_smooth
    payload = {
        "node_id": "N1", "sensor_id": "S1", "modality": "rf_sdr",
        "payload_uuid": str(uuid.uuid4()), "timestamp_utc": time.time(),
        "trust_state": TrustState.CAL_TRUSTED.value,
        "extracted_phases": [0.5, 1.5, 2.5, 3.5] * 10,
    }

    decision = router.route(json.dumps(payload))
    assert decision.stream in (RouteStream.PRIMARY.value, RouteStream.SECONDARY.value)
    # No third stream allowed
    assert decision.stream != "PRIMARY_CANDIDATE"


def test_structured_background_routes_to_secondary():
    """SPEC-003: Packets with 0.15 <= r_smooth < 0.40 route to SECONDARY."""
    from dslv_zpdi.layer2_core.wiring import coherence_engine
    coherence_engine.finalize_baseline(force=True)

    router = DualStreamRouter()
    payload = {
        "node_id": "N1", "sensor_id": "S1", "modality": "rf_sdr",
        "payload_uuid": str(uuid.uuid4()), "timestamp_utc": time.time(),
        "trust_state": TrustState.CAL_TRUSTED.value,
        "extracted_phases": [0.5, 1.5, 2.5, 3.5] * 10,
    }

    decision = router.route(json.dumps(payload))
    assert decision.stream == RouteStream.SECONDARY.value
