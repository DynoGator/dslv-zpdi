import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
from ..layer2_core.wiring import wire_to_coherence
from ..layer2_core.coherence import CoherencePacket

@dataclass
class RoutingDecision:
    """SPEC-007 — Canonical routing container for Layer 3 consumers."""
    stream: str  
    reason: str
    packet: Optional[CoherencePacket]
    trust_state: str

class DualStreamRouter:
    """SPEC-007 — Stateful router for HDF5Writer integration."""
    def __init__(self):
        self.stats = {
            "primary_accepted": 0,
            "secondary_quarantined": 0,
            "rejected": 0
        }
        self.adaptive_threshold = 0.40
    
    def route(self, json_payload: str) -> RoutingDecision:
        """SPEC-007 — Primary routing entry point enforcing Dual-Stream."""
        try:
            payload_dict = json.loads(json_payload)
            incoming_state = payload_dict.get("trust_state", "KILLED")
        except json.JSONDecodeError:
            self.stats["rejected"] += 1
            return RoutingDecision("REJECTED", "json_parse_error", None, "KILLED")
            
        if incoming_state == "SECONDARY_QUARANTINED":
            self.stats["secondary_quarantined"] += 1
            return RoutingDecision("SECONDARY", "layer1_quarantine", None, "SECONDARY_QUARANTINED")
            
        if incoming_state == "KILLED":
            self.stats["rejected"] += 1
            return RoutingDecision("REJECTED", "layer1_killed", None, "KILLED")

        coherence_packet = wire_to_coherence(json_payload)
        
        if coherence_packet is None:
            self.stats["rejected"] += 1
            return RoutingDecision("REJECTED", "wiring_rejected", None, "KILLED")
        
        if (coherence_packet.r_smooth >= self.adaptive_threshold and 
            coherence_packet.event_window_id and
            coherence_packet.trust_state == "CORE_PROCESSED"):
            
            coherence_packet.trust_state = "PRIMARY_ACCEPTED"
            self.stats["primary_accepted"] += 1
            return RoutingDecision("PRIMARY", "confirmed_event", coherence_packet, "PRIMARY_ACCEPTED")
            
        elif coherence_packet.r_smooth >= 0.15:
            coherence_packet.trust_state = "PRIMARY_CANDIDATE"
            self.stats["secondary_quarantined"] += 1
            return RoutingDecision("SECONDARY", "candidate_pending_confirmation", coherence_packet, "PRIMARY_CANDIDATE")
        else:
            coherence_packet.trust_state = "SECONDARY_QUARANTINED"
            self.stats["secondary_quarantined"] += 1
            return RoutingDecision("SECONDARY", "below_threshold", coherence_packet, "SECONDARY_QUARANTINED")
    
    def set_adaptive_threshold(self, threshold: float):
        """SPEC-009 — Dynamic threshold from 72h baseline."""
        self.adaptive_threshold = threshold

def route_packet(json_payload: str) -> Dict[str, Any]:
    """SPEC-007 — Legacy functional interface."""
    router = DualStreamRouter()
    decision = router.route(json_payload)
    return {"stream": decision.stream, "reason": decision.reason, "packet": decision.packet}
