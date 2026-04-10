"""
SPEC-007 | Trust Tier: Routed (Layer 3)
Dual-Stream Protocol enforcer with Swarm Integrity verification.
"""

from dataclasses import dataclass
from typing import List, Optional

from dslv_zpdi.core.states import TrustState, RouteStream
from dslv_zpdi.layer2_core.coherence import CoherencePacket
from dslv_zpdi.layer2_core.swarm_integrity import SwarmIntegrityMonitor
from dslv_zpdi.layer2_core.wiring import coherence_engine, wire_to_coherence


@dataclass
class RoutingDecision:
    """SPEC-007.2 — Data structure for routing outcomes."""

    stream: str
    reason: str
    packet: Optional[CoherencePacket] = None
    trust_state: str = TrustState.ASSEMBLED.value


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
                RouteStream.SECONDARY.value, "wiring_rejected", None, TrustState.SECONDARY_QUARANTINED.value
            )

        # Check SPEC-009 baseline readiness
        baseline_status = coherence_engine.get_baseline_status()
        if not baseline_status.get("ready"):
            pkt.trust_state = TrustState.SECONDARY_QUARANTINED.value
            self.stats["routed_secondary"] += 1
            return RoutingDecision(
                RouteStream.SECONDARY.value, "baseline_learning_active", pkt, TrustState.SECONDARY_QUARANTINED.value
            )

        # Check for confirmed event window
        if pkt.r_smooth >= 0.40 and pkt.event_window_id:
            pkt.trust_state = TrustState.PRIMARY_ACCEPTED.value
            self.stats["routed_primary"] += 1
            return RoutingDecision(
                RouteStream.PRIMARY.value, "confirmed_event", pkt, TrustState.PRIMARY_ACCEPTED.value
            )

        if pkt.r_smooth >= 0.15:
            pkt.trust_state = TrustState.PRIMARY_CANDIDATE.value
            self.stats["routed_secondary"] += 1
            return RoutingDecision(
                RouteStream.PRIMARY_CANDIDATE.value, "structured_background", pkt, TrustState.PRIMARY_CANDIDATE.value
            )

        pkt.trust_state = TrustState.SECONDARY_QUARANTINED.value
        self.stats["routed_secondary"] += 1
        return RoutingDecision(
            RouteStream.SECONDARY.value, "below_threshold", pkt, TrustState.SECONDARY_QUARANTINED.value
        )


    def validate_swarm_cluster(self, packets: List[dict]) -> bool:
        """SPEC-008.1 — Interface for multi-node swarm validation."""
        is_valid, _ = self.swarm_monitor.evaluate_swarm_trigger(packets)
        if not is_valid:
            # SPEC-008.1a: Log poisoned trigger event
            return False
        return True
