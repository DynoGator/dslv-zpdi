# SPEC-019 — Barometric Coherence Index (BCI) Engine

**Status:** ACTIVE
**Trust Tier:** Processed (Layer 2 Domain Coherence)
**Layer:** Layer 2 Core

## Overview

Computes the weighted cross-correlation between interior radon concentration R(t) and barometric pressure derivative magnitude |dP/dt|, modulated by relative humidity:

  χ(τ) = ⟨ R(t) · |dP/dt|(t − τ) ⟩ / (σ_R · σ_|dP/dt|) · w_RH

where w_RH = (1 − RH%/100).

The BCI is a **domain-specific child** of the master Γ(t) coherence framework. It does NOT replace the Kuramoto order parameter r(t) and does NOT depend on the degenerate null distribution.

## Pilot Thresholds

- **Default:** 0.65
- **Range:** 0.60–0.70 (configurable)
- **Label:** Explicitly marked `"pilot"` — not yet locked by seasonal/site baseline.
- **Review flag:** A recommendation for human/expert examination, NOT a verdict.

## Sub-Specs

### SPEC-019.1 — BCIResult dataclass
Canonical output: `chi`, `lag_hours`, `pilot_threshold`, `review_flag`, `review_reason`, `n_samples`, `sigma_r`, `sigma_dp`, `mean_rh_weight`.

### SPEC-019.2 — BarometricCoherenceEngine
Rolling-window engine with configurable window, lag, and pilot threshold. Computes |dP/dt| via central differences. Aligns radon and pressure series with lag τ.

### SPEC-019.3 — Ingestion
`ingest(timestamp_utc, radon_pCiL, pressure_hPa, rh_pct)` appends observations to rolling deques.

### SPEC-019.4 — Computation
`compute()` returns a `BCIResult` when sufficient samples exist (≥ window/2). Chi is clamped to [-1, 1]. Returns None when data is insufficient.

### SPEC-019.5 — Test suite
Unit tests prove:
- Correlated synthetic series raises review_flag
- Uncorrelated synthetic series clears review_flag
- High humidity reduces weighted score vs low humidity
- Extreme values do not escape [-1, 1]
- Reset clears state
- Lag alignment is respected

## Kill Conditions
- Presenting BCI as a certified verdict rather than a pilot review flag → scientific dishonesty
- Depending on the degenerate Kuramoto null distribution → inherited bug
- Using BCI to override or modify the certified radon report → contract breach
