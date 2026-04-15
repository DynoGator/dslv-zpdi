# DSLV-ZPDI Refinement Report — 2026-04-11

> **ARCHITECTURE UPDATE (2026-04-11 onwards):** This report documents the pre-pivot refinement session. The project has since executed the **Phase 2A RF Metrology Pivot**. The current Tier 1 baseline is **Raspberry Pi 5 / HackRF One / Leo Bodnar LBE-1420 GPSDO**. The Intel i210-T1 / PTP / RTL-SDR path discussed herein has been formally deprecated. See `docs/ARCH-PHASE-2A-PIVOT.md` for the canonical current architecture.

**Evaluator:** Claude Opus 4.6 (Lead Software Engineer, DSLV-ZPDI)  
**Operator:** Joseph R. Fross — Resonant Genesis LLC / DynoGator  
**Repo State:** Rev 4.0.2.4 → Rev 4.0.3 (post-refinement)

---

## Baseline State

### Orphan Checker (pre-changes)
```
OK: no rogue nodes and no orphaned SPEC claims.
```

### Test Suite (pre-changes)
```
19 passed in 0.14s
```

All 19 tests passing, zero orphan violations at session start.

---

## Findings

### SPEC-006 — KCET-ATLAS Coherence Engine (`src/dslv_zpdi/layer2_core/coherence.py`)

| # | Finding | Severity | File:Line |
|---|---------|----------|-----------|
| 1 | **EWMA smoothing not implemented.** `update()` set `r_smooth = r_local` directly, bypassing the mandated formula `r_smooth(t) = α·r(t) + (1−α)·r_smooth(t−1)` with α=0.2 per Section 5.5.3. Every packet's smoothed value equaled its instantaneous value — eliminating the temporal dampening the spec requires. | **Critical** | `coherence.py:185` |
| 2 | **Global R(t) not weighted by modality.** `compute_global_r()` used a simple `np.mean()` instead of the weighted formula from Section 5.5.2 where `w_m = 3` for RF nodes. The comment stated "Simple mean for now, Phase 2A will implement." This is not a Phase 2A item — the formula is part of SPEC-006. | **Critical** | `coherence.py:128-134` |
| 3 | **No per-node EWMA history tracking.** The original code lacked the `deque`-based history required for EWMA computation and multi-node event confirmation within the sliding window. | **Major** | `coherence.py` |
| 4 | **Event confirmation used single-node r_local instead of r_smooth.** Without EWMA history, `_check_global_confirmation()` could not evaluate smoothed values across nodes within the 300ms window. | **Major** | `coherence.py` |

### SPEC-009 — Environmental Baseline Learning (`src/dslv_zpdi/layer2_core/coherence.py`)

| # | Finding | Severity | File:Line |
|---|---------|----------|-----------|
| 5 | **No three-state FSM enum.** The spec mandates `NOT_STARTED → LEARNING → LOCKED`. The code used a boolean `baseline_learning_mode` which conflated "never started" with "locked" (both `False`). | **Critical** | `coherence.py:48` |
| 6 | **No state regression prevention.** `start_baseline()` could be called even after the baseline was finalized, resetting a LOCKED baseline back to LEARNING. | **Major** | `coherence.py:68-73` |
| 7 | **72-hour duration gate not enforced.** `finalize_baseline()` only checked sample count, not elapsed time. A baseline could be finalized after 10 samples collected in 10 seconds. | **Major** | `coherence.py:136-156` |

### SPEC-005A — Layer 1 Ingestion (`src/dslv_zpdi/layer1_ingestion/payload.py`)

| # | Finding | Severity | File:Line |
|---|---------|----------|-----------|
| 8 | **SensorModality enum mismatch.** Code defined `MAGNETOMETER` and `INERTIAL`. Spec (Section 5.3, 5.5.1) mandates `THERMAL` and `ACOUSTIC`. Any packet with modality `thermal` or `acoustic` would be silently killed by the wiring layer's enum validation. | **Critical** | `payload.py:15-19` |

### SPEC-003 / SPEC-007 — Dual-Stream Protocol (`src/dslv_zpdi/layer3_telemetry/router.py`)

