"""
DSLV-ZPDI Layer 2 — Coherence Scoring Engine
SPEC-005B | Trust Tier: Processed (Tier 2)
"""
from collections import deque
from typing import Optional, Dict
from .config import ZPDIConfig
from .ewma import EWMAFilter

class CoherenceScorer:
    """SPEC-005B.4a — Operational Coherence Calculator"""
    
    def __init__(self, config: ZPDIConfig):
        """SPEC-005B.4a — Initialize Scorer State"""
        self.config = config
        self.filters: Dict[str, EWMAFilter] = {}
        self.event_buffer: deque = deque(maxlen=10000)

    def score_payload(self, payload: dict) -> dict:
        """SPEC-005B.4b — Single-Payload Scoring"""
        node_id = payload['node_id']
        modality = payload['modality']
        
        filter_key = f"{node_id}:{modality}"
        if filter_key not in self.filters:
            self.filters[filter_key] = EWMAFilter(self.config.ewma_alpha)
        
        raw_r = self._extract_coherence(payload)
        
        if modality == 'rf_sdr':
            weighted_r = raw_r * self.config.rf_weight_multiplier
        else:
            weighted_r = min(raw_r, self.config.optical_r_ceiling)
            
        smoothed_r = self.filters[filter_key].update(weighted_r)
        
        if smoothed_r < self.config.noise_ceiling:
            classification = "NOISE"
        elif smoothed_r < self.config.anomaly_threshold:
            classification = "STRUCTURED_BACKGROUND"
        else:
            classification = "ANOMALOUS_CANDIDATE"
            
        scored = {
            'spec_id': 'SPEC-005B.4b',
            'node_id': node_id,
            'sensor_id': payload['sensor_id'],
            'modality': modality,
            'timestamp_utc': payload['timestamp_utc'],
            'raw_r': raw_r,
            'weighted_r': weighted_r,
            'smoothed_r': smoothed_r,
            'classification': classification,
            'hardware_tier': payload['hardware_tier'],
            'gps_locked': payload.get('gps_locked', False),
            'calibration_valid': payload.get('calibration_valid', False),
            'pps_jitter_ns': payload.get('pps_jitter_ns', 0.0),
        }
        
        self.event_buffer.append(scored)
        return scored

    def check_global_confirmation(self, timestamp: float) -> Optional[dict]:
        """SPEC-005B.4c — Multi-Node Global Confirmation"""
        window_start = timestamp - (self.config.confirmation_window_ms / 1000.0)
        
        candidates = [
            e for e in self.event_buffer
            if e['classification'] == 'ANOMALOUS_CANDIDATE'
            and window_start <= e['timestamp_utc'] <= timestamp
        ]
        
        confirming_nodes = set(e['node_id'] for e in candidates)
        
        if len(confirming_nodes) >= self.config.min_confirming_nodes:
            return {
                'spec_id': 'SPEC-005B.4c',
                'event_type': 'GLOBAL_CONFIRMATION',
                'timestamp_utc': timestamp,
                'confirming_nodes': list(confirming_nodes),
                'node_count': len(confirming_nodes),
                'candidate_details': candidates,
            }
        return None

    def _extract_coherence(self, payload: dict) -> float:
        """SPEC-005B.4d — Raw Coherence Extraction"""
        # Implementation depends on modality. Stubbed for Phase 1.
        return 0.0
