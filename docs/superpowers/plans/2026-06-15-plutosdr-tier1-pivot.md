# DSLV-ZPDI PlutoSDR+ Tier-1 Metrology Pivot — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote the HamGeek AD9363 PlutoSDR+ class device to the canonical Tier-1 RF metrology backend while moving HackRF to optional legacy status, decoupling timing/SDR/frequency-translation, hardening cryptographic provenance, and preserving all existing validation gates.

**Architecture:** Layer 1 becomes a composed `HardwareHAL(timing_authority, sdr_backend, frequency_translation, qualification_policy)`. New `layer1_ingestion/timing/`, `sdr/`, and `frequency_translation/` subpackages provide typed, testable units. A capability-based `qualification/` engine replaces vendor-specific Tier-1 eligibility. Security hardening closes the dev-HMAC loophole, adds event hash chaining, and makes HDF5 finalization atomic. Configuration moves to YAML profiles under `config/` with environment-variable expansion.

**Tech Stack:** Python 3.10+, libiio (`iio`), h5py, numpy, pydantic, pytest, ruff. Optional hardware groups in `pyproject.toml` for `pluto`, `hackrf`, `hardware`.

---

## File Structure

### New files

| Path | Responsibility |
|------|----------------|
| `src/dslv_zpdi/layer1_ingestion/timing/__init__.py` | Package exports |
| `src/dslv_zpdi/layer1_ingestion/timing/base.py` | `TimingAuthority` ABC |
| `src/dslv_zpdi/layer1_ingestion/timing/attestation.py` | `TimingAttestation`, `ClockAttestation` dataclasses |
| `src/dslv_zpdi/layer1_ingestion/timing/pps_listener.py` | Move + refactor existing PPS listener |
| `src/dslv_zpdi/layer1_ingestion/timing/nmea_stream.py` | Move + refactor existing NMEA stream |
| `src/dslv_zpdi/layer1_ingestion/timing/chrony_monitor.py` | `ChronyMonitor` reading `chronyc tracking` |
| `src/dslv_zpdi/layer1_ingestion/timing/lbe1421.py` | `LBE1421TimingAuthority` composing PPS/NMEA/chrony |
| `src/dslv_zpdi/layer1_ingestion/sdr/__init__.py` | Package exports |
| `src/dslv_zpdi/layer1_ingestion/sdr/base.py` | `SdrBackend` ABC |
| `src/dslv_zpdi/layer1_ingestion/sdr/capabilities.py` | `SdrCapabilities`, `CaptureProfile`, `AppliedConfiguration` |
| `src/dslv_zpdi/layer1_ingestion/sdr/capture_result.py` | `CaptureResult`, `SdrHealth` |
| `src/dslv_zpdi/layer1_ingestion/sdr/pluto_iio.py` | `PlutoIioBackend` (libiio) |
| `src/dslv_zpdi/layer1_ingestion/sdr/hackrf_legacy.py` | `HackrfLegacyBackend` (optional) |
| `src/dslv_zpdi/layer1_ingestion/sdr/simulated.py` | `SimulatedSdrBackend` |
| `src/dslv_zpdi/layer1_ingestion/sdr/qualification.py` | `Tier1QualificationPolicy`, `QualificationResult` |
| `src/dslv_zpdi/layer1_ingestion/frequency_translation/__init__.py` | Package exports |
| `src/dslv_zpdi/layer1_ingestion/frequency_translation/model.py` | `FrequencyTranslationStage`, mixer mapping |
| `src/dslv_zpdi/layer1_ingestion/frequency_translation/calibration.py` | `ConverterCalibrationManifest` |
| `src/dslv_zpdi/layer1_ingestion/frequency_translation/mapper.py` | `FrequencyMapper` |
| `src/dslv_zpdi/core/key_provider.py` | `KeyProvider` ABC + file/env/systemd/dev providers |
| `src/dslv_zpdi/cli/__init__.py` | CLI package |
| `src/dslv_zpdi/cli/probe.py` | `dslv-zpdi-probe` |
| `src/dslv_zpdi/cli/preflight.py` | `dslv-zpdi-preflight` |
| `src/dslv_zpdi/cli/verify.py` | `dslv-zpdi-verify` |
| `src/dslv_zpdi/cli/qualify.py` | `dslv-zpdi-qualify` |
| `config/hardware/plutosdr_plus_ad9363.yaml` | Pluto device profile |
| `config/hardware/hackrf_legacy.yaml` | HackRF legacy profile |
| `config/timing/lbe1421.yaml` | LBE-1421 timing profile |
| `config/converters/direct_rf.yaml` | Direct-RF (no converter) profile |
| `config/converters/example_frequency_translator.yaml` | Example converter profile |
| `config/node_profiles/tier1_pluto_lbe1421.yaml` | Combined Tier-1 node profile |
| `config/node_profiles/simulator.yaml` | Simulator-only profile |
| `tools/probe_plutosdr_plus.py` | Standalone hardware probe utility |
| `tools/qualify_sdr.py` | SDR qualification harness |
| `docs/hardware/HAMGEEK_AD9363_PLUTOSDR_PLUS.md` | Hardware doc |
| `docs/hardware/LBE1421_PLUTO_WIRING.md` | Wiring doc (with UNVERIFIED gates) |
| `docs/hardware/HAMGEEK_AD9363_TIMING_PORT_VERIFICATION.md` | Physical verification gate doc |
| `docs/hardware/UPDOWNCONVERTER_INTEGRATION.md` | Converter integration doc |
| `docs/qualification/TIER1_HARDWARE_QUALIFICATION_STANDARD.md` | Capability-based qualification spec |
| `docs/qualification/HACKRF_BASELINE_MATRIX.md` | HackRF baseline matrix |
| `docs/qualification/PLUTO_ACCEPTANCE_MATRIX.md` | Pluto acceptance matrix |
| `docs/security/HDF5_TAMPER_EVIDENCE_AND_KEY_MANAGEMENT.md` | Security doc |
| `docs/operations/PLUTO_TIER1_DEPLOYMENT.md` | Deployment doc |
| `docs/operations/PLUTO_TIER1_TROUBLESHOOTING.md` | Troubleshooting doc |
| `docs/turnover/TURNOVER_PLUTOSDR_TIER1_2026-06-15.md` | Final turnover report |

