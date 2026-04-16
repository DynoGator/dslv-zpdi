"""
SPEC-009 | Canonical Tier 1 Policy Contract
Centralized source of truth for Tier 1 hardware and routing policies.
"""

from dslv_zpdi.layer1_ingestion.payload import SensorModality

# Clock discipline
REQUIRED_CLOCK_SOURCE = "external"
PPS_JITTER_CEILING_NS = 10_000.0

# Accepted modalities for Tier 1 primary stream
ACCEPTED_MODALITIES = {m.value for m in SensorModality}

# Baseline readiness rules
BASELINE_READY_STATE = "LOCKED"
MIN_BASELINE_SAMPLES = 10
BASELINE_DURATION_HOURS = 72

# Routing thresholds
DEFAULT_DYNAMIC_THRESHOLD = 0.40
CANDIDATE_THRESHOLD_RATIO = 0.5
MIN_DYNAMIC_THRESHOLD = 0.25

# Schema
REQUIRED_SCHEMA_VERSION = "3.1"

# Simulation marking
SIMULATION_MARKER = "SIMULATED"


def get_routing_thresholds(dynamic_threshold: float) -> dict:
    """SPEC-009.1 — Return primary and candidate thresholds derived from a locked baseline."""
    return {
        "primary": max(dynamic_threshold, MIN_DYNAMIC_THRESHOLD),
        "candidate": max(dynamic_threshold * CANDIDATE_THRESHOLD_RATIO, 0.05),
    }
