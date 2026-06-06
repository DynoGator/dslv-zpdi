"""
SPEC-019.5 — Barometric Coherence Index engine unit tests.

Proves the engine flags correlated series and clears uncorrelated series.
"""

import numpy as np
import pytest

from dslv_zpdi.layer2_core.barometric_coherence import (
    BarometricCoherenceEngine,
    BCIResult,
)


class TestBarometricCoherenceEngine:
    def _generate_series(
        self,
        n: int = 200,
        correlation: float = 0.0,
        noise_sigma: float = 0.3,
        base_radon: float = 4.0,
        base_pressure: float = 1013.0,
    ):
        """Generate synthetic radon and pressure series.

        Pressure is a sinusoid; radon is correlated with the *computed*
        central-difference derivative so the BCI sees a strong signal.
        """
        t = np.arange(n) * 600.0  # 10-minute intervals
        # Sinusoidal pressure: period = 40 samples (~6.7 h), amplitude = 10 hPa
        period = 40
        pressure = base_pressure + 10.0 * np.sin(2 * np.pi * np.arange(n) / period)
        # Central-difference derivative (matches BCI engine computation)
        dt = 600.0 / 3600.0  # 10 minutes in hours
        dp_dt = np.full(n, np.nan)
        dp_dt[1:-1] = np.abs((pressure[2:] - pressure[:-2]) / (2 * dt))
        dp_dt[0] = dp_dt[1]
        dp_dt[-1] = dp_dt[-2]
        # Radon: baseline + correlation * normalized derivative + noise
        dp_norm = (dp_dt - np.nanmean(dp_dt)) / (np.nanstd(dp_dt) + 1e-9)
        radon = base_radon + correlation * dp_norm * 2.0 + np.random.normal(0, noise_sigma, n)
        radon = np.clip(radon, 0.5, None)
        rh = np.full(n, 50.0)
        return t, radon, pressure, rh

    def test_correlated_series_raises_review_flag(self):
        np.random.seed(42)
        engine = BarometricCoherenceEngine(window_minutes=60, pilot_threshold=0.60)
        t, radon, pressure, rh = self._generate_series(n=200, correlation=1.2, noise_sigma=0.15)
        for i in range(len(t)):
            engine.ingest(t[i], radon[i], pressure[i], rh[i])
        result = engine.compute()
        assert result is not None
        assert result.chi >= 0.60
        assert result.review_flag is True
        assert "pilot" in result.review_reason
        assert result.n_samples >= 10

    def test_uncorrelated_series_clears_flag(self):
        np.random.seed(43)
        engine = BarometricCoherenceEngine(window_minutes=60, pilot_threshold=0.60)
        t, radon, pressure, rh = self._generate_series(n=200, correlation=0.0)
        for i in range(len(t)):
            engine.ingest(t[i], radon[i], pressure[i], rh[i])
        result = engine.compute()
        assert result is not None
        assert result.chi < 0.60
        assert result.review_flag is False
        assert result.review_reason == ""

    def test_insufficient_data_returns_none(self):
        engine = BarometricCoherenceEngine(window_minutes=120)
        # Only 5 samples
        for i in range(5):
            engine.ingest(i * 600.0, 4.0, 1013.0, 50.0)
        assert engine.compute() is None

    def test_rh_weighting_reduces_score_at_high_humidity(self):
        np.random.seed(44)
        engine_low = BarometricCoherenceEngine(window_minutes=60, pilot_threshold=0.60)
        engine_high = BarometricCoherenceEngine(window_minutes=60, pilot_threshold=0.60)
        t, radon, pressure, _ = self._generate_series(n=200, correlation=0.9)
        for i in range(len(t)):
            engine_low.ingest(t[i], radon[i], pressure[i], 30.0)
            engine_high.ingest(t[i], radon[i], pressure[i], 90.0)
        res_low = engine_low.compute()
        res_high = engine_high.compute()
        assert res_low is not None
        assert res_high is not None
        # Both should show strong correlation
        assert res_low.chi >= 0.60
        assert res_high.chi >= 0.60
        # Mean RH weight should be higher for the low-humidity series
        assert res_low.mean_rh_weight > res_high.mean_rh_weight

    def test_chi_clamped_to_unit_range(self):
        np.random.seed(45)
        engine = BarometricCoherenceEngine(window_minutes=60)
        # Inject strong but bounded correlation; chi should still stay in [-1,1]
        t, radon, pressure, rh = self._generate_series(n=200, correlation=2.0, noise_sigma=0.1)
        for i in range(len(t)):
            engine.ingest(t[i], radon[i], pressure[i], rh[i])
        result = engine.compute()
        assert result is not None
        assert -1.0 <= result.chi <= 1.0

    def test_reset_clears_state(self):
        np.random.seed(48)
        engine = BarometricCoherenceEngine(window_minutes=60)
        t, radon, pressure, rh = self._generate_series(n=100, correlation=0.8)
        for i in range(len(t)):
            engine.ingest(t[i], radon[i], pressure[i], rh[i])
        assert engine.compute() is not None
        engine.reset()
        assert engine.compute() is None
        assert engine.last_result is None

    def test_lag_alignment(self):
        np.random.seed(46)
        engine = BarometricCoherenceEngine(window_minutes=60, lag_minutes=30)
        t, radon, pressure, rh = self._generate_series(n=200, correlation=0.8)
        for i in range(len(t)):
            engine.ingest(t[i], radon[i], pressure[i], rh[i])
        result = engine.compute()
        assert result is not None
        assert result.lag_hours == 0.5

    def test_pilot_threshold_configurable(self):
        np.random.seed(47)
        engine = BarometricCoherenceEngine(window_minutes=60, pilot_threshold=0.70)
        t, radon, pressure, rh = self._generate_series(n=200, correlation=0.8)
        for i in range(len(t)):
            engine.ingest(t[i], radon[i], pressure[i], rh[i])
        result = engine.compute()
        assert result is not None
        assert result.pilot_threshold == 0.70
        assert "pilot" in result.review_reason or not result.review_flag
