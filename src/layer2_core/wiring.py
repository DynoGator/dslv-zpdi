"""
SPEC-006.5 | Trust Tier: Processed (Layer 2 Wiring) — Rev 3.1
"""
import json
from typing import Optional
from .coherence import CoherenceScorer, CoherencePacket
from ..layer1_ingestion.payload import SensorModality

coherence_engine = CoherenceScorer()

def wire_to_coherence(json_payload: str) -> Optional[CoherencePacket]:
    """SPEC-006.5a — Layer 2 Wiring (Rev 3.1)"""
    if not json_payload: return None
    try:
        payload_dict = json.loads(json_payload)
    except json.JSONDecodeError:
        return None

    modality_str = payload_dict.get('modality', '')
    try:
        SensorModality(modality_str) 
    except ValueError:
        return None

    trust_state = payload_dict.get('trust_state', '')
    if trust_state in ["SECONDARY_QUARANTINED", "KILLED"]: return None  
    if trust_state not in ["TIME_TRUSTED", "CAL_TRUSTED"]: return None  

    phases = payload_dict.get('extracted_phases') or []
    coherence_packet = coherence_engine.update(payload_dict, phases)
    coherence_packet.trust_state = "CORE_PROCESSED"
    return coherence_packet
