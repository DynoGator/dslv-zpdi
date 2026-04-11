"""
SPEC-003 | Canonical State Vocabulary
Centralized source of truth for all trust and routing states.
"""

from enum import Enum


class TrustState(Enum):
    """SPEC-003.1 — Authorized trust states for telemetry packets."""

    ASSEMBLED = "ASSEMBLED"
    KILLED = "KILLED"
    SECONDARY_QUARANTINED = "SECONDARY_QUARANTINED"
    TIME_TRUSTED = "TIME_TRUSTED"
    CAL_TRUSTED = "CAL_TRUSTED"
    CORE_PROCESSED = "CORE_PROCESSED"
    PRIMARY_ACCEPTED = "PRIMARY_ACCEPTED"
    PRIMARY_CANDIDATE = "PRIMARY_CANDIDATE"


class RouteStream(Enum):
    """SPEC-007.2 — Authorized routing streams per SPEC-003."""

    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"


class BaselineState(Enum):
    """SPEC-009.1 — Three-state FSM for environmental baseline learning."""

    NOT_STARTED = "NOT_STARTED"
    LEARNING = "LEARNING"
    LOCKED = "LOCKED"
