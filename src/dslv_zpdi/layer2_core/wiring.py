"""
SPEC-006.5 | Trust Tier: Processed (Layer 2 Wiring)
Rev 3.2 — enum rehydration, trust gating, phase extraction handoff, baseline status exposure.
"""

import json
from typing import Optional

from dslv_zpdi.core.states import TrustState
from dslv_zpdi.layer1_ingestion.payload import SensorModality
from dslv_zpdi.layer2_core.coherence import CoherencePacket, CoherenceScorer

coherence_engine = CoherenceScorer()


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
    if trust_state not in {TrustState.TIME_TRUSTED.value, TrustState.CAL_TRUSTED.value}:
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
