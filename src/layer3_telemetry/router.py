"""
SPEC-007 | Trust Tier: Routed (Layer 3)
Dual-Stream Protocol enforcer. Primary stream = institutional HDF5 only.
"""
from typing import Optional
from dataclasses import dataclass
from ..layer2_core.wiring import wire_to_coherence
from ..layer2_core.coherence import CoherencePacket

@dataclass
class RoutingDecision:
    """SPEC-007.2 — Data structure for routing outcomes."""
    stream: str
    reason: str
    packet: Optional[CoherencePacket] = None
    trust_state: str = "UNKNOWN"

class DualStreamRouter:
    """SPEC-007.3 — Stateful router for Dual-Stream enforcement."""
    def __init__(self):
        self.stats = {"routed_primary": 0, "routed_secondary": 0}
        
    def route(self, json_payload: str) -> RoutingDecision:
        """SPEC-007.3a — Route a single packet to primary or secondary stream."""
        coherence_packet = wire_to_coherence(json_payload)

        if coherence_packet is None:
            self.stats["routed_secondary"] += 1
            return RoutingDecision("SECONDARY", "wiring_rejected", None, "SECONDARY_QUARANTINED")

        if coherence_packet.r_smooth >= 0.40 and coherence_packet.event_window_id:
            coherence_packet.trust_state = "PRIMARY_ACCEPTED"
            self.stats["routed_primary"] += 1
            return RoutingDecision("PRIMARY", "confirmed_event", coherence_packet, "PRIMARY_ACCEPTED")
        elif coherence_packet.r_smooth >= 0.15:
            coherence_packet.trust_state = "PRIMARY_CANDIDATE"
            self.stats["routed_secondary"] += 1
            return RoutingDecision("PRIMARY_CANDIDATE", "structured_background", coherence_packet, "PRIMARY_CANDIDATE")
        else:
            coherence_packet.trust_state = "SECONDARY_QUARANTINED"
            self.stats["routed_secondary"] += 1
            return RoutingDecision("SECONDARY", "below_threshold", coherence_packet, "SECONDARY_QUARANTINED")
