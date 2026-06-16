# DSLV-ZPDI PlutoSDR+ Tier-1 Pivot — Baseline Audit

**Date:** 2026-06-15  
**Branch:** `feat/tier1-plutosdr-plus-metrology`  
**Base commit:** `1329e76e4ee4faf02cc7fea43bb68443974759e4`  
**Project version:** 4.8.1  
**Auditor:** Autonomous implementation agent

## Executive Summary

The repository is at **Rev 4.8.1** and currently treats the **HackRF One** as the canonical Tier-1 RF source, with a recent work-in-progress (`hal_pluto.py`, `SPEC-004A.5.md`, dashboard updates) adding first-class PlutoSDR/PlutoSDR+ support. All 118 collected simulator tests pass, version sync is clean, and the orphan checker/repo guard pass. However, the architecture still couples timing, SDR backend, and frequency-translation logic inside monolithic HAL classes, contains a hardcoded development HMAC key, silently falls back to simulation in some paths, and overstates timing claims with a single `phase_lock_verified` Boolean. This audit catalogs the baseline so the pivot can be measured against it.

## Baseline Validation Results

| Validator | Command | Result |
|-----------|---------|--------|
| Editable install | `.venv/bin/python -m pip install -e '.[dev]'` | ✅ dslv-zpdi 4.8.1 built |
| `pip check` | `.venv/bin/python -m pip check` | ⚠️ FAILS due to system-wide `.pth` pollution (see note below) |
| pytest | `DEV_SIMULATOR=1 .venv/bin/python -m pytest tests/ -q` | ✅ 118 passed, 2 warnings |
| Orphan checker | `.venv/bin/python tools/orphan_checker.py` | ✅ OK |
| Version sync | `.venv/bin/python tools/check_version_sync.py` | ✅ 4.8.1 clean |
| Repo guard | `.venv/bin/python tools/repo_guard.py` | ✅ OK |
| ruff | `.venv/bin/python -m ruff check src/ tools/ tests/` | ❌ 4 errors in untracked `hal_pluto.py` |

**`pip check` note:** The project venv contains `.venv/lib/python3.13/site-packages/system-dist-packages.pth` which pulls in `/usr/lib/python3/dist-packages`. That system tree has unrelated package conflicts (forensic/plaso/openai/etc.). These are **not** caused by `dslv-zpdi` dependencies; they are an environment artifact.

## Repository Layout

```text
src/dslv_zpdi/
├── __init__.py                    # version = "4.8.1"
├── config_loader.py               # Pydantic pipeline config
├── main_pipeline.py               # CLI + producer/consumer loops
├── contracts/tier1_policy.py      # Trust policy constants
├── core/{exceptions.py,states.py} # Project exceptions
├── layer1_ingestion/
│   ├── hal_base.py                # BaseHAL: ingest_gps_pps, ingest_sdr
│   ├── hal_factory.py             # get_hal() — auto/hackrf/pluto/sim
│   ├── hal_hardware.py            # HackRF-centric HardwareHAL
│   ├── hal_pluto.py               # WIP native libiio PlutoHAL (untracked)
│   ├── hal_simulated.py           # SimulatedHAL
│   ├── cm5_ingestion.py           # Deprecated shim
│   ├── nmea_stream.py             # LBE-1421 NMEA parser
│   ├── payload.py                 # IngestionPayload + validation
│   ├── pps_listener.py            # /dev/pps0 kernel edge reader
│   ├── pixel_node_bridge.py       # Mobile-node BLE bridge
│   ├── radoneye_ingestor.py       # Radon sensor ingestion
│   └── uplink_manager.py          # Uplink telemetry
├── layer2_core/
│   ├── barometric_coherence.py
│   ├── coherence.py               # Baseline FSM
│   ├── swarm_integrity.py
│   └── wiring.py                  # Packet routing
├── layer3_telemetry/
│   ├── hdf5_writer.py             # Event HDF5 + HMAC attestation
│   ├── node_receiver.py           # Flask swarm receiver
│   ├── radon_session_writer.py    # Session manifest + branch checksums
│   └── router.py                  # PRIMARY/SECONDARY routing
├── orchestrator/radon_session.py  # 48-hour campaign
└── watchdog/
    ├── health_reporter.py
    ├── mvip6.py
    ├── pi_watchdog.py
    └── timing_monitor.py          # chronyc-based monitor (used by pipeline)
```

## Existing Hardware Backends

| Backend | File | Driver | Coupling |
|---------|------|--------|----------|
| `HardwareHAL` | `hal_hardware.py` | SoapySDR (`driver=hackrf`) + pyhackrf | **Tightly HackRF-coupled** despite generic name |
| `PlutoHAL` | `hal_pluto.py` (untracked WIP) | libiio `iio` + SoapySDR Pluto | Moderate; clones `HardwareHAL` timing logic |
| `SimulatedHAL` | `hal_simulated.py` | None | Deterministic GPSDO + HackRF simulator |

### HackRF coupling details