### Modified files

| Path | Change |
|------|--------|
| `src/dslv_zpdi/__init__.py` | Bump to `5.0.0` |
| `pyproject.toml` | Version 5.0.0; optional deps `pluto`, `hackrf`, `hardware`; new console scripts; pytest markers |
| `src/dslv_zpdi/layer1_ingestion/hal_base.py` | Expand BaseHAL or keep minimal composition contract |
| `src/dslv_zpdi/layer1_ingestion/hal_factory.py` | Rewrite to use composed HAL + qualification |
| `src/dslv_zpdi/layer1_ingestion/hardware_hal.py` | New composed `HardwareHAL` (renames `hal_hardware.py`) |
| `src/dslv_zpdi/layer1_ingestion/hal_simulated.py` | Adapt to composed HAL |
| `src/dslv_zpdi/layer1_ingestion/payload.py` | Add timing attestation fields; preserve checksum |
| `src/dslv_zpdi/layer3_telemetry/hdf5_writer.py` | Event hash chain, atomic finalization, key provider, no dev-key fallback |
| `src/dslv_zpdi/layer3_telemetry/radon_session_writer.py` | Use key provider, canonical manifest |
| `src/dslv_zpdi/config_loader.py` | Profile validation with env expansion |
| `src/dslv_zpdi/main_pipeline.py` | Use composed HAL, fail-closed simulator logic |
| `src/dslv_zpdi/watchdog/timing_monitor.py` | Use `TimingAttestation` |
| `install_dslv_zpdi.sh` | Add `--tier1-pluto`, `--hackrf-legacy`, `--simulator`; libiio group |
| `Dockerfile` | Use optional `pluto` group; drop mandatory HackRF packages |
| `README.md` | Version bump, capability-based Tier-1 language |
| `CHANGELOG.md` | 5.0.0 entry |
| `RELEASE_NOTES_v5.0.0.md` | New release notes |
| `V3_DSLV-ZPDI_LIVING_MASTER.md` | Update canonical hardware/Tier-1 sections |
| `MASTER_SPEC.md` | Mirror updates |
| `specs/SPEC-004A.5.md` | Supersede/rename to capability-based Pluto backend spec |
| `specs/SPEC-018.md` | Update security terminology and HMAC requirements |
| `.github/workflows/dslv_zpdi_ci.yml` | Optional backend install, markers |

