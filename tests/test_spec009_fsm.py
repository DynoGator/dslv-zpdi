"""SPEC-009 — Three-state FSM tests: NOT_STARTED → LEARNING → LOCKED.
Tests state transitions, regression prevention, persistence, and duration gate."""

import json
import os
import tempfile
import time

from dslv_zpdi.core.states import BaselineState
from dslv_zpdi.layer2_core.coherence import CoherenceScorer


def test_fsm_initial_state_is_not_started():
    """SPEC-009: Fresh scorer starts in NOT_STARTED."""
    scorer = CoherenceScorer()
    status = scorer.get_baseline_status()
    assert status["baseline_state"] == BaselineState.NOT_STARTED.value
    assert status["ready"] is False


def test_fsm_not_started_to_learning():
    """SPEC-009: start_baseline() transitions NOT_STARTED → LEARNING."""
    scorer = CoherenceScorer()
    scorer.start_baseline()
    status = scorer.get_baseline_status()
    assert status["baseline_state"] == BaselineState.LEARNING.value
    assert status["ready"] is False


def test_fsm_learning_to_locked():
    """SPEC-009: finalize_baseline() transitions LEARNING → LOCKED."""
    scorer = CoherenceScorer(min_baseline_samples=5)
    scorer.start_baseline(started_utc=time.time() - (73 * 3600))
    for i in range(10):
        scorer.update_baseline(0.1 + i * 0.01)
    threshold = scorer.finalize_baseline(force=True)
    status = scorer.get_baseline_status()
    assert status["baseline_state"] == BaselineState.LOCKED.value
    assert status["ready"] is True
    assert threshold is not None


def test_fsm_locked_cannot_restart():
    """SPEC-009: Cannot regress from LOCKED back to LEARNING."""
    scorer = CoherenceScorer()
    scorer.start_baseline()
    scorer.finalize_baseline(force=True)
    assert scorer.get_baseline_status()["baseline_state"] == BaselineState.LOCKED.value

    # Attempt restart — should be blocked
    scorer.start_baseline()
    assert scorer.get_baseline_status()["baseline_state"] == BaselineState.LOCKED.value


def test_fsm_persistence_roundtrip():
    """SPEC-009.1: FSM state persists to JSON and survives process restart."""
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "baseline.json")

        # Session 1: start learning, collect samples, finalize
        s1 = CoherenceScorer(baseline_state_path=path, min_baseline_samples=5)
        s1.start_baseline(started_utc=time.time() - (73 * 3600))
        for i in range(10):
            s1.update_baseline(0.05 + i * 0.002)
        s1.finalize_baseline(force=True)

        # Session 2: reload from disk
        s2 = CoherenceScorer(baseline_state_path=path)
        status = s2.get_baseline_status()
        assert status["baseline_state"] == BaselineState.LOCKED.value
        assert status["ready"] is True
        assert status["threshold"] == s1.dynamic_threshold


def test_fsm_duration_gate_enforced():
    """SPEC-009: finalize_baseline() rejects if 72 hours haven't elapsed (non-force)."""
    scorer = CoherenceScorer(min_baseline_samples=5)
    scorer.start_baseline(started_utc=time.time())  # just started
    for i in range(20):
        scorer.update_baseline(0.1)
    result = scorer.finalize_baseline(force=False)  # should fail: not 72h
    assert result is None
    assert scorer.get_baseline_status()["baseline_state"] == BaselineState.LEARNING.value


def test_finalize_not_started_returns_none():
    """SPEC-009: Cannot finalize from NOT_STARTED state."""
    scorer = CoherenceScorer()
    result = scorer.finalize_baseline(force=True)
    assert result is None