- `hal_hardware.py` hardcodes `driver="hackrf"` in SoapySDR path.
- pyhackrf fallback sets HackRF-specific LNA/VGA gains and amp lockout.
- `verify_gpsdo_lock()` calls `hackrf_debug --clock_source`.
- `provision_tier1.py` and dashboard `hardware.py` are HackRF/LBE-1421-centric.
- `pyhackrf>=0.2.0` is a **mandatory** dependency in `pyproject.toml`.
- Auto-detection order in `get_hal()` is HackRF → Pluto → simulator.

## Existing Timing Logic

| Component | What it actually measures | Overclaim |
|-----------|---------------------------|-----------|
| `PpsListener` | Kernel PPS inter-arrival interval RMS | Used as proxy for UTC synchronization |
| `NmeaStream` | GGA fix + satellite count + HDOP | Fix age not checked in ingestion path |
| `HardwareHAL.verify_tier1_phase_lock()` | PPS ≥2 samples AND jitter <1 ms AND GPS fix | Returns `phase_lock_verified=True`; cannot verify 10 MHz/ADC lock |
| `TimingMonitor` | `chronyc tracking` "System time" | 50 µs threshold, not RMS offset; starts `healthy=True` |
| `GPSDOLockMonitor` | NMEA + chronyc RMS + `hackrf_debug` | Not wired into production pipeline; HackRF-only |

**Problematic terminology:** `phase_lock_verified` collapses GPS fix, PPS regularity, and user-asserted external clock into a single Boolean. It does **not** separately report `frequency_disciplined`, `utc_epoch_disciplined`, `external_reference_detected`, `baseband_pll_locked`, `sample_epoch_synchronized`, etc.

## Existing HDF5 Integrity Behavior

- `IngestionPayload.to_json()` computes SHA-256 over a JSON representation (self-computable).
- `HDF5Writer` stores `content_sha256` and `hmac_sha256` per event group.
- `RadonSessionWriter` computes branch SHA-256 checksums and HMAC-SHA256 manifest.
- **Loophole:** Both writers fall back to hardcoded key `b"dev_key_replace_before_field_deploy"` with only a warning.
- No event hash chain exists.
- Atomic finalization (`.partial` → `.h5`) is not implemented.

## Existing Production Key Behavior

- No key-provider abstraction.
- Development key is embedded as a string literal in `hdf5_writer.py` and `radon_session_writer.py`.
- Field mode does **not** fail closed when production key is missing.

## Existing Simulator Fallback Behavior

- `get_hal(simulator=True)` or `DEV_SIMULATOR=1` → `SimulatedHAL`.
- `sdr_type="auto"` falls back to `SimulatedHAL` if hardware init fails.
- `main_pipeline.py` silently sets `args.simulator = True` when `get_hal()` returns a simulator unexpectedly.
- This violates the requirement that missing hardware must **not** trigger silent simulation in field mode.

## Existing CLI Entry Points

Declared in `pyproject.toml`:

| Script | Target | Status |
|--------|--------|--------|
| `dslv-zpdi-pipeline` | `dslv_zpdi.main_pipeline:main` | ✅ Working |
| `dslv-zpdi-dashboard` | `dashboard.__main__:main` | ❌ Broken — `dashboard` package is under `tools/dashboard/`, outside setuptools discovery |
| `dslv-zpdi-preflight` | `dslv_zpdi.layer1_ingestion.hal_hardware:HardwareHAL.verify_tier1_phase_lock` | ❌ Broken — console script points to an instance method |

## Existing Installer Dependencies

File: `install_dslv_zpdi.sh` (Rev 4.6.1-LBE1421-RESCUE)

- `TIER1_PACKAGES` includes `hackrf`, `libhackrf-dev`, `soapysdr-module-hackrf`, `python3-soapysdr`.
- No separate `--tier1-pluto` / `--hackrf-legacy` / `--simulator` install modes.
- No `libiio` package group.

## Existing Systemd Services

Reference units in `config/`:

- `dslv-zpdi.service`
- `dslv-zpdi-baseline.service`
- `dslv-zpdi-hackrf-init.service` (HackRF-specific)
- `dslv-zpdi-node-receiver.service`
- `dslv-zpdi-preflight.service`
- `dslv-zpdi-tuning.service`
- `dslv-zpdi-webdash.service`

Hardened variants in `config/os-hardening/`. Several still reference old paths (`/home/dynogator/Gem-home/dslv-zpdi/venv`).

## Dependency and Call Graph

```text
main_pipeline.py / capture_baseline.py
    └── get_hal(...) [hal_factory.py]
            ├── HardwareHAL [hal_hardware.py] ── SoapySDR/pyhackrf
            ├── PlutoHAL [hal_pluto.py] ── iio/SoapySDR
            └── SimulatedHAL [hal_simulated.py]

HAL.ingest_sdr() / ingest_gps_pps()
    └── IngestionPayload [payload.py]
            └── to_json() ── HDF5Writer.ingest() [hdf5_writer.py]
                    └── DualStreamRouter.route() [router.py]
                            └── wiring.py ── CoherenceScorer [coherence.py]

RadonSessionWriter adds: certified_crm, macro_atmosphere, space_weather,
                         mobile_node_tier2, validation_index, manifest
```

