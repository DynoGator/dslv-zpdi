# SPEC-020 — 48-Hour Radon Validation Session Orchestrator

**Status:** ACTIVE
**Trust Tier:** Session Orchestration
**Layer:** Orchestrator

## Overview

Coordinates a named 48-hour measurement session binding the RadonEye Pro (certified CRM), Pixel 9 Pro XL (Tier 2 mobile node), and LBE-1421 GPSDO (clock authority). Ingests telemetry on native cadences, computes BCI in real-time, writes to the extended HDF5 envelope, and emits a compound `.h5` audit package + human-readable summary at completion.

## Resilience

- Session state cached to JSON every 60 s.
- `resume()` reconstructs an in-flight session from cache.
- If 48 h has already elapsed on resume, finalizes immediately.

## Certified / Forensic Separation

- Native certified report: archived read-only in `/certified_crm` with `WARNING` attr.
- All other data: forensic context in separate branches.
- The two domains are written by different methods and can never be conflated.

## Sub-Specs

### SPEC-020.1 — SessionConfig
Configurable parameters: session name, operator ID, output directory, device addresses, BCI window and threshold, simulator mode.

### SPEC-020.2 — SessionState
Serializable state: session ID, timestamps, sample counts, status, timing health, error log.

### SPEC-020.3 — RadonSessionOrchestrator
Manages lifecycle: `start()`, `stop()`, `finalize()`, `run()` (async main loop), `run_sync()`, `resume()`.

### SPEC-020.4 — Main loop
Async loop ingests radon every 10 min, atmosphere/space weather/BCI every 1 h, mobile node every 30 min, caches state every 60 s. Exits when 48 h elapsed or stop requested.

### SPEC-020.5 — Resume
Reads cached JSON state. Re-initializes HDF5 writer and ingestors. Returns False if no cache or session already completed.

### SPEC-020.6 — Test suite
Tests for initialization, file creation, finalize/summary generation, cache roundtrip, resume logic, short async run, and stop request.

## Kill Conditions
- Conflating certified report with forensic data → contract breach
- Losing samples because of a session restart → pipeline violation
- Running without simulator mode when hardware is absent → undefined behavior (caller must set `simulator_mode=True`)
