"""
SPEC-006.5 | Trust Tier: Processed (Layer 2 Wiring) — Rev 3.1
Canonical wiring between Layer 1 ingestion JSON and CoherenceScorer.

Rev 3.1 FIXES:
  - Enum rehydration from string (fixes silent routing failure)
  - Phase extraction REMOVED (phases come from Layer 1 via extracted_phases)
  - No scipy imports (Layer 2 is hardware-agnostic)
"""
import json
from typing import Optional

from dslv_zpdi.layer1_ingestion.payload import SensorModality

from .coherence import CoherencePacket, CoherenceScorer

coherence_engine = CoherenceScorer()


def wire_to_coherence(json_payload: str) -> Optional[CoherencePacket]:
    """SPEC-006.5a — Layer 2 Wiring (Rev 3.1)
    Called by DualStreamRouter after every Layer 1 emission.
    Never called directly from Layer 1 or Layer 3.
    """
    if not json_payload:
        return None

    try:
        payload_dict = json.loads(json_payload)
    except json.JSONDecodeError:
        return None

    # Rev 3.1 FIX: Rehydrate enum from string for type-safe comparison
    modality_str = payload_dict.get('modality', '')
    try:
        SensorModality(modality_str)
    except ValueError:
        # Unknown modality — if it's a mobile modality, allow it through
        if modality_str not in {
            "accel", "magnetometer", "barometer",
            "gyroscope", "rotation_vector", "geomagnetic_rotation", "gravity",
        }:
            return None  # Unknown modality = silent kill

    # State machine enforcement (Section 5.2B)
    trust_state = payload_dict.get('trust_state', '')
    if trust_state in ["SECONDARY_QUARANTINED", "KILLED"]:
        return None  # Do not process — these packets go to secondary stream only
    if trust_state not in ["TIME_TRUSTED", "CAL_TRUSTED"]:
        return None  # Insufficient trust gate

    # Rev 3.1 FIX: Read pre-extracted phases from Layer 1 (NO Hilbert transform here)
    phases = payload_dict.get('extracted_phases') or []

    coherence_packet = coherence_engine.update(payload_dict, phases)
    coherence_packet.trust_state = "CORE_PROCESSED"
    return coherence_packet


def wire_mobile_to_coherence(payload_dict: dict) -> Optional[CoherencePacket]:
    """Mobile-specific wiring that bypasses the Tier-1 trust gate.

    Tier-2 packets are inherently SECONDARY_QUARANTINED, but we still
    compute coherence scores for categorisation (noise / structured /
    anomalous) within the secondary stream per SPEC-007 mobile router.
    """
    if not payload_dict:
        return None

    modality_str = payload_dict.get('modality', '')
    try:
        SensorModality(modality_str)
    except ValueError:
        if modality_str not in {
            "accel", "magnetometer", "barometer",
            "gyroscope", "rotation_vector", "geomagnetic_rotation", "gravity",
        }:
            return None

    trust_state = payload_dict.get('trust_state', '')
    if trust_state == "KILLED":
        return None

    phases = payload_dict.get('extracted_phases') or []
    packet = coherence_engine.update(payload_dict, phases)
    packet.trust_state = "CORE_PROCESSED"
    return packet