| # | Finding | Severity | File:Line |
|---|---------|----------|-----------|
| 9 | **Third routing stream "PRIMARY_CANDIDATE".** The router returned `RouteStream.PRIMARY_CANDIDATE` as a routing destination. SPEC-003 mandates exactly two streams: PRIMARY and SECONDARY. `PRIMARY_CANDIDATE` is a trust state, not a routing stream. Packets with structured background (0.15 ≤ r < 0.40) without event confirmation must route to SECONDARY. | **Critical** | `router.py:58-63` |
| 10 | **`RouteStream` enum contained `PRIMARY_CANDIDATE`.** This third enum member should not exist as a routing stream. | **Minor** | `states.py:25-28` |

### SPEC-007 — HDF5 Writer (`src/dslv_zpdi/layer3_telemetry/hdf5_writer.py`)

| # | Finding | Severity | File:Line |
|---|---------|----------|-----------|
| 11 | **HDF5Writer referenced non-existent `RouteStream.PRIMARY_CANDIDATE`.** The `ingest()` method checked for a `PRIMARY_CANDIDATE` stream that no longer exists after the routing fix. | **Minor** | `hdf5_writer.py:63` |

### Test Suite

| # | Finding | Severity | File:Line |
|---|---------|----------|-----------|
| 12 | **`test_global_R` used exact float comparison.** The weighted global R(t) computation introduces floating-point imprecision; test used `==` instead of approximate comparison. | **Minor** | `test_pipeline.py:98` |
| 13 | **`test_outlier_detection` incompatible with EWMA smoothing.** Test sent 2 packets expecting immediate event confirmation, but EWMA dampening prevents r_smooth from reaching the threshold that quickly. Also tested with `min_nodes=4` default using only 1 node. | **Minor** | `test_coherence.py:22-37` |
| 14 | **No test coverage for SPEC-009 three-state FSM transitions**, duration gate, or regression prevention. | **Major** | `tests/` |
| 15 | **No test coverage for EWMA smoothing behavior** (dampening, convergence). | **Major** | `tests/` |
| 16 | **No test coverage for two-stream routing enforcement.** No test verified that only PRIMARY and SECONDARY are valid routing destinations. | **Major** | `tests/` |
| 17 | **No test coverage for weighted global R(t) modality weighting.** | **Major** | `tests/` |

---

## Changes Implemented

### Modified Files

| File | SPEC-ID | Description |
|------|---------|-------------|
| `src/dslv_zpdi/core/states.py` | SPEC-009, SPEC-003 | Added `BaselineState` enum (NOT_STARTED/LEARNING/LOCKED). Removed `PRIMARY_CANDIDATE` from `RouteStream` enum — only PRIMARY and SECONDARY are valid routing streams. |
| `src/dslv_zpdi/layer1_ingestion/payload.py` | SPEC-005A | Added `THERMAL` and `ACOUSTIC` to `SensorModality` enum per Section 5.3. Retained `MAGNETOMETER`/`INERTIAL` for forward compatibility. |
| `src/dslv_zpdi/layer2_core/coherence.py` | SPEC-006, SPEC-009 | **Full rewrite.** Implemented EWMA smoothing with α=0.2 per Section 5.5.3. Implemented weighted global R(t) per Section 5.5.2 (RF w=3, others w=1). Replaced boolean baseline flag with three-state FSM using `BaselineState` enum. Added state regression prevention (LOCKED → LEARNING blocked). Added 72-hour duration gate to `finalize_baseline()`. Added per-node deque history for sliding-window event confirmation. Event confirmation now uses dynamic threshold from baseline. |
| `src/dslv_zpdi/layer3_telemetry/router.py` | SPEC-003, SPEC-007 | Eliminated third routing stream. `PRIMARY_CANDIDATE` trust state packets now route to SECONDARY per SPEC-003. Baseline LOCKED gate preserved. |
| `src/dslv_zpdi/layer3_telemetry/hdf5_writer.py` | SPEC-007 | Updated `ingest()` to handle two-stream routing (removed `PRIMARY_CANDIDATE` stream reference). |
| `tests/test_coherence.py` | SPEC-006 | Refactored `test_outlier_detection` to account for EWMA dampening and use `min_nodes=1` for unit test isolation. |
| `tests/test_pipeline.py` | SPEC-006 | Fixed `test_global_R` to use approximate float comparison for weighted computation. |

### New Files