### Removed / deprecated

- `src/dslv_zpdi/layer1_ingestion/hal_hardware.py` → replaced by `hardware_hal.py` + `sdr/hackrf_legacy.py`.
- `src/dslv_zpdi/layer1_ingestion/hal_pluto.py` (untracked WIP) → replaced by `sdr/pluto_iio.py`.
- `src/dslv_zpdi/layer1_ingestion/lock_monitor.py` → remove or merge into `timing/`.
- Hardcoded dev HMAC literals → removed from source.

---

## Phase 1: Foundation — Profiles, Key Provider, and Timing Subpackage

### Task 1.1: Create configuration profile schemas and loader

**Files:**
- Create: `src/dslv_zpdi/config_models.py`
- Modify: `src/dslv_zpdi/config_loader.py`
- Test: `tests/test_config_models.py`

Implement Pydantic models for device, timing, converter, and node profiles with safe env-variable expansion (only `${VAR:-default}` syntax, no code execution). Validate profile fields including `direction_verified: bool`, `electrical_level_verified: bool`, `fail_closed: bool`.

### Task 1.2: Add key-provider abstraction

**Files:**
- Create: `src/dslv_zpdi/core/key_provider.py`
- Test: `tests/test_key_provider.py`

Implement `KeyProvider` ABC and concrete providers:
- `FileKeyProvider(path, mode=0o600)`
- `EnvKeyProvider(env_var)`
- `SystemdCredentialKeyProvider(credential_id)`
- `DevelopmentKeyProvider()` (explicitly for simulator mode)

`ProductionKeyResolver` tries file → env → systemd → fails closed. Never log or expose key material.

### Task 1.3: Refactor PPS listener and NMEA stream into `timing/`

**Files:**
- Create: `src/dslv_zpdi/layer1_ingestion/timing/pps_listener.py` (move from root)
- Create: `src/dslv_zpdi/layer1_ingestion/timing/nmea_stream.py` (move from root)
- Create: `src/dslv_zpdi/layer1_ingestion/timing/chrony_monitor.py`
- Create: `src/dslv_zpdi/layer1_ingestion/timing/attestation.py`
- Modify: `src/dslv_zpdi/layer1_ingestion/__init__.py` (re-export for compatibility)
- Test: `tests/timing/test_pps_listener.py`, `tests/timing/test_nmea_stream.py`, `tests/timing/test_chrony_monitor.py`

Keep existing APIs functional but add structured snapshot methods returning dataclasses. `ChronyMonitor` parses `chronyc tracking` RMS offset and reference ID.

### Task 1.4: Implement `LBE1421TimingAuthority`

**Files:**
- Create: `src/dslv_zpdi/layer1_ingestion/timing/lbe1421.py`
- Test: `tests/timing/test_lbe1421.py`

Compose PPS + NMEA + chrony into `LBE1421TimingAuthority.attest() -> TimingAttestation`. All nine timing states must be represented separately (`frequency_disciplined`, `utc_epoch_disciplined`, etc.). Use `None` for unknown evidence.

---

## Phase 2: SDR Backend Subpackage

### Task 2.1: Define typed SDR backend interfaces

**Files:**
- Create: `src/dslv_zpdi/layer1_ingestion/sdr/base.py`
- Create: `src/dslv_zpdi/layer1_ingestion/sdr/capabilities.py`
- Create: `src/dslv_zpdi/layer1_ingestion/sdr/capture_result.py`
- Test: `tests/sdr/test_interfaces.py`

