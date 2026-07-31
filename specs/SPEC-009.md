# SPEC-009 — Baseline Learning Finite-State Machine

**Status:** IMPLEMENTED  
**Revision:** 5.0.0  
**Depends on:** SPEC-006 (Coherence Analysis), SPEC-007 (HDF5 Persistence)  

## 1. Purpose

Define the baseline-learning state machine that gates PRIMARY-stream HDF5 output.
Before the node can declare *confirmed events*, it must learn what "normal"
background coherence looks like for its local RF environment. This prevents
ordinary noise and environmental phase drift from flooding the primary stream.

## 2. States

```text
NOT_STARTED → LEARNING → LOCKED
```

| State | Meaning |
|-------|---------|
| `NOT_STARTED` | Coherence engine has not yet begun collecting baseline samples. |
| `LEARNING` | Collecting `r_local` samples and persisting them atomically. No PRIMARY events declared. |
| `LOCKED` | Baseline threshold computed. PRIMARY routing enabled when `r_smooth` exceeds the threshold and an event window exists. |

## 3. Transition Conditions

### 3.1 NOT_STARTED → LEARNING

Triggered by `CoherenceScorer.start_baseline()`. The transition is idempotent:
if the engine is already `LEARNING`, samples and start time are preserved across
process restarts.

### 3.2 LEARNING → LOCKED

Triggered by `CoherenceScorer.finalize_baseline()`. The gate requires:

- `len(baseline_samples) >= DSLV_MIN_BASELINE_SAMPLES`
- `(now - baseline_started_utc) / 3600 >= DSLV_BASELINE_HOURS`

The threshold is normally computed as:

```text
threshold = max(mean(r_local) + 3 * std(r_local), 0.25)
```

For development or controlled environments, a fixed threshold may be supplied via
`DSLV_BASELINE_FIXED_THRESHOLD`.

### 3.3 LOCKED → (no restart)

Once `LOCKED`, the baseline cannot be restarted without deleting the persisted
baseline state file. This protects the learning investment from accidental
restarts.

## 4. Persistence

Baseline state is persisted atomically to `DSLV_BASELINE_STATE_PATH`
(default `/var/lib/dslv-zpdi/baseline.json`) using write-then-rename with `fsync`.
See SPEC-009.1 for persistence details.

## 5. Environment Parameters

| Variable | Default | Description |
|----------|---------|-------------|
| `DSLV_BASELINE_HOURS` | `72` | Minimum duration of the learning phase in hours. |
| `DSLV_MIN_BASELINE_SAMPLES` | `240` | Minimum number of `r_local` samples required. |
| `DSLV_BASELINE_STATE_PATH` | `/var/lib/dslv_zpdi/baseline.json` | Persisted baseline state file. |
| `DSLV_BASELINE_FIXED_THRESHOLD` | (unset) | Optional fixed event threshold used instead of the 3-sigma calculation. |

## 6. Operational Notes

- During `LEARNING`, every packet is routed to the secondary stream with reason
  `baseline_learning_active`.
- After `LOCKED`, the router uses the learned `dynamic_threshold` to distinguish
  confirmed PRIMARY events, structured-background PRIMARY_CANDIDATE records, and
  sub-threshold noise.
- Restarting the pipeline no longer resets an in-progress baseline; the engine
  reloads the persisted `LEARNING` state and continues from where it left off.
