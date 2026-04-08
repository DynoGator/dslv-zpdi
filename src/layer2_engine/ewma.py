"""
DSLV-ZPDI Layer 2 — EWMA Smoothing
SPEC-005B | Trust Tier: Processed (Tier 2)
"""
from typing import Optional

class EWMAFilter:
    """SPEC-005B.3a — Exponentially Weighted Moving Average"""
    def __init__(self, alpha: float = 0.2):
        self.alpha = alpha
        self.value: Optional[float] = None

    def update(self, new_sample: float) -> float:
        """SPEC-005B.3a — Update filter with new sample"""
        if self.value is None:
            self.value = new_sample
        else:
            self.value = self.alpha * new_sample + (1 - self.alpha) * self.value
        return self.value

    def reset(self):
        """SPEC-005B.3a — Reset filter state"""
        self.value = None
