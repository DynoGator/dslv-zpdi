"""
SPEC-007 | Trust Tier: Routed (Layer 3)
Dual-Stream Protocol enforcer with Swarm Integrity verification.
"""

from typing import Optional, List
from dataclasses import dataclass
from ..layer2_core.wiring import wire_to_coherence, coherence_engine
from ..layer2_core.coherence import CoherencePacket
from ..layer2_core.swarm_integrity import SwarmIntegrityMonitor


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
        self.swarm_monitor = SwarmIntegrityMonitor()  # SPEC-008 Integration

    def route(self, json_payload: str) -> RoutingDecision:
        """SPEC-007.3a — Route single packet."""
        pkt = wire_to_coherence(json_payload)
        if pkt is None:
            self.stats["routed_secondary"] += 1
            return RoutingDecision(
                "SECONDARY", "wiring_rejected", None, "SECONDARY_QUARANTINED"
            )

        # Check SPEC-009 baseline readiness
        baseline_status = coherence_engine.get_baseline_status()
        if not baseline_status.get("ready"):
            pkt.trust_state = "SECONDARY_QUARANTINED"
            self.stats["routed_secondary"] += 1
            return RoutingDecision(
                "SECONDARY", "baseline_learning_active", pkt, "SECONDARY_QUARANTINED"
            )

        # Check for confirmed event window
        if pkt.r_smooth >= 0.40 and pkt.event_window_id:
            pkt.trust_state = "PRIMARY_ACCEPTED"
            self.stats["routed_primary"] += 1
            return RoutingDecision(
                "PRIMARY", "confirmed_event", pkt, "PRIMARY_ACCEPTED"
            )
        elif pkt.r_smooth >= 0.15:
            pkt.trust_state = "PRIMARY_CANDIDATE"
            self.stats["routed_secondary"] += 1
            return RoutingDecision(
                "PRIMARY_CANDIDATE", "structured_background", pkt, "PRIMARY_CANDIDATE"
            )

        pkt.trust_state = "SECONDARY_QUARANTINED"
        self.stats["routed_secondary"] += 1
        return RoutingDecision(
            "SECONDARY", "below_threshold", pkt, "SECONDARY_QUARANTINED"
        )

    def validate_swarm_cluster(self, packets: List[dict]) -> bool:
        """SPEC-008.1 — Interface for multi-node swarm validation."""
        is_valid, reason = self.swarm_monitor.evaluate_swarm_trigger(packets)
        if not is_valid:
            # SPEC-008.1a: Log poisoned trigger event
            return False
        return True
