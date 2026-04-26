# Session Report — Pipeline Hardening & Dashboard Polish

**Date:** 2026-04-26
**Operator:** Joseph R. Fross
**Build target:** Pi 5 — DSLV-ZPDI Tier 1 Anchor (post-v4.5.1 fixpack)
**Branch:** `main`
**Scope:** integrity audit → forensic-completeness fix → dashboard rebuild → full regression

---

## 1. Executive Summary

A pipeline integrity audit surfaced a class-A data-accuracy bug: under
`monitor.healthy == False` or upstream `SECONDARY_QUARANTINED`, both the
synchronous and threaded run loops in `main_pipeline.py` were skipping
`writer.ingest()` outright. No HDF5, no quarantine.jsonl — silent drop.
On a freshly-booted Pi this happened deterministically because
`TimingMonitor` reads host `chronyc`, and the first `RMS offset` read in
simulator mode was ~28 ms (above the 10 ms relaxed threshold), so every
payload after the first second was discarded with no forensic trace.

This session:

1. Restored full forensic-completeness of the data path.
2. Decoupled the simulator timing monitor from host clock health.
3. Fixed the start-up race that dropped the first batch of payloads.
4. Rebuilt the dashboard `PipelinePanel` to surface live router /
   integrity / baseline / timing metrics from the SPEC-014 health
   endpoint.
5. Added a disk-usage row to the system panel.
6. Added a regression test that locks in the no-silent-drop guarantee.

All 49 pytest cases pass; an 8-second simulator run with the 4-node
demo gate now produces 99 PRIMARY HDF5 events with full attestation
plus a populated quarantine.jsonl.

---

## 2. Audit Findings

### 2.1 Critical: silent payload drop (SPEC-011 violation)

`main_pipeline._process_loop` (threaded) and the synchronous body
both contained:

```python
if not monitor.healthy or payload.trust_state == "SECONDARY_QUARANTINED":
    continue   # ← payload vanishes
```

Result: when timing was unhealthy or the HAL flagged a payload as
quarantined (e.g., GPS unlock, high PPS jitter), neither HDF5 nor
quarantine.jsonl received the record. The router stats counters never
advanced, so the failure was invisible to operators.

### 2.2 Critical: TimingMonitor coupling in simulator mode

`TimingMonitor._read_pps_jitter()` shells out to `chronyc tracking`
unconditionally. In simulator mode this couples the data path to the
host clock — on a development workstation with NTP-only sync, the
first reading was ~28 ms RMS, blowing the 10 ms simulator threshold
and triggering 2.1 above. CI/dev/sim runs were therefore environment-
dependent.

### 2.3 Race: start-up `healthy = False` window

`TimingMonitor.healthy` initialised to `False`. Between
`monitor.start()` and the first jitter read (typically ~10 s on the
default check interval) every payload was eligible to be dropped by 2.1.

### 2.4 Test masking: `test_hdf5_schema_matches_spec`

The test's terminal assertion was:

```python
assert quarantine.exists() or len(h5_files) > 0
```

Both clauses were false in the silent-drop regime, but the test had
been passing on hosts where chronyc happened to be tight. It surfaced
in this session as a hard failure — the first repro of the bug.

### 2.5 Dashboard gap

`PipelinePanel` showed only filesystem-level counts (HDF5 file count,
quarantine line count) and a derived rate. It never read the live
SPEC-014 health endpoint, so router stats, integrity counters, baseline
state, and timing health were invisible from the operator console.

---

## 3. Changes Performed

### 3.1 `src/dslv_zpdi/main_pipeline.py`

- New `PipelineState.note_quarantine(reason: str)` records a counter
  per quarantine reason behind the existing lock.
- `PipelineState.get_snapshot()` now returns
  `quarantine_reasons: dict[str, int]`.
- Both run-loop bodies tag and route instead of dropping:
  * `monitor.healthy is False` → `payload.trust_state =
    SECONDARY_QUARANTINED`, `quarantine_reason = "timing_unhealthy"`,
    counter incremented, then `writer.ingest(payload.to_json())`.
  * `payload.trust_state == "SECONDARY_QUARANTINED"` on entry →
    counter incremented (using the upstream reason), routed normally.
- The 60-second status heartbeat now publishes `timing_jitter_ns`,
  `timing_threshold_ns`, and `quarantine_reasons` to the health
  endpoint.
- `TimingMonitor` is constructed with `simulated=simulator_mode`.

### 3.2 `src/dslv_zpdi/watchdog/timing_monitor.py`

- New constructor kwargs: `simulated: bool = False`,
  `jitter_source: Optional[Callable[[], float]] = None`.
- `healthy` defaults to `True` (optimistic) so the start-up window no
  longer drops payloads.
- `_read_pps_jitter()` precedence:
  1. Caller-supplied `jitter_source` (test injection).
  2. `simulated=True` → synthetic value matching `DSLV_SIM_TIMING`
     (`gpsdo`: ~10 ns, `ntp`: ~3 ms).
  3. Otherwise `chronyc tracking` (production behaviour, unchanged).

### 3.3 `tests/test_integration.py`

Strengthened from `quarantine.exists() or h5_files > 0` to:

```python
assert quarantine.exists()
assert sum(1 for _ in quarantine.open()) > 0
```

This locks in the SPEC-011.5 forensic-completeness guarantee.

