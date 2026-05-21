# SPEC Violation Baseline — Mobile Node (`main` @ 0b9cce1)

**Date:** 2026-05-21
**Auditor:** Kimi Code CLI (k2.6)
**Canonical Law:** `V3_DSLV-ZPDI_LIVING_MASTER.md` Rev 4.3.0
**Scope:** `zpdi_mobile_node.py`, `zpdi_verifier.py`, `edge_listener_stub.py`

---

## Summary

The `main` branch currently operates as a **flat-file data logger** with no three-layer architecture, no trust-state machine, no dual-stream routing, and no coherence engine. It is **NOT compliant** with SPEC-005, SPEC-005A, SPEC-006, SPEC-006.5, or SPEC-007. Because this device is a **Tier-2 Swarm node** (Pixel 9 Pro XL, no PPS, no GPSDO, no hardware clock), every packet it produces must be `SECONDARY_QUARANTINED`. The current codebase writes all data into a single HDF5 primary stream, which constitutes a **SPEC-003 total pipeline kill condition**.

---

## Kill Conditions Currently Violated

### SPEC-003 — DUAL-STREAM PROTOCOL (Total Pipeline Kill)

> **Kill Condition:** A single unstandardized data point in the primary HDF5 output constitutes a total pipeline failure.

- `zpdi_mobile_node.py` writes every sensor sample to `data/zpdi_stream.h5` via `HDF5Sink` without any trust-state gate or quarantine logic.
- This device is Tier-2 (mobile, no PPS, no GPSDO). **No packet from this device may ever reach `PRIMARY_ACCEPTED`.**
- **Violation:** All historical data in `data/zpdi_stream.h5` is exploratory/Tier-2 data that has been commingled with primary-stream semantics.
- **Fix required:** Implement `DualStreamRouter` (SPEC-007) and reject all non-`PRIMARY_ACCEPTED` packets from the HDF5 sink.

### SPEC-004B — TIER 2: SWARM NODES

> **Kill Condition:** Tier 2 data entering primary stream without Tier 1 corroboration.

- `zpdi_mobile_node.py` hardcodes `node: "dslv-zpdi/tier1"` in `_build_payload()`.
- The device is a Pixel 9 Pro XL running inside a Termux proot — it has no GPSDO, no PPS pin, no hardware clock, and no Intel i210-T1.
- **Violation:** Self-identifies as Tier-1 while being physically incapable of Tier-1 timing.
- **Fix required:** Set `hardware_tier=2` on all payloads and update node identity string.

### SPEC-005 — THREE-LAYER SOFTWARE DECOUPLING

> **Kill Condition:** Direct hardware calls in L2/L3; formatting logic in L1/L2; phase extraction in L2 (must occur in L1).

- The entire pipeline (sensor capture, payload construction, hashing, HDF5 formatting, WSS transport, SQLite caching) lives in a **single file**: `zpdi_mobile_node.py`.
- There is no `src/layer1_ingestion/`, `src/layer2_core/`, or `src/layer3_telemetry/` package structure.
- There is no separation of concerns; a sensor swap would require editing the monolith.
- **Fix required:** Port canonical three-layer package structure from Rev 3.4 baseline.

### SPEC-005A — LAYER 1: INGESTION API

> **Kill Condition:** Orphaned payload fields, missing schema version, missing trust-state validation.

#### SPEC-005A.1b — Hardened Universal Payload

The current `_build_payload()` returns a flat `dict` with these **missing mandatory fields**:

| Mandatory Field | Status in Current Code | Consequence |
|-----------------|------------------------|-------------|
| `spec_id` | ❌ Missing | No traceability to canonical spec |
| `schema_version` | ❌ Missing (`schema: 1` is non-canonical) | Silent breakage on contract evolution |
| `payload_uuid` | ❌ Missing | No deduplication or replay protection |
| `node_id` | ⚠️ Present as `"dslv-zpdi/tier1"` (wrong tier) | Identity mismatch |
| `sensor_id` | ❌ Missing | Cannot attribute to specific sensor |
| `modality` | ❌ Missing | No type-safe routing |
| `ingest_monotonic_ns` | ❌ Missing | No local ordering guarantee |
| `extracted_phases` | ❌ Missing | No phase vector for coherence engine |
| `gps_locked` | ❌ Missing | Cannot apply trust gate |
| `pps_jitter_ns` | ❌ Missing | Cannot enforce 10µs threshold |
| `calibration_valid` | ❌ Missing | No calibration gate |
| `calibration_age_s` | ❌ Missing | No drift tracking |
| `drift_percent` | ❌ Missing | No drift tracking |
| `source_path` | ❌ Missing | No provenance for audit |
| `trust_state` | ❌ Missing | No state machine |
| `quarantine_reason` | ❌ Missing | No audit trail for quarantine |
| `payload_checksum` | ⚠️ Present as `sha256` (full hex, not truncated) | Slight mismatch with SPEC-005A.3 |
| `hardware_tier` | ❌ Missing | Defaults to implicit Tier-1 |

