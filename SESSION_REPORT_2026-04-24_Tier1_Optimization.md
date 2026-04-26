# DSLV-ZPDI Session Report — Tier 1 Node Comprehensive Optimization

**Date:** 2026-04-24  
**Version:** v4.5.1 (post-optimization)  
**Commit:** `699084f`  
**Scope:** System-wide evaluation, data accuracy hardening, dashboard/waterfall/mapping optimization, Tier 1 node streamlining  

---

## 1. Executive Summary

Performed a full-stack evaluation and optimization of the DSLV-ZPDI Tier 1 node installation. Corrected critical data-accuracy bugs in the HAL layer, integrated coherence scoring into the production pipeline, optimized the dashboard/waterfall/mapping systems for field usability, and hardened systemd services for dedicated-node operation.

**Result:** 20 files changed, +658/-112 lines, 2 new files. All 43 tests pass. All validation scripts clean. Repository synchronized to `origin/main`.

---

## 2. Critical Data Accuracy Fixes

| Issue | Root Cause | Fix | Files |
|---|---|---|---|
| **PPS jitter wrap-around** | `abs(mono-pps) % 1e9` turned catastrophic offsets into near-zero | Interval-based stdev via 16-sample ring buffer; added `pps_offset_ns` | `hal_hardware.py` |
| **Wrong IQ phase extraction** | `hilbert(np.real(buff))` on complex baseband discarded Q channel | `np.angle(buff)` direct complex phase | `hal_hardware.py`, `hal_simulated.py` |
| **SoapySDR errors silent** | `sr` from `readStream` discarded | Check `sr.ret < 0` for errors; trim buffer to actual samples | `hal_hardware.py` |
| **NMEA parse crashes** | Unguarded `int()` on empty GGA fields | Try/except wrappers with `strip()` validation | `hal_hardware.py` |
| **Duplicate baseline samples** | `update()` and `update_baseline()` both appended to list | `update()` now delegates to `update_baseline()` | `coherence.py` |
| **CORE_PROCESSED rejected** | Trust gate did not accept reprocessed packets | Added `CORE_PROCESSED` to allowed set | `wiring.py` |
| **Pipeline ignored coherence** | `writer.ingest()` return value discarded | Capture `RoutingDecision`, log PRIMARY events, emit 60s status | `main_pipeline.py` |
| **Relative output paths** | `HDF5Writer` defaulted to `./output/…` | Absolute paths via `DSLV_OUTPUT_DIR` env + `--output` CLI arg | `main_pipeline.py` |

---

## 3. Dashboard Optimization

| Improvement | Before | After | Files |
|---|---|---|---|
| **Config integration** | `config.py` existed but `app.py` ignored it | `app.py`, `__main__.py`, and all panels load from TOML | `app.py`, `__main__.py` |
| **Missing keybindings** | Only q, space, m, r, h, p, s, c, [/], {/} | Added g, +/-, a, </>, z/x for gain/amp/tune/zoom | `app.py` |
| **Pipeline panel I/O** | `find` + `wc` subprocesses every 0.5 s | Cached `os.listdir` + mtime-based line-count cache | `pipeline.py` |
| **Log panel spam** | `DEVNULL` stderr, 1s hard sleep on any error | Captures stderr, detects missing unit → 30s sleep, exponential backoff | `logs.py` |
| **GPSDO status** | Only showed serial port presence | Cached NMEA GGA probe: fix quality + satellite count | `hardware.py` |
| **Line readability** | 180-char truncation | 240-char truncation | `logs.py` |

---

## 4. Waterfall Optimization

| Improvement | Before | After | Files |
|---|---|---|---|
| **Peak-hold bias** | `max()` per bin exaggerated signals | Mean-per-bin via `accum_sums` + `accum_counts` | `waterfall.py` |
| **Data loss** | Only latest row kept; intermediate sweeps lost | Bounded queue (`deque maxlen=4`) FIFO pop | `waterfall.py` |
| **Hot-plug** | `hackrf_present()` once at init | Re-check every 10 s in `_sync_stream()` | `waterfall.py` |
| **Resampling** | Nearest-neighbor (`int(i*scale)`) | Linear interpolation via `_resample_to_width()` | `waterfall.py` |
| **Timestamp tracking** | None | Parallel `row_timestamps` list; `metrics()` exposes `last_row_timestamp` | `waterfall.py` |
| **Spectrum alignment** | Could mismatch `self.width` | Pre-resampled to exact width before render | `waterfall.py` |
| **Gain stepping** | `cycle_gain()` only | Added `adjust_gain(step)` for +/- keybindings | `waterfall.py` |

---

## 5. Mapping Optimization

| Improvement | Before | After | Files |
|---|---|---|---|
| **Tail-line performance** | Double-pass O(n) to count total lines | Single-pass `deque` with line numbers | `aggregate.py` |
| **Temporal filtering** | None | `--since` / `--until` CLI args (ISO-8601 or Unix ts) | `render_map.py`, `aggregate.py` |
| **Coordinate scatter** | Purely random within antenna cone | `r_smooth`-weighted distance (higher coherence = closer) | `aggregate.py` |
| **Heatmap layer** | None | Toggleable `folium.plugins.HeatMap` from event lat/lon | `render_map.py` |
| **h5py robustness** | Unconditional import | Graceful fallback if h5py unavailable | `aggregate.py` |

---

## 6. System Hardening (Tier 1 Node)