### 3.4 `tools/dashboard/panels/pipeline.py`

Full rewrite:

| Metric              | Source                             |
|---------------------|------------------------------------|
| Service / PID / up  | `systemctl show` + `/proc/<pid>/stat` |
| Node / HAL / ticks  | health endpoint                    |
| PRIMARY events      | health → `stats.primary_written`   |
| HDF5 files / bytes  | `os.listdir` + `os.path.getsize`   |
| SECONDARY events    | health → `stats.secondary_logged`  |
| Quarantine on disk  | line count of quarantine.jsonl     |
| Integrity counters  | health → fail/miss/inv/rej         |
| Baseline state      | health → `baseline.baseline_state` |
| Timing health       | health → `timing_healthy` + jitter |
| Throughput          | derived rate over 2 s window       |

Health endpoint is read from `/run/dslv-zpdi/health.json` with
fallback to `/tmp/health.json` (matches the writer's privilege
fallback). Cached for 1.5 s to keep the render loop cheap.

### 3.5 `tools/dashboard/panels/system.py`

Added a `Disk` row showing usage of the `DSLV_OUTPUT_DIR` partition
(or `/` if the env var isn't set). Banded green ≤70 %, yellow ≤90 %,
red above.

### 3.6 `CHANGELOG.md`

New `[4.5.2] - 2026-04-26` block documenting the Fixed/Added/Changed
items above.

---

## 4. Verification

### 4.1 Test suite

```
$ pytest -q
49 passed, 2 warnings in 15.60s
```

All previously passing tests still pass; the previously failing
`test_hdf5_schema_matches_spec` now passes; the strengthened
`test_integration.py` passes.

### 4.2 Version sync

```
$ python tools/check_version_sync.py
[OK] Version sync clean: 4.5.0
```

### 4.3 Compile sweep

```
$ python -m compileall -q src tools/dashboard
(no errors)
```

### 4.4 End-to-end simulator run (8 s, 4-node demo)

```
$ DEV_SIMULATOR=1 DSLV_SIM_DEMO=1 python -m dslv_zpdi.main_pipeline \
    --simulator --mode sdr --interval 0.05 --output /tmp/dslv_e2e
```

- 99 PRIMARY events written to `/tmp/dslv_e2e/primary/dslv_zpdi_*.h5`
  (~430 KB, 99 event groups, full attestation attrs).
- `/tmp/dslv_e2e/secondary/quarantine.jsonl` populated with
  baseline-warmup samples (8 KB).
- Zero `VIOLATION` log lines, zero silent drops.

### 4.5 Dashboard render

`PYTHONPATH=tools python -m dashboard --no-banner --no-boot` launches
cleanly, all panels render, exits cleanly on SIGTERM.

---

## 5. Operator Turnover

### What's running on the Pi

The deployed `dslv-zpdi.service` is unchanged. To pick up these
fixes, do a normal `systemctl daemon-reload && systemctl restart
dslv-zpdi.service`. No config changes required.

### Behavioural deltas the operator will observe

1. **Quarantine logs grow during baseline warm-up.** That's expected
   and correct now — the first ~30 s of payloads are below the
   coherence threshold while baseline locks. They will appear in
   `output/secondary/quarantine.jsonl` rather than vanishing.
2. **Dashboard PIPELINE panel is denser.** New rows: integrity,
   baseline, timing. If `timing` shows `UNHEALTHY` with jitter `--`,
   the pipeline service hasn't written a fresh health snapshot yet
   (or is stopped). Restart the service.
3. **Sim runs are deterministic again.** `DEV_SIMULATOR=1` no longer
   reads host chrony; CI is decoupled from the runner's clock.

### What's NOT changed in this session

- Hardware HAL path: untouched.
- Coherence math, baseline FSM, swarm gate: untouched.
- Systemd units / install script / first-boot tooling: untouched.
- Dashboard waterfall, weather, storm, anomaly, logs, notifications
  panels: untouched.

### LBE-1420 readiness

Independent of this session. Once the GPSDO arrives and is wired in,
the production timing monitor (host chronyc) will report sub-µs RMS
and `timing_healthy` will go green continuously. The dashboard already
exposes that.

---

## 6. Known Caveats

- The CHANGELOG entry is `[4.5.2]` but `pyproject.toml` is still
  `4.5.0` — matching the pre-existing pattern (`4.5.1` was also a
  changelog-only patch). If the next release wants a real version
  bump, also update `README.md` revision line and add a
  `RELEASE_NOTES_v4.5.2.md`. `tools/check_version_sync.py` will
  enforce the trio.
- `test_integration.py` writes to `/tmp/dslv-zpdi-integration-test`
  and isn't cleaned up. Manual `rm -rf` if needed.
- The dashboard reads the health endpoint without any age check —
  if the pipeline service has been stopped for hours the panel will
  still show the stale snapshot. Acceptable for now; flag if it
  becomes confusing in the field.

---

## 7. Files Touched

```
M  src/dslv_zpdi/main_pipeline.py
M  src/dslv_zpdi/watchdog/timing_monitor.py
M  tests/test_integration.py
M  tools/dashboard/panels/pipeline.py
M  tools/dashboard/panels/system.py
M  CHANGELOG.md
A  docs/archive/SESSION_REPORT_2026-04-26_PipelineHardening.md
```
