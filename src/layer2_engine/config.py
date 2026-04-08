"""
DSLV-ZPDI Layer 2 — Engine Configuration
SPEC-005B | Trust Tier: Processed (Tier 2)
"""
from dataclasses import dataclass

@dataclass
class ZPDIConfig:
    """SPEC-005B.1a — Engine Configuration Block"""
    noise_ceiling: float = 0.15
    anomaly_threshold: float = 0.40
    ewma_alpha: float = 0.2
    min_confirming_nodes: int = 4
    confirmation_window_ms: float = 300.0
    rf_weight_multiplier: float = 3.0
    optical_r_ceiling: float = 0.48
    drift_check_interval_s: int = 86400
    drift_recal_threshold: float = 0.20
