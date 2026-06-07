# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Joseph R. Fross

"""
SPEC-006.5 | Trust Tier: Processed (Layer 2 Wiring)
Rev 3.2 — enum rehydration, trust gating, phase extraction handoff, baseline status exposure.
"""

import json
import os
from typing import Optional

from dslv_zpdi.core.states import TrustState
from dslv_zpdi.layer1_ingestion.payload import SensorModality
from dslv_zpdi.layer2_core.coherence import CoherencePacket, CoherenceScorer


def _resolve_baseline_path() -> Optional[str]:
    """SPEC-006.5 — Return a baseline state path only if it exists on disk. Env override wins."""
    path = os.getenv("DSLV_BASELINE_STATE_PATH") or "/var/lib/dslv_zpdi/baseline.json"
    return path if os.path.exists(path) else None


coherence_engine = CoherenceScorer(baseline_state_path=_resolve_baseline_path())


# SPEC-006.5
def wire_to_coherence(json_payload: str) -> Optional[CoherencePacket]:
    """SPEC-006.5 — Wire ingested JSON payload to Layer 2 Coherence Packet."""
    if not json_payload:
        return None
    try:
        payload_dict = json.loads(json_payload)
    except json.JSONDecodeError:
        return None

    modality_str = str(payload_dict.get("modality", "")).strip()
    try:
        SensorModality(modality_str)
    except ValueError:
        return None

    trust_state = str(payload_dict.get("trust_state", "")).strip()
    if trust_state in {TrustState.SECONDARY_QUARANTINED.value, TrustState.KILLED.value}:
        return None
    if trust_state not in {
        TrustState.TIME_TRUSTED.value,
        TrustState.CAL_TRUSTED.value,
        TrustState.CORE_PROCESSED.value,
    }:
        return None

    phases = payload_dict.get("extracted_phases")
    if phases is None:
        raw_value = payload_dict.get("raw_value") or {}
        phases = raw_value.get("phases", []) if isinstance(raw_value, dict) else []
    if not isinstance(phases, list):
        phases = []

    packet = coherence_engine.update(payload_dict, phases)
    packet.trust_state = TrustState.CORE_PROCESSED.value
    return packet


# --- Mobile Tier-2 adaptation (from local mobile branch, integrated against GitHub master template) ---
def wire_mobile_to_coherence(payload_dict: dict) -> Optional[CoherencePacket]:
    """Mobile-specific wiring that bypasses the strict Tier-1 trust gate (TIME_TRUSTED etc).

    Tier-2 packets are inherently SECONDARY_QUARANTINED (by hardware definition on phone),
    but we still compute coherence scores for categorisation within the secondary stream
    (noise / structured_background / anomalous_candidate) per the mobile router (SPEC-007).

    This preserves full mobile functionality while using the canonical CoherenceScorer / Packet
    from the master package.
    """
    if not payload_dict:
        return None

    modality_str = str(payload_dict.get("modality", "")).strip()
    try:
        SensorModality(modality_str)
    except ValueError:
        # Allow known mobile modalities even if not in base SensorModality at load time
        if modality_str not in {
            "accel", "magnetometer", "barometer",
            "gyroscope", "rotation_vector", "geomagnetic_rotation", "gravity",
        }:
            return None

    trust_state = str(payload_dict.get("trust_state", "")).strip()
    if trust_state == TrustState.KILLED.value:
        return None
    # Note: deliberately do *not* early-return on SECONDARY_QUARANTINED for mobile

    phases = payload_dict.get("extracted_phases") or []
    if not isinstance(phases, list):
        phases = []

    packet = coherence_engine.update(payload_dict, phases)
    packet.trust_state = TrustState.CORE_PROCESSED.value
    return packet