## Audit Categories

### Architecture-level vendor coupling

- `HardwareHAL` is effectively a HackRF HAL with a generic name.
- `BaseHAL` only defines two methods; thermal/acoustic hooks live in `HardwareHAL`.
- Timing authority (PPS/NMEA) is embedded inside `HardwareHAL` and `PlutoHAL` instead of being a separate composable object.

### Documentation-only references

- `PHASE_2A_TIER_1_BUILD_SHEET.md` still calls the HackRF One the Tier-1 SDR.
- `README.md` and release notes reference HackRF as canonical Tier-1.
- `CHANGELOG.md` and turnover documents describe the LBE-1421 + HackRF build.

### Tests tied to HackRF

- `tests/test_hardware_failure_paths.py` — mocks `pyhackrf` and SoapySDR HackRF paths.
- `tests/test_timing_monitor.py` — tests `GPSDOLockMonitor` (HackRF-only helper).
- No custom `@pytest.mark.hardware` or `@pytest.mark.soak` markers.

### Installer coupling

- `install_dslv_zpdi.sh` installs HackRF packages unconditionally in Tier-1 mode.
- `Dockerfile` installs `libhackrf-dev`, `soapysdr-module-hackrf`.

### Runtime coupling

- `hal_factory.py` imports `hal_hardware.py` eagerly, which eagerly imports `SoapySDR` and `hackrf`.
- `pyhackrf` monkey-patching happens at module load.

### HDF5 schema coupling

- Existing `event_*` groups must be preserved (additive changes only).
- `hdf5_writer.py` and `radon_session_writer.py` share no common manifest schema.

### User-interface coupling

- Dashboard `hardware.py` probes `hackrf_info` and `iio.Context` but is visually HackRF-first.
- Dashboard `waterfall.py` supports SIM/HACKRF/PLUTO sources.

### Dead or duplicated code

- `lock_monitor.py` — only used in tests.
- `HardwareHAL.ingest_thermal()` / `ingest_acoustic()` — placeholders, never called.
- `HardwareHAL.verify_nmea_telemetry()` — duplicates `NmeaStream.parse_gga()`.
- `cm5_ingestion.py` — deprecated shim.
- PPS/NMEA logic duplicated between `HardwareHAL` and `PlutoHAL`.

### Incorrect or overstated timing claims

| Location | Claim | Reality |
|----------|-------|---------|
| `hal_hardware.py` | `phase_lock_verified` | PPS + GPS fix only; no ADC clock verification |
| `hal_pluto.py` | Same | External clock is a user assertion |
| `timing_monitor.py` | 50 µs system-time threshold | Not RMS offset; starts healthy |
| `config/deployment.yaml` | `max_pps_jitter_ns: 1000` | Not consumed anywhere |

## Recommendations for the Pivot

1. Introduce a composed `HardwareHAL(timing_authority, sdr_backend, frequency_translation, qualification_policy)`.
2. Move HackRF-specific code to `sdr/hackrf_legacy.py` and make it optional.
3. Implement `sdr/pluto_iio.py` as the canonical Tier-1 backend using lazy `iio` imports.
4. Create `timing/` subpackage with `LBE1421TimingAuthority`, `PpsListener`, `NmeaStream`, `ChronyMonitor`, and structured `TimingAttestation`.
5. Add `frequency_translation/` subpackage for converter provenance.
6. Add capability-based `qualification/` engine with explicit `PASS/FAIL/UNVERIFIED/DEGRADED` states.
7. Remove hardcoded dev HMAC key; implement key-provider abstraction that fails closed in field mode.
8. Add event hash chain and atomic `.partial` → `.h5` finalization.
9. Fix broken CLI entry points and add `dslv-zpdi-probe`, `dslv-zpdi-preflight`, `dslv-zpdi-verify`, `dslv-zpdi-qualify`, `dslv-zpdi-soak-test`.
10. Restructure installer with `--tier1-pluto`, `--hackrf-legacy`, `--simulator` modes.
11. Update documentation to capability-based Tier-1 language and explicitly mark all unverified physical properties.
12. Target version **5.0.0** and synchronize all version authorities.

## Owner WIP to Preserve

The following untracked files exist in the working tree and were backed up before branch creation:

- `src/dslv_zpdi/layer1_ingestion/hal_pluto.py` — useful libiio/SoapySDR capture code; will be refactored into `sdr/pluto_iio.py`.
- `tests/test_pluto_hal.py` — useful mock patterns; will be expanded/relocated.
- `specs/SPEC-004A.5.md` — useful Pluto HAL spec; will be superseded by capability-based specs.
- `TURNOVER_2026-06-14_PlutoSDR_Dashboard.md` — dashboard turnover; retained for reference.

Backup location: `/home/dynogator/Desktop/DSLV-ZPDI_GitHub_Dev/dslv-zpdi_artifact_backups/20260615_030821/`