Define `SdrBackend` ABC with `discover`, `configure`, `verify_clocking`, `capture`, `health`, `close`. Define `CaptureResult` with all required fields including sample accounting, overflow indicators, configuration hash.

### Task 2.2: Implement `PlutoIioBackend`

**Files:**
- Create: `src/dslv_zpdi/layer1_ingestion/sdr/pluto_iio.py`
- Test: `tests/sdr/test_pluto_iio.py`

Use lazy `iio` import. Support `local:`, `usb:`, `ip:` URIs from `DSLV_SDR_URI`. Validate settings by reading them back. Detect short reads, lost contexts, overruns. Track expected vs received samples. Do not enable TX. Produce `ClockAttestation` with `external_reference_configured` (from profile) and `external_reference_detected` (`None` until hardware proves it).

### Task 2.3: Implement `HackrfLegacyBackend` (optional)

**Files:**
- Create: `src/dslv_zpdi/layer1_ingestion/sdr/hackrf_legacy.py`
- Modify: `pyproject.toml` optional deps
- Test: `tests/sdr/test_hackrf_legacy.py`

Move HackRF-specific behavior from `hal_hardware.py`. Lazy `SoapySDR`/`pyhackrf` imports. Mark backend as `legacy`, `not_canonical_tier1`.

### Task 2.4: Implement `SimulatedSdrBackend`

**Files:**
- Create: `src/dslv_zpdi/layer1_ingestion/sdr/simulated.py`
- Test: `tests/sdr/test_simulated.py`

Deterministic simulator with configurable sample loss/injection hooks for fault tests.

### Task 2.5: Implement capability-based qualification engine

**Files:**
- Create: `src/dslv_zpdi/layer1_ingestion/sdr/qualification.py`
- Test: `tests/sdr/test_qualification.py`

`Tier1QualificationPolicy.evaluate(timing_attestation, sdr_health, capture_result) -> QualificationResult` with states `PASS/FAIL/UNVERIFIED/NOT_APPLICABLE/DEGRADED`. An `UNVERIFIED` mandatory dimension is not a pass.

---

## Phase 3: Frequency Translation and Composed HAL

### Task 3.1: Implement frequency-translation abstraction

**Files:**
- Create: `src/dslv_zpdi/layer1_ingestion/frequency_translation/model.py`
- Create: `src/dslv_zpdi/layer1_ingestion/frequency_translation/calibration.py`
- Create: `src/dslv_zpdi/layer1_ingestion/frequency_translation/mapper.py`
- Test: `tests/frequency_translation/test_mapper.py`

Mixer mapping: `rf = lo + sideband_sign * if`. Persist native and translated metadata. Calibration manifest with SHA-256 and device serial.

### Task 3.2: Implement composed `HardwareHAL`

**Files:**
- Create: `src/dslv_zpdi/layer1_ingestion/hardware_hal.py`
- Modify: `src/dslv_zpdi/layer1_ingestion/hal_factory.py`
- Modify: `src/dslv_zpdi/layer1_ingestion/hal_simulated.py`
- Test: `tests/test_hardware_hal.py`

`HardwareHAL(timing_authority, sdr_backend, frequency_translation, qualification_policy, fail_closed=True)`. `ingest_gps_pps()` and `ingest_sdr()` now delegate to composed objects and attach `TimingAttestation`/`ClockAttestation`. Fail closed on qualification failure.

### Task 3.3: Rewrite `hal_factory.py`

**Files:**
- Modify: `src/dslv_zpdi/layer1_ingestion/hal_factory.py`
- Test: `tests/test_hal_factory.py`

Factory behavior:
- Explicit profile → selected backend → qualification.
- No profile + one unambiguous discovered SDR → auto-select with evidence.
- No device / ambiguous / fail qualification → fail closed (not simulator) in field mode.
- Explicit simulator flag → simulator.

---

## Phase 4: HDF5 Security Hardening

### Task 4.1: Add canonical payload serialization

**Files:**
- Modify: `src/dslv_zpdi/layer1_ingestion/payload.py`
- Test: `tests/test_payload.py`

