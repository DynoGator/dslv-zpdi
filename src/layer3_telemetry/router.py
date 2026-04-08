"""
DSLV-ZPDI Layer 3 — Dual-Stream Router
SPEC-005C | Trust Tier: Rendered (Tier 3)
"""

class DualStreamRouter:
    """SPEC-005C.1 — Dual-Stream Routing Engine"""
    
    def route(self, scored_result: dict) -> str:
        """SPEC-005C.1 — Determine if data goes to Primary or Secondary stream"""
        if scored_result.get('hardware_tier', 2) != 1:
            return 'SECONDARY'
            
        if not scored_result.get('gps_locked', False):
            return 'SECONDARY'
            
        if not scored_result.get('calibration_valid', False):
            return 'SECONDARY'
            
        return 'PRIMARY'
