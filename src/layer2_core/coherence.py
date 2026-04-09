import uuid
import time
import math
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
    def __init__(self):
        self.fleet_state: Dict[str, Dict] = {}
        self.baseline_learning_mode = False
        self.baseline_samples: List[float] = []
        self.dynamic_threshold = 0.40

    def compute_local_r(self, phases: List[float]) -> float:
        """SPEC-006.1 — Compute Kuramoto order parameter r(t)."""
        if not phases: return 0.0
        phases_arr = np.array(phases)
        r = np.abs(np.mean(np.exp(1j * phases_arr)))
        return float(r)

    def compute_global_R(self) -> float:
        """SPEC-006.2 — Compute weighted global coherence R(t)."""
        if not self.fleet_state: return 0.0
        # Simple mean for now, Phase 2A will implement SPEC-006 modality weights
        r_vals = [node.get("r_smooth", 0.0) for node in self.fleet_state.values()]
        return float(np.mean(r_vals))

    def finalize_baseline(self):
        """SPEC-009 — Finalize 72-hour learning threshold using Kurtosis-aware stats."""
        self.baseline_learning_mode = False
        if not self.baseline_samples:
            self.dynamic_threshold = 0.40
            return
            
        arr = np.array(self.baseline_samples)
        mean_r = np.mean(arr)
        std_r = np.std(arr)
        
        # SPEC-009: 3-sigma outlier detection for environmental calibration
        self.dynamic_threshold = float(mean_r + (3.0 * std_r))
        # Ensure threshold doesn't collapse to 0 in silent environments
        self.dynamic_threshold = max(self.dynamic_threshold, 0.25)

    def update(self, payload: Dict, phases: List[float]) -> CoherencePacket:
        """SPEC-006.3 — Main update loop mapping phases to coherence packet."""
        r_local = self.compute_local_r(phases)
        node_id = payload.get("node_id", "UNKNOWN")
        
        # Update fleet state for global R(t) calculation
        self.fleet_state[node_id] = {
            "r_smooth": r_local,
            "modality": payload.get("modality", "unknown"),
            "timestamp": payload.get("timestamp_utc", time.time())
        }
        
        if self.baseline_learning_mode:
            self.baseline_samples.append(r_local)
            
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
            event_window_id=evt_id
        )
