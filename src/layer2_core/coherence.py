import uuid
import time
import math
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
        if not phases: return 0.0
        x = sum(math.cos(p) for p in phases)
        y = sum(math.sin(p) for p in phases)
        return math.sqrt(x*x + y*y) / len(phases)

    def compute_global_R(self) -> float:
        if not self.fleet_state: return 0.0
        return sum(node.get("r_smooth", 0.0) for node in self.fleet_state.values()) / max(1, len(self.fleet_state))

    def finalize_baseline(self):
        """SPEC-009 – Finalize 72-hour learning threshold."""
        self.baseline_learning_mode = False
        if self.baseline_samples:
            mean_r = sum(self.baseline_samples) / len(self.baseline_samples)
            variance = sum((x - mean_r)**2 for x in self.baseline_samples) / max(1, len(self.baseline_samples))
            self.dynamic_threshold = mean_r + (3 * math.sqrt(variance))

    def update(self, payload: Dict, phases: List[float]) -> CoherencePacket:
        """SPEC-006.3 — Main update loop mapping phases to coherence packet."""
        r_local = self.compute_local_r(phases)
        node_id = payload.get("node_id", "UNKNOWN")
        self.fleet_state[node_id] = {
            "r_smooth": r_local,
            "mean_phase": 0.0,
            "modality": payload.get("modality", "unknown"),
            "ts": payload.get("timestamp_utc", time.time())
        }
        r_global = self.compute_global_R()
        evt_id = f"EVT-{int(time.time())}-{str(uuid.uuid4())[:8]}" if r_local >= self.dynamic_threshold else None
        
        return CoherencePacket(
            payload_uuid=payload.get("payload_uuid", str(uuid.uuid4())),
            node_id=node_id, modality=payload.get("modality", "unknown"),
            r_local=r_local, r_smooth=r_local, r_global=r_global,
            trust_state="UNKNOWN", event_window_id=evt_id
        )
