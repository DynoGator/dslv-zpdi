"""
SPEC-007 | Trust Tier: Routed (Layer 3) — Rev 3.1
"""
from typing import Optional
from ..layer2_core.wiring import wire_to_coherence
from ..layer2_core.coherence import CoherencePacket

def route_packet(json_payload: str) -> dict:
    """SPEC-007.1 — Route a single packet to primary or secondary stream."""
    coherence_packet = wire_to_coherence(json_payload)
    if coherence_packet is None:
        return {"stream": "SECONDARY", "reason": "wiring_rejected", "packet": None}

    if coherence_packet.r_smooth >= 0.40 and coherence_packet.event_window_id:
        coherence_packet.trust_state = "PRIMARY_ACCEPTED"
        return {"stream": "PRIMARY", "reason": "confirmed_event", "packet": coherence_packet}
    elif coherence_packet.r_smooth >= 0.15:
        coherence_packet.trust_state = "PRIMARY_CANDIDATE"
        return {"stream": "PRIMARY_CANDIDATE", "reason": "structured_background", "packet": coherence_packet}
    else:
        coherence_packet.trust_state = "SECONDARY_QUARANTINED"
        return {"stream": "SECONDARY", "reason": "below_threshold", "packet": coherence_packet}
