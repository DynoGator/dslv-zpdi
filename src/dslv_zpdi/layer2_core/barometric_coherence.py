"""
SPEC-019 | Trust Tier: Processed (Layer 2 Domain Coherence)
Barometric Coherence Index (BCI) engine.

Computes the weighted cross-correlation between interior radon concentration
and barometric pressure derivative magnitude, modulated by relative humidity.

  χ(τ) = ⟨ R(t) · |dP/dt|(t − τ) ⟩ / (σ_R · σ_|dP/dt|) · w_RH

where w_RH = (1 − RH%/100).

  R(t)      = interior radon moving average (pCi/L)
  |dP/dt|   = magnitude of barometric derivative (Darcy pump strength, hPa/h)

Pilot thresholds (0.60–0.70) are configurable and explicitly labeled as
"pilot — not yet locked by seasonal/site baseline."  The review flag is a
recommendation for human/expert examination, NOT a verdict.

The BCI is a domain-specific child of the master Γ(t) coherence framework;
it does NOT replace or depend on the Kuramoto order parameter r(t).
"""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

logger = logging.getLogger("dslv-zpdi.bci")


@dataclass
class BCIResult:
    """SPEC-019.1 — BCI computation result."""

    timestamp_utc: float
    chi: float
    lag_hours: float
    pilot_threshold: float
    review_flag: bool
    review_reason: str
    n_samples: int
    sigma_r: float
    sigma_dp: float
    mean_rh_weight: float


class BarometricCoherenceEngine:
    """SPEC-019.2 — BCI engine with rolling window and configurable pilot threshold."""

    def __init__(
        self,
        window_minutes: int = 120,
        lag_minutes: int = 0,
        pilot_threshold: float = 0.65,
        threshold_label: str = "pilot",
    ):
        """
        Args:
            window_minutes: Rolling correlation window in minutes.
            lag_minutes:    Lag τ between radon and pressure derivative (minutes).
            pilot_threshold: Review-flag threshold (0.60–0.70 pilot range).
            threshold_label: Must be "pilot" until site-seasonal baseline is locked.
        """
        self.window_minutes = window_minutes
        self.lag_minutes = lag_minutes
        self.pilot_threshold = pilot_threshold
        self.threshold_label = threshold_label

        self._radon: deque = deque(maxlen=window_minutes * 2)
        self._pressure: deque = deque(maxlen=window_minutes * 2)
        self._rh: deque = deque(maxlen=window_minutes * 2)
        self._timestamps: deque = deque(maxlen=window_minutes * 2)

        self._last_result: Optional[BCIResult] = None

    def ingest(
        self,
        timestamp_utc: float,
        radon_pCiL: float,
        pressure_hPa: float,
        rh_pct: Optional[float] = None,
    ):
        """SPEC-019.3 — Ingest a new observation triple."""
        self._timestamps.append(timestamp_utc)
        self._radon.append(radon_pCiL)
        self._pressure.append(pressure_hPa)
        self._rh.append(rh_pct if rh_pct is not None else 50.0)

    def compute(self) -> Optional[BCIResult]:
        """SPEC-019.4 — Compute BCI from the current rolling window."""
        if len(self._radon) < self.window_minutes // 2:
            return None  # Insufficient data

        # Build aligned arrays
        t = np.array(self._timestamps)
        r = np.array(self._radon)
        p = np.array(self._pressure)
        rh = np.array(self._rh)

        # Compute |dP/dt| in hPa/hour via central difference
        dt_hours = np.diff(t) / 3600.0
        dp = np.diff(p)
        # Avoid division by zero; pad with nan at edges
        dp_dt = np.full_like(p, np.nan, dtype=np.float64)
        with np.errstate(divide="ignore", invalid="ignore"):
            dp_dt[1:-1] = np.abs(dp[1:] + dp[:-1]) / (dt_hours[1:] + dt_hours[:-1])

        # Lag alignment: shift pressure derivative backward by lag_minutes
        lag_idx = max(1, int(round(self.lag_minutes)))
        if len(r) <= lag_idx:
            return None

        r_aligned = r[lag_idx:]
        dp_aligned = dp_dt[:-lag_idx] if lag_idx > 0 else dp_dt
        rh_aligned = rh[lag_idx:]

        # Trim to common length
        n = min(len(r_aligned), len(dp_aligned))
        if n < 10:
            return None

        r_vec = r_aligned[:n]
        dp_vec = dp_aligned[:n]
        rh_vec = rh_aligned[:n]

        # Drop any nan pairs
        valid = ~(np.isnan(r_vec) | np.isnan(dp_vec))
        if valid.sum() < 10:
            return None

        r_vec = r_vec[valid]
        dp_vec = dp_vec[valid]
        rh_vec = rh_vec[valid]

        sigma_r = float(np.std(r_vec, ddof=1))
        sigma_dp = float(np.std(dp_vec, ddof=1))
        if sigma_r == 0 or sigma_dp == 0:
            return None

        # Hydro-dielectric weight: w_RH = 1 − RH%/100
        # RH near 100% → weight near 0 (high humidity suppresses radon exhalation)
        # RH near 0%   → weight near 1
        rh_weights = 1.0 - (rh_vec / 100.0)
        rh_weights = np.clip(rh_weights, 0.0, 1.0)
        mean_rh_weight = float(np.mean(rh_weights))
        if mean_rh_weight <= 0:
            return None

        # Weighted covariance numerator
        r_mean = np.mean(r_vec)
        dp_mean = np.mean(dp_vec)
        numerator = np.mean(rh_weights * (r_vec - r_mean) * (dp_vec - dp_mean))

        # Normalize by mean weight so chi stays bounded by [-1, 1] regardless of RH
        chi = float(numerator / (mean_rh_weight * sigma_r * sigma_dp))
        # Clamp to [-1, 1] to protect against numeric outliers
        chi = max(-1.0, min(1.0, chi))

        review = chi >= self.pilot_threshold
        reason = ""
        if review:
            reason = (
                f"BCI {chi:.2f} exceeds pilot threshold {self.pilot_threshold:.2f} "
                f"({self.threshold_label} — not yet locked by seasonal/site baseline)"
            )

        result = BCIResult(
            timestamp_utc=float(t[-1]),
            chi=round(chi, 4),
            lag_hours=self.lag_minutes / 60.0,
            pilot_threshold=self.pilot_threshold,
            review_flag=review,
            review_reason=reason,
            n_samples=int(valid.sum()),
            sigma_r=round(sigma_r, 4),
            sigma_dp=round(sigma_dp, 4),
            mean_rh_weight=round(mean_rh_weight, 4),
        )
        self._last_result = result
        return result

    @property
    def last_result(self) -> Optional[BCIResult]:
        return self._last_result

    def reset(self):
        """Clear all history — used at session boundaries."""
        self._radon.clear()
        self._pressure.clear()
        self._rh.clear()
        self._timestamps.clear()
        self._last_result = None