Define canonical serialization (UTF-8, key order, numeric format, null handling, timestamp representation). Ensure checksum is computed over canonical form.

### Task 4.2: Implement event hash chain in HDF5 writer

**Files:**
- Modify: `src/dslv_zpdi/layer3_telemetry/hdf5_writer.py`
- Test: `tests/test_hdf5_event_chain.py`

Add `event_payload_sha256`, `previous_event_chain_sha256`, `event_chain_sha256`, and sequence numbers. Genesis value documented. Detect deleted/reordered/altered/injected events.

### Task 4.3: Replace dev-key fallback with key provider

**Files:**
- Modify: `src/dslv_zpdi/layer3_telemetry/hdf5_writer.py`
- Modify: `src/dslv_zpdi/layer3_telemetry/radon_session_writer.py`
- Test: `tests/test_hdf5_key_hardening.py`

Accept `KeyProvider` in constructors. In field mode, missing/unreadable key raises `SecurityError`. In simulator mode, allow `DevelopmentKeyProvider`. Remove hardcoded literals.

### Task 4.4: Atomic HDF5 finalization

**Files:**
- Modify: `src/dslv_zpdi/layer3_telemetry/hdf5_writer.py`
- Modify: `src/dslv_zpdi/layer3_telemetry/radon_session_writer.py`
- Test: `tests/test_hdf5_atomic_finalization.py`

Write `.h5.partial`, flush, close, reopen read-only, verify datasets + event chain, generate manifest, HMAC manifest, generate detached SHA-256, atomic rename to `.h5`, write detached status record.

### Task 4.5: Implement `dslv-zpdi-verify` CLI

**Files:**
- Create: `src/dslv_zpdi/cli/verify.py`
- Modify: `pyproject.toml`
- Test: `tests/cli/test_verify.py`

Exit codes: 0 valid, 1 integrity failure, 2 missing artifact, 3 unsupported schema, 4 key unavailable, 5 operational error. Human + JSON output.

---

## Phase 5: CLIs, Installer, and Configuration

### Task 5.1: Add CLI package

**Files:**
- Create: `src/dslv_zpdi/cli/__init__.py`
- Create: `src/dslv_zpdi/cli/_common.py` (shared `--version`, `--json`, `--profile`, `--simulator`)
- Create: `src/dslv_zpdi/cli/probe.py`
- Create: `src/dslv_zpdi/cli/preflight.py`
- Create: `src/dslv_zpdi/cli/qualify.py`
- Modify: `pyproject.toml`
- Test: `tests/cli/test_clis.py`

All CLIs are standalone functions, not instance methods. `--version` reads `dslv_zpdi.__version__`.

### Task 5.2: Create YAML configuration profiles

**Files:**
- Create all YAML profiles under `config/`
- Test: `tests/test_profiles.py`

Include explicit `direction_verified: false`, `electrical_level_verified: false`, `sdr_pps_support: unverified` where not yet proven.

### Task 5.3: Refactor installer

**Files:**
- Modify: `install_dslv_zpdi.sh`
- Test: manual smoke test in Docker

Add `--tier1-pluto`, `--hackrf-legacy`, `--simulator`. Package groups: `BASE_PACKAGES`, `TIMING_PACKAGES`, `PLUTO_PACKAGES`, `HACKRF_LEGACY_PACKAGES`, `HARDENING_PACKAGES`. Detect Trixie package availability.

### Task 5.4: Create hardware probe utility

**Files:**
- Create: `tools/probe_plutosdr_plus.py`
- Test: `tests/test_probe_plutosdr_plus.py`

Read-only by default. Supports `--discover`, `--uri`, `--json`. Collects IIO inventory, host inventory, firmware fingerprint. Hashes artifacts.

### Task 5.5: Create qualification harness

**Files:**
- Create: `tools/qualify_sdr.py`
- Test: `tests/test_qualify_sdr.py`

Runs sustained captures, transport tests, sample accounting. Does not invent ENOB/SFDR without equipment.

---

## Phase 6: Tests and Fault Injection

