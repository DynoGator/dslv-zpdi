# Turnover — PlutoSDR+ Integration + Dashboard Generalization

**Date:** 2026-06-14  
**Topic:** First-class PlutoSDR/ADALM-PLUTO support across HAL, config, pipeline, and dashboard.  
**Branch/State:** Working tree in `/home/dynogator/Desktop/DSLV-ZPDI_GitHub_Dev/dslv-zpdi`

## What changed

1. **HAL layer**
   * New `src/dslv_zpdi/layer1_ingestion/hal_pluto.py` — native `libiio` HAL.
   * `src/dslv_zpdi/layer1_ingestion/hal_factory.py` — `sdr_type` routing (`auto`/`hackrf`/`pluto`/`sim`) + auto-detection helpers.
2. **Config / pipeline**
   * `src/dslv_zpdi/config_loader.py` — Pluto fields + env overrides; `nodes.registered` list now normalized to a dict so the current YAML validates.
   * `src/dslv_zpdi/main_pipeline.py` — `--sdr-type` CLI arg.
   * `config/deployment.yaml` — Pluto section added (`sdr_type: auto`).
3. **Tests**
   * `tests/test_pluto_hal.py` — mock-based coverage.
4. **Dashboard**
   * `tools/dashboard/panels/waterfall.py` — `PlutoSweepStream`, source enum (`SIM`/`HACKRF`/`PLUTO`/`…-WAIT`), source cycling, config/env/CLI selection.
   * `tools/dashboard/panels/hardware.py` — shows both HackRF and PlutoSDR detection.
   * `tools/dashboard/panels/anomaly.py` — source styling for PLUTO.
   * `tools/dashboard/app.py` — `--sdr-source` CLI flag, `r` key cycles sources, footer shows source label.
   * `tools/dashboard/config.py` — `waterfall.sdr_source`, `pluto_uri`, `pluto_gain`.
   * `tools/dashboard/launch.sh` — uses `.venv`, updated comments.
5. **Docs / process**
   * `specs/SPEC-004A.5.md` — new specification.
   * `AGENTS.md` — documented system `.pth` workaround for `iio`/`SoapySDR` in venv.
   * `.venv/lib/python3.13/site-packages/system-dist-packages.pth` — points to `/usr/lib/python3/dist-packages`.

## Verification run

```bash
cd /home/dynogator/Desktop/DSLV-ZPDI_GitHub_Dev/dslv-zpdi
.venv/bin/python tools/check_version_sync.py
.venv/bin/python tools/orphan_checker.py
.venv/bin/python tools/repo_guard.py
DEV_SIMULATOR=1 .venv/bin/python -m pytest tests/ -q --ignore=tests/test_hardware_failure_paths.py
```

Result: 96 passed, 2 skipped, repo guard clean, version sync clean, no orphaned SPEC claims.

Real Pluto (when connected at `ip:192.168.2.1`) initializes and produces `RF_SDR` payloads. With `external_clock=false` they correctly validate to `SECONDARY_QUARANTINED` (`rf_clock_not_external`).

## Known open items

* **External-clock trust remains wiring-dependent.** Tier 1 primary output requires physically wiring GPSDO 10 MHz → Pluto `CLKIN` and 1 PPS, then setting `pluto_external_clock: true`.
* **Pre-existing test failure:** `tests/test_hardware_failure_paths.py::TestNMEAFailurePaths::test_serial_timeout` fails on this host because `/dev/ttyACM0` is locked by another process. Unrelated to Pluto work.
* **Dashboard launch script/service paths:** The repo uses `.venv`; production systemd units in `config/` still reference `/home/dynogator/Gem-home/dslv-zpdi/venv`. If those units are used on this host, update them to match the repo path or re-link.

## Next recommended steps

1. Field-test Pluto with GPSDO reference wired and `pluto_external_clock: true`; confirm primary-stream eligibility.
2. Add a hardware-in-the-loop test that exercises real `PlutoHAL.ingest_sdr()` with a short capture when a Pluto is reachable.
3. Decide whether to recreate the venv with `--system-site-packages` or keep the `.pth` workaround long-term.
4. Resolve `/dev/ttyACM0` lock and re-enable `test_hardware_failure_paths.py`.
