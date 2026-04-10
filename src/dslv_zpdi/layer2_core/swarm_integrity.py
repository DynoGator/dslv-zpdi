"""
SPEC-008 | Trust Tier: Swarm Validation
"""

import math
import time
from typing import List

SPEED_OF_LIGHT_M_S = 299_792_458.0


# pylint: disable=too-few-public-methods
class SwarmIntegrityMonitor:
    """SPEC-008.1a — Swarm Anti-Poisoning (Rev 3.1)"""

    def __init__(self, sigma_threshold: float = 3.0):
        self.sigma_threshold = sigma_threshold
        self.regional_baselines: dict = {}

    # pylint: disable=too-many-locals
    def evaluate_swarm_trigger(self, swarm_packets: List[dict]) -> tuple:
        """SPEC-008.2 — Enhanced with temporal freshness check."""
        if len(swarm_packets) < 2:
            return True, "single_node_trigger"

        # New: Check timestamp freshness (prevent stale trigger replay)
        now = time.time()
        max_age_seconds = 300  # 5-minute window
        for packet in swarm_packets:
            pkt_time = packet.get("timestamp_utc", 0)
            if now - pkt_time > max_age_seconds:
                return False, "POISONED: stale_trigger_replay"

        for i in range(len(swarm_packets) - 1):
            p1, p2 = swarm_packets[i], swarm_packets[i + 1]
            dist_m = (
                math.sqrt(
                    (p2.get("lat", 0) - p1.get("lat", 0)) ** 2
                    + (p2.get("lon", 0) - p1.get("lon", 0)) ** 2
                )
                * 111_320
            )
            dt_s = abs(p2.get("timestamp_utc", 0) - p1.get("timestamp_utc", 0))
            if dt_s > 0 and (dist_m / dt_s) > 1.5 * SPEED_OF_LIGHT_M_S:
                return False, "POISONED: impossible propagation speed"

        region_id = swarm_packets[0].get("region_id", "default")
        baseline = self.regional_baselines.get(region_id)
        if baseline:
            for packet in swarm_packets:
                mean = baseline.get("mean_signal", 0)
                std = baseline.get("std_signal", 1)
                deviation = (
                    abs(packet.get("signal_strength", mean) - mean) / std
                    if std > 0
                    else 0.0
                )
                if deviation > self.sigma_threshold:
                    return False, f"POISONED: stylistic deviation {deviation:.1f}σ"
        return True, "valid_trigger"
