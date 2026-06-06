# SPEC-016 — Pixel 9 Pro XL Mobile Node Bridge (Tier 2 Context)

**Status:** ACTIVE
**Trust Tier:** Tier 2 Mobile Node Context
**Layer:** Layer 1 Ingestion

## Overview

The Google Pixel 9 Pro XL (GrapheneOS) operates as a Tier 2 swarm node and internet hotspot. It contributes magnetometer, GPS vectoring/triangulation, low-res tamper-evidence camera frames, and opportunistic environmental sensors. All Pixel data is explicitly labeled `hardware_tier=2` and is **never** eligible for the Tier 1 primary institutional stream.

## Transport

**Primary:** HTTP polling over the PiRepo hotspot LAN (`10.42.0.0/24`).
The Pixel runs a lightweight JSON publisher inside Termux (documented in `docs/PIXEL_NODE_SETUP.md`).

**Fallback:** Simulator mode generates deterministic synthetic sensor data.

## Trust Scoring

`PixelTrustScorer` evaluates every poll and returns a `trust_score` (0.0–1.0) plus `trust_flags`:

| Flag | Trigger | Score Impact |
|------|---------|--------------|
| `no_gps` | Missing GPS fix | −0.3 |
| `coarse_gps` | Accuracy > 50 m | −0.2 |
| `no_magnetometer` | Missing magnetometer | −0.2 |
| `mag_anomaly` | Field magnitude outside 25–65 µT | −0.15 |
| `no_tamper_evidence` | Missing camera frame hash | −0.1 |
| `stale_data` | Pixel timestamp > 60 s old | −0.25 |
| `hotspot_drop` | HTTP unreachable, returning cached data | −0.3 |
| `unreachable` | HTTP unreachable, no cache | −0.5 |

Samples with `trust_score < trust_threshold` (default 0.5) are still logged to `/mobile_node_tier2` but carry a quarantine flag.

## Sub-Specs

### SPEC-016.1 — PixelTelemetry dataclass
Normalized Pixel telemetry with fields for all sensors plus trust metadata.

### SPEC-016.2 — Layer 1 payload serialization
`PixelTelemetry.to_ingestion_payload()` converts to a standard `IngestionPayload` with `hardware_tier=2` and modality inferred from available sensors (`gps_pps` if GPS present, else `magnetometer`).

### SPEC-016.3 — PixelTrustScorer
Computes trust score and flags from raw telemetry dict.

### SPEC-016.4 — PixelHttpTransport
Polls the Pixel's Termux JSON publisher with retries, latency tracking, and stale-data caching on hotspot drops.

### SPEC-016.5 — PixelSimulator
Deterministic synthetic sensor data for CI and offline development.

### SPEC-016.6 — PixelNodeBridge
Unified bridge with HTTP → SIM failover. Never raises; always returns telemetry.

### SPEC-016.7 — Test suite
Unit tests for trust scoring, simulator math, HTTP failover, and payload serialization.

### SPEC-016.8 — Safe float coercion
`_safe_float()` normalizes Termux API numeric strings to Python floats.

## Kill Conditions
- Tier 2 data entering PRIMARY stream without explicit quarantine label → pipeline violation
- Customer PII or real addresses transmitted off-node → HARD STOP
- Camera resolution > 640×480 in tamper-evidence mode → flag and downscale
