"""
SPEC-006 | Trust Tier: Coherence Analysis
SPEC-009 | Baseline Learning FSM (NOT_STARTED → LEARNING → LOCKED)
Layer 2 implementation of Kuramoto order parameters, EWMA smoothing, and baseline learning.

Kill condition: Any coherence calculation on packets below CAL_TRUSTED state,
or any direct hardware access from this layer.
"""

import cmath
import json
import logging
import os
import time
import uuid
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from dslv_zpdi.core.states import BaselineState

logger = logging.getLogger("dslv-zpdi.coherence")


@dataclass
class CoherencePacket:
    """SPEC-006 — Processed telemetry packet."""

    payload_uuid: str
    node_id: str
    modality: str
    r_local: float
    r_smooth: float
    r_global: float
    trust_state: str = "UNKNOWN"
    event_window_id: Optional[str] = None


# pylint: disable=too-many-instance-attributes
class CoherenceScorer:
    """SPEC-006 — Kuramoto Coherence Engine with EWMA smoothing and baseline FSM."""

    MODALITY_WEIGHTS = {
        "rf_sdr": 3.0,
        "gps_pps": 1.0,
        "thermal": 1.0,
        "acoustic": 1.0,
        "magnetometer": 1.0,
        "inertial": 1.0,
    }

    def __init__(
        self,
        alpha: float = 0.2,
        window_ms: int = 300,
        min_nodes: int = 4,
        baseline_state_path=None,
        min_baseline_samples=10,
        baseline_duration_hours=72,
    ):
        """SPEC-006 / SPEC-009 — Initialize coherence engine with baseline support."""
        self.alpha = alpha
        self.window_ms = window_ms
        self.min_nodes = min_nodes
        self.history: Dict[str, deque] = {}
        self.fleet_state: Dict[str, Dict] = {}
        self.global_events: List[Dict] = []

        # SPEC-009: Baseline FSM state
        self.baseline_state_path = baseline_state_path
        self.min_baseline_samples = min_baseline_samples
        self.baseline_duration_hours = baseline_duration_hours
        self._baseline_state = BaselineState.NOT_STARTED
        self.baseline_samples: List[float] = []
        self.dynamic_threshold = 0.40
        self.baseline_started_utc = 0.0

        # Load persisted baseline state
        if self.baseline_state_path and os.path.exists(self.baseline_state_path):
            try:
                with open(self.baseline_state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    persisted = data.get("baseline_state", "NOT_STARTED")
                    if persisted == BaselineState.LOCKED.value:
                        self._baseline_state = BaselineState.LOCKED
                        self.dynamic_threshold = data.get("threshold", 0.40)
                    elif persisted == BaselineState.LEARNING.value:
                        self._baseline_state = BaselineState.LEARNING
                        self.baseline_samples = data.get("samples", [])
                        self.baseline_started_utc = data.get("started_utc", 0.0)
                    else:
                        self._baseline_state = BaselineState.NOT_STARTED
            except (json.JSONDecodeError, OSError, KeyError):
                pass

    @property
    def baseline_learning_mode(self) -> bool:
        """Compatibility property: True when FSM is in LEARNING state."""
        return self._baseline_state == BaselineState.LEARNING

    @baseline_learning_mode.setter
    def baseline_learning_mode(self, value: bool):
        """Compatibility setter for legacy code that sets baseline_learning_mode directly."""
        if value and self._baseline_state == BaselineState.NOT_STARTED:
            self._baseline_state = BaselineState.LEARNING
        elif not value and self._baseline_state == BaselineState.LEARNING:
            self._baseline_state = BaselineState.LOCKED

    def start_baseline(self, started_utc=None):
        """SPEC-009 — Transition NOT_STARTED → LEARNING. Restarting from LOCKED is forbidden."""
        if self._baseline_state == BaselineState.LOCKED:
            logger.warning("SPEC-009: Cannot restart baseline from LOCKED state")
            return
        self._baseline_state = BaselineState.LEARNING
        self.baseline_started_utc = started_utc or time.time()
        self.baseline_samples = []
        self._save_baseline_state()

    def update_baseline(self, r_local):
        """SPEC-009 — Collect r_local sample during LEARNING phase."""
        if self._baseline_state == BaselineState.LEARNING:
            self.baseline_samples.append(r_local)
            self._save_baseline_state()

    def get_baseline_status(self) -> dict:
        """SPEC-009 — Get current baseline learning status."""
        return {
            "ready": self._baseline_state == BaselineState.LOCKED,
            "baseline_state": self._baseline_state.value,
            "threshold": self.dynamic_threshold,
            "samples": len(self.baseline_samples),
            "started_utc": self.baseline_started_utc,
        }

    def _save_baseline_state(self):
        """SPEC-009.1 — Atomic baseline persistence with write verification."""
        if not self.baseline_state_path:
            return

        temp_path = self.baseline_state_path + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "baseline_state": self._baseline_state.value,
                        "ready": self._baseline_state == BaselineState.LOCKED,
                        "threshold": self.dynamic_threshold,
                        "samples": self.baseline_samples,
                        "started_utc": self.baseline_started_utc,
                        "schema_version": "3.1",
                    },
                    f,
                )
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self.baseline_state_path)
        except (IOError, OSError) as e:
            logger.error("Baseline persistence failed: %s", e)
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def compute_local_r(self, phases: List[float]) -> float:
        """SPEC-006.1 — Compute Kuramoto order parameter r(t).
        r(t) = | (1/N) * sum(e^(i*phi_k)) |"""
        if not phases:
            return 0.0
        phases_arr = np.array(phases)
        r = np.abs(np.mean(np.exp(1j * phases_arr)))
        return float(r)

    def compute_global_r(self) -> float:
        """SPEC-006.2 — Compute weighted global coherence R(t) per Section 5.5.2.
        R(t) = | sum(w_m * r_m * e^(i*psi_m)) | / sum(w_m)"""
        if not self.fleet_state:
            return 0.0
        weighted_sum = 0j
        total_weight = 0.0
        for _nid, state in self.fleet_state.items():
            w = self.MODALITY_WEIGHTS.get(state.get("modality", ""), 1.0)
            r_smooth = state.get("r_smooth", 0.0)
            mean_phase = state.get("mean_phase", 0.0)
            weighted_sum += w * r_smooth * cmath.exp(1j * mean_phase)
            total_weight += w
        if total_weight == 0:
            return 0.0
        return float(abs(weighted_sum / total_weight))

    def finalize_baseline(self, force=False):
        """SPEC-009 — Transition LEARNING → LOCKED after minimum samples and duration gate."""
        if self._baseline_state != BaselineState.LEARNING:
            return None

        if not force:
            if len(self.baseline_samples) < self.min_baseline_samples:
                return None
            # 72-hour duration gate
            elapsed_hours = (time.time() - self.baseline_started_utc) / 3600.0
            if elapsed_hours < self.baseline_duration_hours:
                return None

        self._baseline_state = BaselineState.LOCKED
        if not self.baseline_samples:
            self.dynamic_threshold = 0.40
            self._save_baseline_state()
            return self.dynamic_threshold

        arr = np.array(self.baseline_samples)
        mean_r = np.mean(arr)
        std_r = np.std(arr)

        # SPEC-009: 3-sigma outlier detection for environmental calibration
        self.dynamic_threshold = float(mean_r + (3.0 * std_r))
        # Ensure threshold doesn't collapse to 0 in silent environments
        self.dynamic_threshold = max(self.dynamic_threshold, 0.25)
        self._save_baseline_state()
        return self.dynamic_threshold

    def update(self, payload: Dict, phases: List[float]) -> CoherencePacket:
        """SPEC-006.3 — Main entry point with EWMA smoothing per Section 5.5.3."""
        node_id = payload.get("node_id", "UNKNOWN")
        modality = payload.get("modality", "unknown")
        if hasattr(modality, "value"):
            modality = modality.value

        r_local = self.compute_local_r(phases)

        # SPEC-006 Section 5.5.3: EWMA smoothing
        # r_smooth(t) = alpha * r(t) + (1 - alpha) * r_smooth(t-1)
        if node_id not in self.history:
            self.history[node_id] = deque(maxlen=100)
        prev_r_smooth = self.history[node_id][-1][1] if self.history[node_id] else 0.0
        r_smooth = self.alpha * r_local + (1 - self.alpha) * prev_r_smooth

        ts = payload.get("timestamp_utc", 0.0)
        self.history[node_id].append((ts, r_smooth))

        # Update fleet state for global R(t) with mean phase
        mean_phase = 0.0
        if phases:
            mean_phase = cmath.phase(
                sum(cmath.exp(1j * phi) for phi in phases) / len(phases)
            )
        self.fleet_state[node_id] = {
            "r_smooth": r_smooth,
            "mean_phase": mean_phase,
            "modality": modality,
            "ts": ts,
        }

        # Collect baseline samples during LEARNING
        if self._baseline_state == BaselineState.LEARNING:
            self.baseline_samples.append(r_local)

        r_global = self.compute_global_r()

        packet = CoherencePacket(
            payload_uuid=payload.get("payload_uuid", str(uuid.uuid4())),
            node_id=node_id,
            modality=modality,
            r_local=r_local,
            r_smooth=r_smooth,
            r_global=r_global,
            trust_state=payload.get("trust_state", "ASSEMBLED"),
        )

        # SPEC-009: No event declaration during LEARNING
        if self._baseline_state != BaselineState.LEARNING:
            self._check_global_confirmation(ts, packet)

        return packet

    def _check_global_confirmation(self, ts: float, packet: CoherencePacket):
        """SPEC-006.4 — Multi-node event confirmation within sliding window.
        Requires >=min_nodes with r_smooth >= threshold within window_ms."""
        window_s = self.window_ms / 1000.0
        threshold = self.dynamic_threshold
        confirming = []
        for nid, hist in self.history.items():
            recent = [(t, r) for t, r in hist if abs(t - ts) <= window_s]
            if recent and recent[-1][1] >= threshold:
                confirming.append(nid)
        if len(confirming) >= self.min_nodes:
            event_id = str(uuid.uuid4())
            packet.event_window_id = event_id
            self.global_events.append({
                "event_id": event_id,
                "timestamp": ts,
                "confirming_nodes": confirming,
                "node_count": len(confirming),
            })
