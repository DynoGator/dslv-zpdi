import uuid
import time
import math
import os
import json
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class CoherencePacket:
    """SPEC-006 – Processed telemetry packet."""

    payload_uuid: str
    node_id: str
    modality: str
    r_local: float
    r_smooth: float
    r_global: float
    trust_state: str = "UNKNOWN"
    event_window_id: Optional[str] = None


class CoherenceScorer:
    """SPEC-006 ― Kuramoto Coherence Engine."""

    def __init__(
        self,
        baseline_state_path=None,
        min_baseline_samples=10,
        baseline_duration_hours=72,
    ):
        self.fleet_state: Dict[str, Dict] = {}
        self.baseline_state_path = baseline_state_path
        self.min_baseline_samples = min_baseline_samples
        self.baseline_duration_hours = baseline_duration_hours

        self.baseline_learning_mode = False
        self.baseline_samples: List[float] = []
        self.dynamic_threshold = 0.40
        self.baseline_started_utc = 0.0

        # Load from persistence if available
        if self.baseline_state_path and os.path.exists(self.baseline_state_path):
            try:
                with open(self.baseline_state_path, "r") as f:
                    data = json.load(f)
                    if data.get("ready"):
                        self.dynamic_threshold = data.get("threshold", 0.40)
                        self.baseline_learning_mode = False
                    else:
                        self.baseline_learning_mode = True
                        self.baseline_samples = data.get("samples", [])
                        self.baseline_started_utc = data.get("started_utc", time.time())
            except Exception:
                pass

    def start_baseline(self, started_utc=None):
        self.baseline_learning_mode = True
        self.baseline_started_utc = started_utc or time.time()
        self.baseline_samples = []
        self._save_baseline_state()

    def update_baseline(self, r_local, ts):
        if self.baseline_learning_mode:
            self.baseline_samples.append(r_local)
            self._save_baseline_state()

    def get_baseline_status(self) -> dict:
        return {
            "ready": not self.baseline_learning_mode,
            "threshold": self.dynamic_threshold,
            "samples": len(self.baseline_samples),
            "started_utc": self.baseline_started_utc,
        }

    def _save_baseline_state(self):
        if self.baseline_state_path:
            try:
                with open(self.baseline_state_path, "w") as f:
                    json.dump(
                        {
                            "ready": not self.baseline_learning_mode,
                            "threshold": self.dynamic_threshold,
                            "samples": self.baseline_samples,
                            "started_utc": self.baseline_started_utc,
                        },
                        f,
                    )
            except Exception:
                pass

    def compute_local_r(self, phases: List[float]) -> float:
        """SPEC-006.1 — Compute Kuramoto order parameter r(t)."""
        if not phases:
            return 0.0
        phases_arr = np.array(phases)
        r = np.abs(np.mean(np.exp(1j * phases_arr)))
        return float(r)

    def compute_global_R(self) -> float:
        """SPEC-006.2 — Compute weighted global coherence R(t)."""
        if not self.fleet_state:
            return 0.0
        # Simple mean for now, Phase 2A will implement SPEC-006 modality weights
        r_vals = [node.get("r_smooth", 0.0) for node in self.fleet_state.values()]
        return float(np.mean(r_vals))

    def finalize_baseline(self, force=False):
        """SPEC-009 — Finalize 72-hour learning threshold using Kurtosis-aware stats."""
        if not force and len(self.baseline_samples) < self.min_baseline_samples:
            return None

        self.baseline_learning_mode = False
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
        """SPEC-006.3 — Main update loop mapping phases to coherence packet."""
        r_local = self.compute_local_r(phases)
        node_id = payload.get("node_id", "UNKNOWN")

        # Update fleet state for global R(t) calculation
        self.fleet_state[node_id] = {
            "r_smooth": r_local,
            "modality": payload.get("modality", "unknown"),
            "timestamp": payload.get("timestamp_utc", time.time()),
        }

        if self.baseline_learning_mode:
            self.update_baseline(r_local, payload.get("timestamp_utc", time.time()))

        r_global = self.compute_global_R()

        # Event declaration based on dynamic threshold (SPEC-009)
        evt_id = None
        if not self.baseline_learning_mode and r_local >= self.dynamic_threshold:
            evt_id = f"EVT-{int(time.time())}-{str(uuid.uuid4())[:8]}"

        return CoherencePacket(
            payload_uuid=payload.get("payload_uuid", str(uuid.uuid4())),
            node_id=node_id,
            modality=payload.get("modality", "unknown"),
            r_local=r_local,
            r_smooth=r_local,
            r_global=r_global,
            trust_state=payload.get("trust_state", "ASSEMBLED"),
            event_window_id=evt_id,
        )