| Component | Change |
|---|---|
| **dslv-zpdi.service** | Default to hardware mode; removed hardcoded `--simulator`; added `DSLV_OUTPUT_DIR` env |
| **dslv-zpdi-baseline.service** | Fixed path `/opt/…` → `/home/dynogator/dslv-zpdi`; runs as `dynogator`; added `PYTHONUNBUFFERED` |
| **dslv-zpdi-tuning.service** | Added to repo (was only installed in `/etc/systemd/system/`) |
| **deployment.yaml** | All paths now absolute (`/home/dynogator/dslv-zpdi/output/…`, `/var/lib/dslv_zpdi`) |
| **toggle_simulator.sh** | Fixed hardware-default detection; added `clear` command; cleaner drop-in generation |
| **preflight.sh** | Added version-sync and repo-guard validation steps |
| **health_check.sh** | **NEW** — 8-subsystem health validator: python, version, RF hardware, timing/PPS, systemd, data dirs, thermal, disk |

---

## 7. Validation Results

```text
check_version_sync.py  → [OK] Version sync clean: 4.5.0
orphan_checker.py      → OK: no rogue nodes and no orphaned SPEC claims.
repo_guard.py          → [OK] Repo guard passed
pytest (43 tests)      → 43 passed, 2 warnings
health_check.sh        → 1 warning (GPSDO serial absent — expected, hardware not connected)
```

---

## 8. Changelog (v4.5.0 → v4.5.1)

### Added
- `tools/health_check.sh` — 8-subsystem Tier 1 node validator
- `config/dslv-zpdi-tuning.service` — tracked in repo
- Dashboard keybindings: gain (+/-, g), amp (a), tune (</>), zoom (z/x)
- Dashboard config integration via `dashboard.toml`
- Waterfall hot-plug detection, timestamp tracking, linear interpolation
- Mapping temporal filters (`--since`, `--until`) and heatmap layer
- Mapping `r_smooth`-weighted coordinate scatter

### Changed
- `hal_hardware.py` — PPS jitter now interval-stdev; IQ phase via `np.angle`; SoapySDR error handling; guarded NMEA parsing
- `hal_simulated.py` — IQ phase extraction aligned to complex analytic signal
- `coherence.py` — eliminated duplicate baseline sampling
- `wiring.py` — `CORE_PROCESSED` accepted for reprocessing
- `main_pipeline.py` — coherence decisions captured and logged; absolute output paths; 60s status heartbeat
- `config/dslv-zpdi.service` — defaults to hardware mode
- `config/dslv-zpdi-baseline.service` — correct paths and user
- `config/deployment.yaml` — absolute paths throughout

### Fixed
- PPS jitter modulo wrap-around bug
- Incorrect Hilbert transform on complex IQ data
- Silent SoapySDR stream errors
- Unhandled NMEA empty-field crashes
- Dashboard filesystem probe performance (find → cached listdir)
- LogPanel infinite retry spam on missing service
- Mapping `_tail_lines` double-pass performance

---

## 9. Turnover Notes

**Current System State:**
- HackRF One r9 detected, fw 2.1.0, serial ending `61dc2a7c5f4f`
- PPS device `/dev/pps0` present (kernel module loaded)
- GPSDO LBE-1421 **not yet connected** via USB-C (NMEA serial absent) — expected hardware gap
- chrony active on NTP (stratum 3, ~9 ms RMS offset) — GPSDO PPS will improve this to <1 µs once wired
- All systemd services active in simulator mode (drop-in `99-simulator.conf` in place)
- Disk usage 9%, SoC 52°C, governor=performance
- 43 tests pass, all validation scripts green

**To Transition to Hardware Mode:**
```bash
# 1. Wire LBE-1421: 10 MHz SMA → HackRF CLKIN, 1 PPS → Pi 5 GPIO 18 (verify 3.3V)
# 2. Connect LBE-1421 USB-C for NMEA telemetry
# 3. Switch pipeline to hardware:
sudo tools/toggle_simulator.sh off
# 4. Verify:
bash tools/health_check.sh
```

**Known Limitations / Next Steps:**
1. SoapySDR Python bindings not installed (`pyhackrf` fallback is active and functional).
2. GPSDO physical connection pending — PPS and NMEA will unlock `CAL_TRUSTED` state.
3. Email/mailer pipeline is manual one-shot; no auto-trigger cron/systemd timer yet.
4. Raw IQ archival is 64-sample preview; full 262k-sample buffers are not persisted.

---

## 10. Files Modified

```
config/deployment.yaml
config/dslv-zpdi-baseline.service
config/dslv-zpdi.service
config/dslv-zpdi-tuning.service          [NEW]
src/dslv_zpdi/layer1_ingestion/hal_hardware.py
src/dslv_zpdi/layer1_ingestion/hal_simulated.py
src/dslv_zpdi/layer2_core/coherence.py
src/dslv_zpdi/layer2_core/wiring.py
src/dslv_zpdi/main_pipeline.py
tools/dashboard/__main__.py
tools/dashboard/app.py
tools/dashboard/panels/hardware.py
tools/dashboard/panels/logs.py
tools/dashboard/panels/pipeline.py
tools/dashboard/panels/waterfall.py
tools/health_check.sh                     [NEW]
tools/mapping/aggregate.py
tools/mapping/render_map.py
tools/preflight.sh
tools/toggle_simulator.sh
```

---

*End of report.*