#### SPEC-005A.2 — Payload Self-Validation

- No `validate()` method exists.
- No `KILLED` vs `SECONDARY_QUARANTINED` distinction.
- GPS-untrusted packets would be destroyed rather than quarantined (pre-Rev 3.1 behavior).
- **Fix required:** Implement `IngestionPayload.validate()` returning `(trust_state, reason)`.

#### SPEC-005A.3 — Serialization Gate

- `_build_payload()` serializes directly without validation.
- There is no gate that blocks `KILLED` packets from reaching sinks.
- **Fix required:** `to_json()` must call `validate()` first and return `None` for `KILLED`.

### SPEC-006 — KCET-ATLAS COHERENCE ENGINE

> **Kill Condition:** Any coherence calculation performed on packets that have not reached CAL_TRUSTED state, or any direct hardware access from this layer.

- `CoherenceScorer` does not exist in the current codebase.
- No `r_local`, `r_smooth`, or `r_global` is computed.
- No EWMA smoothing.
- No event confirmation logic.
- **Fix required:** Port `coherence.py` and `wiring.py` from Rev 3.4 baseline.

### SPEC-006.5 — LAYER 2 WIRING GATE

> **Kill Condition:** Any direct call to `CoherenceScorer.update()` from anywhere except this wiring function. Any Hilbert transform or phase-extraction math in this layer.

- No `wire_to_coherence()` function exists.
- No enum rehydration.
- No trust-state enforcement before coherence processing.
- **Fix required:** Implement `wire_to_coherence()` that blocks `SECONDARY_QUARANTINED`/`KILLED` packets.

### SPEC-007 — DUAL-STREAM ROUTER

> **Kill Condition:** Any packet reaching HDF5Writer without having passed through this router.

- No `DualStreamRouter` exists.
- `HDF5Sink.append()` accepts any `Payload` unconditionally.
- `FallbackLog` only receives WSS failover data, not quarantined data.
- **Fix required:** Implement `route_packet()` that enforces Tier-2 quarantine and routes by `r_smooth` threshold.

---

## Additional Findings (Non-Kill but Non-Compliant)

| Finding | File | Notes |
|---------|------|-------|
| `sha256` field embeds digest into body **before** hashing | `zpdi_mobile_node.py` | The current code hashes the body *without* the digest, then adds it. This is actually correct per the docstring, but the verifier strips the digest before re-hashing, which is also correct. **Not a violation.** |
| `edge_listener_stub.py` strips `sha256` before recompute | `edge_listener_stub.py` | Matches node logic. **Not a violation.** |
| `zpdi_verifier.py` only verifies HDF5 | `zpdi_verifier.py` | Does not verify secondary JSONL stream. Acceptable for now, but should be noted. |
| `SENSORS` tuple uses exact sensor names | `zpdi_mobile_node.py` | Correct per `termux-sensor -l`. **Not a violation.** |
| `h5py.vlen_dtype(bytes)` used | `zpdi_mobile_node.py` | Correct (post-3.0 API). **Not a violation.** |

---

## Remediation Plan

1. **STEP 1** (this document): Establish violation baseline.
2. **STEP 2**: Port canonical `src/` structure; create `mobile_ingestion.py`.
3. **STEP 3**: Implement `IngestionPayload` + trust-state validation.
4. **STEP 4**: Refactor `zpdi_mobile_node.py` to use Layer 1.
5. **STEP 5**: Port Layer 2 `CoherenceScorer` and `wiring.py`.
6. **STEP 6**: Implement `DualStreamRouter` (SPEC-007); reject non-primary from HDF5.
7. **STEP 7**: Port tests, add mobile-specific tests, run live validation.
8. **STEP 8**: Add log rotation and health watchdog.
9. **STEP 9**: Update docs (`TURNOVER.md`, `CHANGELOG.md`, `README.md`).
10. **STEP 10**: Merge, tag `v3.4.0-mobile`.

---

*APPEND-ONLY — this document is a snapshot in time. Do not modify after commit.*