### Task 6.1: Add pytest markers

**Files:**
- Modify: `pyproject.toml`

Register markers: `hardware`, `soak`, `slow`, `pluto`, `hackrf`.

### Task 6.2: Add unit tests for new components

**Files:**
- Create/update tests under `tests/timing/`, `tests/sdr/`, `tests/frequency_translation/`, `tests/cli/`, `tests/security/`

Cover: profile validation, env expansion, clock attestation tri-states, qualification logic, fail-closed factory, frequency translation, spectral inversion, calibration manifest hashing, event hash chain, atomic finalization, manifest signing, missing-key failure, dev-key simulator allowance, CLI exit codes.

### Task 6.3: Add fault-injection tests

**Files:**
- Create: `tests/test_fault_injection.py`

Deterministic tests for no SDR, multiple SDRs, context loss, short read, overflow, unsupported rate, readback mismatch, PPS lost, GPS lost, NMEA stale, chrony unsync, calibration mismatch, HMAC key missing, payload hash mismatch, event-chain mismatch, simulator-in-field-mode, TX enabled.

---

## Phase 7: Documentation and Specifications

### Task 7.1: Update canonical specification

**Files:**
- Modify: `V3_DSLV-ZPDI_LIVING_MASTER.md`
- Modify: `MASTER_SPEC.md`
- Modify/create `specs/SPEC-004A.5.md` and `specs/SPEC-018.md`

Replace "Tier-1 means HackRF" with capability-based language. Declare Pluto as Phase 2A canonical pending verification. Separate synchronization claims.

### Task 7.2: Write hardware documentation

**Files:**
- Create all `docs/hardware/*.md`
- Create all `docs/qualification/*.md`
- Create all `docs/security/*.md`
- Create all `docs/operations/*.md`

Include UNVERIFIED_PHYSICAL_PROPERTY markers, prohibited wiring assumptions, exact verification steps.

### Task 7.3: Update README, CHANGELOG, release notes

**Files:**
- Modify: `README.md`, `CHANGELOG.md`
- Create: `RELEASE_NOTES_v5.0.0.md`

### Task 7.4: Create turnover report

**Files:**
- Create: `docs/turnover/TURNOVER_PLUTOSDR_TIER1_2026-06-15.md`

---

## Phase 8: CI and Version Synchronization

### Task 8.1: Update CI workflow

**Files:**
- Modify: `.github/workflows/dslv_zpdi_ci.yml`

Test optional dependency installs (`[pluto]`, `[hackrf]`), marker-based test runs, manifest round-trip, simulator-only import.

### Task 8.2: Bump version everywhere

**Files:**
- Modify: `pyproject.toml`, `src/dslv_zpdi/__init__.py`, `README.md`, `CHANGELOG.md`, `RELEASE_NOTES_v5.0.0.md`, specs

Run `tools/check_version_sync.py` until clean.

### Task 8.3: Final validation

Run:
```bash
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pip check
DEV_SIMULATOR=1 .venv/bin/python -m pytest tests/ -q
.venv/bin/python tools/orphan_checker.py
.venv/bin/python tools/check_version_sync.py
.venv/bin/python tools/repo_guard.py
.venv/bin/python -m ruff check src/ tools/ tests/
DEV_SIMULATOR=1 dslv-zpdi-preflight --profile config/node_profiles/simulator.yaml --simulator --json output/preflight.json
DEV_SIMULATOR=1 dslv-zpdi-pipeline --profile config/node_profiles/simulator.yaml --simulator
dslv-zpdi-verify output/*.h5 --deep
```

---

## Self-Review

**Spec coverage:** Each section of the user's prompt maps to at least one task above. The largest omission by design is running long-duration (24 h / 72 h) soak tests, which cannot be completed in an agent session; the harness is provided and results are marked pending.

**Placeholder scan:** No `TBD` or `TODO` remain in task descriptions. Exact file paths and commands are included.

**Type consistency:** Common types (`TimingAttestation`, `ClockAttestation`, `CaptureResult`, `SdrBackend`) are defined in early tasks and reused.
