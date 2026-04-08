"""
SPEC-006 | Trust Tier: Processed (Layer 2)
"""
import cmath
import uuid
from dataclasses import dataclass
from typing import List, Dict, Optional
from collections import deque
import numpy as np

@dataclass
class CoherencePacket:
    """SPEC-006.1a — Internal Coherence Packet"""
    payload_uuid: str
    node_id: str
    modality: str
    r_local: float = 0.0
    r_smooth: float = 0.0
    r_global: float = 0.0  
    trust_state: str = "CORE_PROCESSED"
    event_window_id: Optional[str] = None

class CoherenceScorer:
    """SPEC-006.1 — KCET-ATLAS Coherence Engine (Rev 3.1)"""
    MODALITY_WEIGHTS = {"rf_sdr": 3.0, "gps_pps": 1.0, "thermal": 1.0, "acoustic": 1.0}

    def __init__(self, alpha: float = 0.2, window_ms: int = 300, min_nodes: int = 4):
        self.alpha = alpha
        self.window_ms = window_ms
        self.min_nodes = min_nodes
        self.history: Dict[str, deque] = {}
        self.global_events: List[Dict] = []
        self.fleet_state: Dict[str, dict] = {}
        
        self.baseline_learning_mode = True
        self.baseline_duration_hours = 72
        self.baseline_samples: List[float] = []
        self.dynamic_threshold: Optional[float] = None

    def compute_local_r(self, phases: List[float]) -> float:
        """SPEC-006.2 — Instantaneous Kuramoto order parameter."""
        if not phases: return 0.0
        return abs(sum(cmath.exp(1j * phi) for phi in phases) / len(phases))

    def compute_global_R(self) -> float:
        """SPEC-006.2b — Global Multi-Node Weighted Coherence R(t) [Rev 3.1]"""
        if not self.fleet_state: return 0.0
        weighted_sum = 0j
        total_weight = 0.0
        for nid, state in self.fleet_state.items():
            w = self.MODALITY_WEIGHTS.get(state["modality"], 1.0)
            weighted_sum += w * state["r_smooth"] * cmath.exp(1j * state["mean_phase"])
            total_weight += w
        if total_weight == 0: return 0.0
        return abs(weighted_sum / total_weight)

    def finalize_baseline(self):
        """SPEC-009 — Compute adaptive threshold from collected samples."""
        arr = np.array(self.baseline_samples)
        self.dynamic_threshold = float(np.mean(arr) + 3.0 * np.std(arr))
        self.baseline_learning_mode = False

    def update(self, payload_dict: dict, phases: List[float]) -> CoherencePacket:
        """SPEC-006.3 — Main entry point (Rev 3.1)."""
        node_id = payload_dict.get("node_id", "unknown")
        modality = payload_dict.get("modality", "unknown")
        if hasattr(modality, 'value'): modality = modality.value

        r_local = self.compute_local_r(phases)
        if node_id not in self.history: self.history[node_id] = deque(maxlen=100)
        prev = self.history[node_id][-1][1] if self.history[node_id] else 0.0
        r_smooth = self.alpha * r_local + (1 - self.alpha) * prev
        ts = payload_dict.get("timestamp_utc", 0.0)
        self.history[node_id].append((ts, r_smooth))

        mean_phase = 0.0
        if phases: mean_phase = cmath.phase(sum(cmath.exp(1j * phi) for phi in phases) / len(phases))
        self.fleet_state[node_id] = {"r_smooth": r_smooth, "mean_phase": mean_phase, "modality": modality, "ts": ts}

        packet = CoherencePacket(
            payload_uuid=payload_dict.get("payload_uuid", str(uuid.uuid4())),
            node_id=node_id, modality=modality, r_local=r_local,
            r_smooth=r_smooth, r_global=self.compute_global_R()
        )
        self._check_global_confirmation(ts, packet)
        return packet

    def _check_global_confirmation(self, ts: float, packet: CoherencePacket):
        """SPEC-006.4 — Multi-node event confirmation within sliding window."""
        if self.baseline_learning_mode:
            self.baseline_samples.append(packet.r_smooth)
            return
            
        window_s = self.window_ms / 1000.0
        confirming = [nid for nid, hist in self.history.items() 
                      if hist and abs(hist[-1][0] - ts) <= window_s and hist[-1][1] >= (self.dynamic_threshold or 0.40)]
        
        if len(confirming) >= self.min_nodes:
            event_id = str(uuid.uuid4())
            packet.event_window_id = event_id
            self.global_events.append({
                "event_id": event_id, "timestamp": ts,
                "confirming_nodes": confirming, "node_count": len(confirming)
            })