| File | SPEC-ID | Description |
|------|---------|-------------|
| `tests/test_spec009_fsm.py` | SPEC-009 | 7 tests covering: initial NOT_STARTED state, NOT_STARTED→LEARNING transition, LEARNING→LOCKED transition, LOCKED regression prevention, JSON persistence roundtrip, 72-hour duration gate enforcement, and finalize-from-NOT_STARTED rejection. |
| `tests/test_ewma_and_routing.py` | SPEC-006, SPEC-003, SPEC-007 | 5 tests covering: EWMA spike dampening, EWMA convergence, weighted global R(t) with modality weighting, two-stream-only routing enforcement, and structured-background-to-SECONDARY routing. |

### Post-Change Validation

- **Orphan checker:** `OK: no rogue nodes and no orphaned SPEC claims.`
- **Test suite:** `31 passed in 0.17s` (19 existing + 12 new)
- **Governing documents:** `V3_DSLV-ZPDI_LIVING_MASTER.md` and `MASTER_SPEC.md` confirmed unmodified.

---

## Remaining Work

### Requires Physical Hardware

| Item | SPEC-ID | Reason |
|------|---------|--------|
| Validate real PPS jitter via Intel i210-T1 on CM5 | SPEC-004A.1 | `hal_hardware.py` ioctl calls require `/dev/pps0` and physical PPS signal from u-blox. Cannot be tested in virtual environments. |
| Execute 72-hour SPEC-009 baseline at field site | SPEC-009 | Duration gate is now enforced in code. Actual field deployment required to collect real environmental r_smooth distribution. |
| Validate HDF5 output against physical sensor data | SPEC-007, Appendix E | HDF5 schema structure matches Appendix E in code, but no physical sensor data has traversed the full pipeline to produce a hardware-certified golden sample. |
| Deploy 4-node Tier 2 swarm with supercapacitor power | SPEC-004B, SPEC-008 | `SwarmIntegrityMonitor` is implemented but untested with real swarm node data. Regional baseline stats (`regional_baselines`) must be populated from field observations. |

### Requires Owner Decision

| Item | SPEC-ID | Reason |
|------|---------|--------|
| `MAGNETOMETER` and `INERTIAL` modalities lack spec coverage | SPEC-005A | These modalities exist in code but are not defined in Section 5.3 or Section 5.5.1 of the Living Master. They were retained for forward compatibility. Owner should either add them to the spec or remove them from code. |
| Orphan checker authority source | Tools | Currently parses `specs/` directory for SPEC-ID definitions. The evaluation prompt recommends parsing `MASTER_SPEC.md` directly. Current approach is robust (one spec file per SPEC-ID) but the canonical authority question should be settled by the owner. |
| `run_golden_sample.py` uses mock h5py | Tests | This test injects a `MockH5py` module into `sys.modules` to simulate HDF5 writing. It exercises the attestation path but does not validate real HDF5 file structure. Once `h5py` is available in the test environment, this should be refactored to use real file I/O. |

### Out of Scope for Automated Tooling

| Item | Reason |
|------|--------|
| PTP Monitor integration with MVIP-6 | `ptp_monitor.py:81` has a `_trigger_timing_quarantine()` stub marked "Phase 2B integration." Requires defining the MVIP-6 hook interface and cross-module event bus. |
| Visualization layer (Phase 3) | Per roadmap Section 8.1, visualization is downstream of persistence and not in scope for Phase 2A software hardening. |
| SPEC-010 checksum verification in HDF5Writer pipeline | `verify_packet_integrity()` exists in `hdf5_writer.py` but is never called in the `ingest()` path. The attestation uses a separate `content_sha256` computed at write time. Owner should decide whether to wire `verify_packet_integrity()` into the ingest pipeline or deprecate it. |

---

## Phase 2A Readiness Assessment

The software pipeline is substantially ready for hardware integration on the CM5 Tier 1 anchor node. The five critical correctness violations discovered in this session — missing EWMA smoothing, unweighted global R(t), absent three-state baseline FSM, wrong sensor modality enum, and a third routing stream violating SPEC-003 — have all been corrected and verified with 31 passing tests and a clean orphan check. The blocking items for Phase 2A are exclusively hardware-dependent: procurement and installation of the Intel i210-T1 NIC, physical PPS verification via `/dev/pps0`, and execution of the 72-hour SPEC-009 baseline at the first field site. No software changes are required before hardware commissioning can proceed. The recommended immediate next step is to run `tools/provision_tier1.py` on the first physical CM5 unit, verify PPS jitter < 50ns, and then invoke `CoherenceScorer.start_baseline()` to begin the 72-hour adaptive learning period.
