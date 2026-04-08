"""
DSLV-ZPDI Layer 2 — Payload Deserialization
SPEC-005B | Trust Tier: Processed (Tier 2)
"""
import json
import logging
from typing import Optional

def deserialize_payload(json_str: str) -> Optional[dict]:
    """SPEC-005B.2a — Inbound Payload Parser"""
    REQUIRED_FIELDS = [
        'node_id', 'sensor_id', 'modality', 
        'timestamp_utc', 'raw_value', 'gps_locked',
        'calibration_valid', 'hardware_tier'
    ]
    
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logging.error(f"[SPEC-005B.2a] JSON decode failed: {e}")
        return None
    
    for f in REQUIRED_FIELDS:
        if f not in data:
            logging.warning(f"[SPEC-005B.2a] KILL: missing field '{f}'")
            return None
    
    if not data.get('gps_locked', False):
        logging.warning("[SPEC-005B.2a] KILL: GPS not locked at source")
        return None
        
    if not data.get('calibration_valid', False):
        logging.warning("[SPEC-005B.2a] KILL: calibration invalid at source")
        return None
        
    return data
