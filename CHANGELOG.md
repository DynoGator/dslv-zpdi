# Changelog

## [Unreleased] — Mobile node sync and installer hardening (2026-06-19)

### Added
- `supervisor.sh` now manages all three mobile services (tier1 server :8443,
  Flask web dashboard :8080, mobile daemon) — previously only the daemon was
  supervised. Ancillary services auto-restart if they exit unexpectedly.
  `DSLV_WEBDASH_HOST` defaults to `0.0.0.0` so the dashboard is reachable on LAN.
- `install_zpdi_mobile.sh` Rev 5: `pip install -e ".[dev]"` replaces bare
  requirements.txt install; `hdf5-tools` apt package added (provides `h5clear`);
  complete `.env` with all 16 required variables including AES-256-GCM + HMAC keys,
  server host/port, webdash host/port, and path variables; non-destructive
  `add_if_missing` upgrade path for existing installs; boot script copied from
  repo (`termux-boot/99-start-zpdi.sh`) instead of inlining a stale duplicate;
  runtime directories created; post-install smoke test runs full pytest suite.
- `.gitignore` now excludes `.grok/` (Grok agent workspace), `logs/` (runtime
  logs), and `*.pid` (daemon PID files).

### Changed
- `README.md`: mobile node prerequisites and "Connect the Pixel 9 Pro XL" section
  updated to reflect the current three-service WSS-based architecture with
  one-shot installer, service table, start/stop commands, and health check.
- `docs/collaboration/README.md`: local checkout path corrected to `/root/dslv-zpdi`
  (Pixel 9 Pro XL / GrapheneOS / PRoot Debian).
- `CREW_MEMORY.md`: updated to 2026-06-19 with v5.0.0 feature inventory, mobile
  hardware config table, and post-sync next-actions.

## [Unreleased] — Repository hardening follow-up (2026-06-17)

### Fixed
- Simulator Tier-1 HAL construction now uses an explicit simulated timing
  authority instead of opening real PPS/NMEA devices during `--simulator` runs.
- Layer 2 strict mypy target annotations now cover baseline persistence and BCI
  ingest/reset methods.
- Conventional Commit local hook now uses a real script instead of a malformed
  shell file with literal newline escapes.

### Changed
- Python support policy reconciled to 3.10 through 3.14, with Python 3.13 as the
  local development and requirements-generation interpreter.
- Docker runtime drops to a non-root user after build-time validation.
- Package license metadata now uses a SPDX license expression compatible with
  current setuptools guidance.
- Node receiver and web dashboard bind hosts are configurable and default to
  loopback for safer local development.
- HTTP fallback clients validate URL schemes before local `urlopen` calls.

### CI/CD
- CodeQL upgraded to v4 with explicit code scanning permissions, scheduled
  scanning, and scoped analysis paths.
- Docker workflow now lowercases GHCR image tags, skips publication on pull
  requests, scans the AMD64 image with Trivy, and emits SBOM/provenance.
- Dependency Review now checks pull-request dependency diffs for high-severity
  advisories and denied copyleft licenses.
- Release workflow now verifies tag/package version consistency, builds wheel
  and sdist artifacts, validates metadata, and publishes checksums.
- PR title validation enforces the repository Conventional Commit policy.
- GitHub Discussions enabled; category setup and audit/accountability boundaries
  are documented.

## [5.0.0] — PlutoSDR+ Tier-1 hardware pivot (2026-06-15)

### Added
- Capability-based Tier-1 hardware qualification engine (`src/dslv_zpdi/layer1_ingestion/sdr/qualification.py`, SPEC-004A.QUAL).
- Composed `HardwareHAL` separating timing authority, SDR backend, frequency translation, and qualification policy (`src/dslv_zpdi/layer1_ingestion/hardware_hal.py`, SPEC-005A.HAL).
- Native libiio PlutoSDR+ backend (`src/dslv_zpdi/layer1_ingestion/sdr/pluto_iio.py`, SPEC-004A.PLUTO).
- Structured timing attestation with explicit evidence dimensions (`src/dslv_zpdi/layer1_ingestion/timing/attestation.py`, SPEC-005A.TIMING).
- `LBE1421TimingAuthority` composing PPS, NMEA, and chrony evidence.
- Key-provider abstraction with file, env, systemd credential, and development providers (`src/dslv_zpdi/core/key_provider.py`, SPEC-018).
- HDF5 event hash chain and atomic `.partial` → `.h5` finalization (`src/dslv_zpdi/layer3_telemetry/hdf5_writer.py`, SPEC-007).
- YAML node profiles under `config/node_profiles/` with safe env-variable expansion (`src/dslv_zpdi/config_models.py`, SPEC-004A.CONFIG).
- New CLIs: `dslv-zpdi-probe`, `dslv-zpdi-preflight`, `dslv-zpdi-verify` (`src/dslv_zpdi/cli/`, SPEC-011.CLI).
- Optional dependency groups `[pluto]`, `[hackrf]`, `[hardware]` in `pyproject.toml`.

### Changed
- Tier-1 canonical RF instrument is now a capability-qualified PlutoSDR+ class device; HackRF One is the legacy minimum reference floor.
- Timing claims are no longer collapsed into a single `phase_lock_verified` Boolean; each evidence dimension is represented separately.
- `pyhackrf` moved from mandatory to optional `[hackrf]` dependency group.

### Security
- Production HMAC key absence now blocks primary output when `allow_development_key=False`.
- Event hash chain detects deleted, reordered, altered, or injected events.

### Documentation
- Baseline audit in `docs/audits/PLUTOSDR_PIVOT_BASELINE_AUDIT.md`.
- Implementation plan in `docs/superpowers/plans/2026-06-15-plutosdr-tier1-pivot.md`.

## [4.8.1] — Grok autonomous Pixel simulator session (2026-06-11)

### Fixed
- **Task A (critical)**: `hal_hardware.py` SoapySDR and pyhackrf top-level guards changed from bare `except ImportError:` to `except (ImportError, OSError):`. The `hackrf` package (and Soapy) execute `CDLL('libhackrf.so.0')` (and equiv) at *import time*, raising `OSError` (not `ImportError`) when the native shared object is absent (this proot Pixel / GrapheneOS simulator-only host has no libhackrf). This previously caused 0 tests collected (test_hardware_failure_paths + test_timing_monitor via lock_monitor). Now 113 tests collected + passing on no-hw host. Added Rev 4.8.x explanatory comments referencing governing `SPEC-005A.HAL-HW`.
- Audit of sibling native guards: broadened h5py guards in `hdf5_writer.py` (SPEC-007) and `radon_session_writer.py` (SPEC-018); broadened bleak/dbus guards (existing + bare `from bleak` sites) in `radoneye_ingestor.py` (SPEC-015). Pure-Python guards (flask in node_receiver.py, pyserial inside funcs in hal_hardware.py:827 and nmea_stream.py:92) left as `ImportError`-only — they never load .so at import time; their OSErrors are runtime port/serial conditions already handled separately. Justified in work report.
- **Task B**: stray hardcoded "Rev 4.7.1" in `tests/test_pipeline.py:145` replaced by `from dslv_zpdi import __version__` (now prints Rev 4.8.1 and can never desync). `check_version_sync.py` remains clean. Cosmetic banner appends in hal_*.py docstrings (no orphan noise).
- **Task C** (per NEXT_STEPS P2): added 10 new contract tests in `tests/test_node_receiver.py` (SPEC-014.8) covering `/api/v1/ingest`, `/api/v1/ingest/radoneye`, `/api/v1/health` for malformed JSON, missing required, writer-failure (500), and concurrent POSTs. Uses Flask test client + injected writers for isolation. Node receiver coverage lifted from 0%. Extended `specs/SPEC-014.md` with test section. No new public contracts; RadonEye remains secondary-only. No Tier-1 promotion, no metrology changes.
- All per `AGENTS.md` / `CONTRIBUTING.md` / orphan_checker / repo_guard. Full §2 contract green before/after each commit. 113 passed / ruff clean / version-sync clean / coverage ~53%+ (node_receiver now exercised).

### Changed
- Version bump 4.8.0 → 4.8.1 (behavior change for simulator hosts + new test surface coverage). All authorities synchronized: pyproject.toml, __init__.py, README revision line, CHANGELOG.md, new RELEASE_NOTES_v4.8.1.md.

## [Unreleased] · Repository Hardening (2026-06-10)

Repository infrastructure and trust hardening. No runtime/hardware behavior of the
trust pipeline, RF ingestion, GPSDO/timing, HDF5 schema, or metrology algorithms
was changed.

### Fixed
- **4 failing tests on `main`** — the Phase 2B async tests (SPEC-015/020) were
  marked `@pytest.mark.asyncio` but `pytest-asyncio` was absent, so the coroutines
  never executed. Added the dev dependency and `asyncio_mode=auto`; full suite now
  103 passed.
- **Version desync** — `pyproject.toml` / `__init__.py` / README declared 4.7.2
  while the `v4.8.0` tag and CHANGELOG already named 4.8.0. Reconciled all version
  authorities to 4.8.0 and added `RELEASE_NOTES_v4.8.0.md`. `check_version_sync`
  clean.
- Removed two dead local assignments; logged Pixel poll latency at debug instead
  of discarding it; dropped an unused `psutil` import.

### Changed
- **117 ruff findings cleared** across the Phase 2B modules (annotation
  modernization, import hygiene). Unit-encoded schema identifiers
  (`radon_pCiL`, `radon_Bqm3`, `pressure_hPa`, `dp_dt_hPa_h`) were preserved with
  scoped `# noqa`, not renamed.

### CI/CD
- Rewrote `.github/workflows/dslv_zpdi_ci.yml` from an orphan-checker + 10-test
  smoke into a full matrix (Python 3.10–3.13) running editable install, `pip
  check`, version sync, orphan checker, repo guard, ruff, the full pytest suite
  with coverage, the pipeline smoke test, and a separate package-build job with a
  clean-wheel install smoke test. Least-privilege token, timeouts, pip caching,
  and concurrency cancellation.

### Security
- Added `SECURITY.md` (private vulnerability reporting, evidence-integrity scope,
  redaction policy).
- Added `.github/dependabot.yml` for pip, github-actions, and docker ecosystems.
- Enabled Dependabot vulnerability alerts and automated security updates.

### Packaging
- Added `[tool.coverage]` configuration (branch coverage, `fail_under=50`;
  simulator baseline ~53%).
- Verified `python -m build` + `twine check` + clean-venv wheel install at 4.8.0.

### Repository management
- Added structured YAML issue forms (`bug_report`, `feature_request`,
  `hardware_incident`) + `config.yml`, replacing the single markdown bug template.
- Added `CODEOWNERS`, `docs/README.md` index, `compose.yaml` (simulator-first,
  opt-in hardware profile), and `.dockerignore`.
- Extended `.gitignore` for coverage/build artifacts.

## [4.8.0] - 2026-06-05 · Phase 2B: Radon Validation Metrology Stack (Tier 2)

### Added
- **RadonEye Pro RD200P ingestor** (`src/dslv_zpdi/layer1_ingestion/radoneye_ingestor.py`, SPEC-015) — BLE GATT primary transport (known FTLab UUIDs), HTTP fallback, simulator for CI. Reads radon concentration in Bq/m³ with ±7% accuracy per EcoSense datasheet. Falls through BLE → HTTP → SIM with graceful degradation.
- **Pixel 9 Pro XL mobile node bridge** (`src/dslv_zpdi/layer1_ingestion/pixel_node_bridge.py`, SPEC-016) — HTTP polling bridge (Termux JSON publisher) with trust scoring (0.0–1.0). Surfaces magnetometer, GPS fix, camera perceptual hash. Trust threshold configurable (default 0.5); scores < threshold flagged for review.
- **Pi–Pixel uplink manager** (`src/dslv_zpdi/layer1_ingestion/uplink_manager.py`, SPEC-017) — Monitors hotspot connectivity (`10.42.0.2:8777`), classifies state as online / offline / degraded. Triggers backfill replay when uplink restored. Never blocks Tier 1 primary stream.
- **HDF5 schema extension** (`src/dslv_zpdi/layer3_telemetry/radon_session_writer.py`, SPEC-018) — 5 new top-level branches (`certified_crm`, `macro_atmosphere`, `space_weather`, `mobile_node_tier2`, `validation_index`) written alongside existing event groups. Signed manifest with per-branch SHA-256 checksums and HMAC attestation for tamper detection.
- **Barometric coherence engine** (`src/dslv_zpdi/layer2_core/barometric_coherence.py`, SPEC-019) — χ(τ) cross-correlation between radon and barometric pressure with optional RH weighting. Pilot threshold 0.65 (configurable 0.60–0.70). Review flag explicitly subordinate to certified CRM result; BCI never overrides certified data.
- **48-hour session orchestrator** (`src/dslv_zpdi/orchestrator/radon_session.py`, SPEC-020) — Manages full 48-hour campaign lifecycle: init → run → finalize → summary. Resume from JSON cache on interruption. Generates compound `.h5` audit file + human-readable `.txt` summary.
- **Dashboard panel suite** (`tools/dashboard/panels/radon.py`, `mobile.py`, `bci.py`, SPEC-021) — Three new panels surfaced in existing compact/wide layout. RADON panel shows live radon concentration and device mode. MOBILE/T2 panel shows trust score and node state. BCI panel shows χ value, threshold band, and review flag. Zero aesthetic regression; new snark lines added to humor pool.
- **`SensorModality.RADON`** — Added to ingestion enum contract (`payload.py`) for downstream routing.
- **`bleak>=0.21.0`** dependency — BLE GATT transport support.
- **New documentation:** `docs/RADONEYE_GATT_MAP.md`, `docs/PIXEL_NODE_SETUP.md`, `docs/KIMI_BRANCH_AUDIT.md`, `docs/KIMI_PHASE2B_INTAKE.md`, `docs/KIMI_QUESTIONS.md`.
- **New specs:** SPEC-014 (real content, was stub), SPEC-015 through SPEC-021.

### Fixed
- **27 pre-existing SPEC-ID orphan gaps** — `node_receiver.py` (7), `pps_listener.py` (8), `nmea_stream.py` (8), `hal_hardware.py` (1), plus creation of real `specs/SPEC-014.md`. `orphan_checker.py` now green.
- **LBE-1420→LBE-1421 typos** in `V3_DSLV-ZPDI_LIVING_MASTER.md` — two instances where dual-output GPSDO was misidentified as single-output.
- **Dual-output architecture clarity** in `PHASE_2A_TIER_1_BUILD_SHEET.md` — new section documenting LBE-1421 Out1 (1 PPS → GPIO 18) and Out2 (10 MHz → HackRF CLKIN) independence.

### Changed
- `tools/dashboard/app.py` — imports + instantiates 3 new panels; layout builder and render loop updated. Toggle keys `4` (RADON), `5` (MOBILE), `6` (BCI) added.
- `tools/dashboard/config.py` — `PanelsCfg` extended with `radon`, `mobile`, `bci` booleans.
- `tools/dashboard/humor.py` — 11 radon-themed snark lines added to pool.
- `pyproject.toml` / `requirements.txt` — `bleak>=0.21.0` added.

### Tests
- 56 new tests added across 6 modules (SPEC-015 through SPEC-020). All green.
- Total suite: 94 passing (excluding 2 pre-existing flaky hardware tests tied to real HackRF state).
- `orphan_checker.py` green before every commit.


## [4.7.2] - 2026-06-01 · Robustness, Reliability & Security Hardening

Quality-and-hardening pass focused on system stability and trustworthy data
output. No functional behaviour of the trust pipeline changed; the work tightens
shutdown safety, the swarm receiver's attack surface, and overall code health.

### Fixed
- **Graceful pipeline shutdown (data-integrity)** — `main_pipeline.py` no longer
  calls `os._exit(0)` from the signal handler, which could leave the active HDF5
  file truncated. SIGINT/SIGTERM now cooperatively drain the worker threads and
  flush/close the writer, the timing monitor, and the health reporter. SIGTERM
  (used by systemd) is now handled in addition to SIGINT.
- **`cm5_ingestion` import crash (latent bug)** — the deprecation shim imported
  `BaseHAL` from `hal_factory`, which never exported it; importing the module
  raised `ImportError`. `hal_factory` now re-exports the canonical HAL surface
  (`__all__`), and all 31 package submodules import cleanly.

### Security
- **Node receiver request-size cap** — the Flask swarm receiver now enforces
  `MAX_CONTENT_LENGTH` (1 MiB), rejecting oversized bodies before they are
  buffered into memory.
- **Concurrent node-registry safety** — `node_registry.jsonl` updates are now
  serialized under a lock and written atomically (`tmp` + `os.replace`), removing
  a read-modify-write corruption race under concurrent POSTs.
- **RadonEye input validation** — non-numeric `radon_bq_m3` now returns a clean
  `422` instead of surfacing a `500`.
- **Insecure attestation key is now loud** — `HDF5Writer` emits a warning when it
  falls back to the development HMAC key so it cannot silently reach the field.

### Changed
- **Code health** — ruff is clean across `src/`, `tools/`, and `tests/`
  (~240 issues resolved: import hygiene, PEP 585/604 type modernization behind
  `from __future__ import annotations`, whitespace, bare `except`, dead variables,
  unsafe comparisons). Pylint rating improved from 9.31 to 9.64/10.
- **Single-source version** — `dslv_zpdi.__version__` is now defined and is
  enforced against `pyproject.toml` by `tools/check_version_sync.py`.
- **Structured logging** — the HAL factory hardware-fallback path now logs via the
  `dslv-zpdi.hal` logger instead of `print()`.
- **Hardening of timing probes** — subprocess clock probes specify `check=False`
  explicitly and catch narrow, expected exceptions instead of bare `except`.

## [4.7.1] - 2026-05-30 · Tier 1 / Tier 2 Node Optimization & Communication Refinement

### Fixed
- **pyhackrf LNA/VGA Gain Log Spam** — removed redundant print statements in `pyhackrf` site-package that caused severe stdout spam during rapid SDR capture cycles.
- **ComplexWarning in hal_hardware.py** — corrected the pyhackrf ingestion flow which was redundantly converting complex data from `read_samples` into interleaved structures, discarding the imaginary parts and raising a `ComplexWarning`.
- **NMEA Stream Serial Exception** — implemented exception handling for the `pyserial` bug where the device reports readiness to read but returns no data, avoiding pipeline restarts and silent drops on `/dev/ttyACM0`.
- **Chronyc Jitter Monitor Stability** — resolved large PPS jitter reporting by forcing chronyc to step the system clock (`chronyc makestep`), aligning the system time with the GPSDO time.
- **Validation Compliance Repair** — restored clean version-sync and orphan-checker results by adding v4.7.1 release notes, synchronizing the README revision, and adding missing SPEC-ID coverage in new ingestion and node receiver paths.

### Added
- **Shared Collaboration Workspace** — added `docs/collaboration/` as the common operating layer for Gemini CLI, Claude Code, Kimi Code, and Codex CLI with setup, validation, turnover, asset, and next-step guidance.

## [4.7.0] - 2026-05-30 · Node Bridging, HDF5 Multi-Node Aggregation & Dashboard Finalisation

### Added
- **PiRepo hotspot configuration** (`config/PiRepo.nmconnection`) — NetworkManager keyfile
  to create a 2.4 GHz AP (SSID `PiRepo`) on `wlan0`. The Pi 5 holds static IP
  `10.42.0.1/24`. Pixel 9 Pro XL (GrapheneOS) and additional swarm nodes connect here.
- **HackRF boot initialisation service** (`config/dslv-zpdi-hackrf-init.service`) — runs
  `hackrf_info` once after udev settles USB, waking the device out of cold-start before
  the pipeline preflight. Failure is non-fatal (pipeline falls back to SimulatedHAL).
- **Mobile node telemetry receiver** (`src/dslv_zpdi/layer3_telemetry/node_receiver.py`,
  `config/dslv-zpdi-node-receiver.service`) — Flask micro-service on port 5775 that
  accepts JSON telemetry POSTs from any swarm node (Pixel 9 Pro XL, future nodes) and
  forwards them into the local HDF5Writer pipeline.
- **RadonEye Pro staging endpoint** (`POST /api/v1/ingest/radoneye`) — SPEC-015
  placeholder; validates EcoSense RadonEye Pro payloads and writes them to
  `secondary/radoneye_staging.jsonl`. Full primary-stream promotion deferred pending
  SPEC-015 calibration baseline ratification.
- **Web dashboard** (`tools/dashboard/web_server.py`, `config/dslv-zpdi-webdash.service`)
  — read-only HTML dashboard at port 8080 displaying system, pipeline, swarm node, and
  SDR status panels. Auto-refreshes every 5 s. Accessible to any device on the PiRepo LAN.
- **`source_node` attestation field** in HDF5 writer — every primary-stream group now
  carries a `source_node` HDF5 attribute identifying which physical node produced the
  packet, enabling per-node provenance tracing in aggregated files.

### Fixed
- **HardwareHAL SoapySDR/pyhackrf fallback** — when SoapySDR raises `DriverUnavailableError`
  and `PYHACKRF_AVAILABLE` is False (no fallback driver), the original exception is now
  re-raised instead of being silently swallowed. Previously the constructor succeeded with
  no SDR initialised, masking the configuration error. Fixes
  `test_no_devices_found_raises_driver_unavailable`.
- **Concurrent HDF5 writes** — `HDF5Writer._write_primary` now acquires a
  `threading.Lock` before touching the HDF5 file handle, preventing data corruption when
  the pipeline and the node-receiver HTTP server write to the same file concurrently.

### Changed
- **HackRF / real-SDR ON by default** — dashboard now sets
  `DSLV_DASHBOARD_REAL_SDR=1` at startup. Use `--no-real-sdr` CLI flag to start in
  simulated mode. Waterfall panel and footer SDR indicator reflect live HackRF data
  immediately on launch.
- **HDF5 file version bumped** to `3.3` (reflects `source_node` field addition and
  concurrent-write safety).
- `HDF5Writer.__init__` accepts an optional `source_node` parameter (default
  `"tier1-anchor"`) used to stamp every attestation block.

### Tests
- All 47 tests passing (previously 1 failing).

## [4.6.2] - 2026-05-08 · Chrony PPS Disambiguation Research

### Investigated
- **Chrony NMEA driver unavailable** — chrony 4.6.1 on this system was compiled without
  the NMEA refclock driver. `refclock NMEA ...` fails with "unknown refclock driver NMEA".
  The recommended NMEA + `lock GPS` configuration from the v4.6.1 session report cannot
  be applied without recompiling chrony or installing gpsd.
- **`prefer` without `trust` oscillates** — removing `trust` causes 30-second NTP/PPS
  toggle cycles as chrony alternately selects PPS and NTP pool sources. Worse than the
  original `prefer trust` behavior.
- **`makestep 0.5 -1` with `trust`** — unlimited stepping does not help with second-boundary
  oscillation because `trust` causes chrony to accept PPS as absolute truth, so NTP can
  never trigger a corrective step.

### Confirmed Working
- Restored original `refclock PPS /dev/pps0 poll 4 prefer trust` + `makestep 1 3` config.
  After clean chronyd restart this converges to stratum 1 at 5–20 µs in ~3–5 minutes.

### Known Remaining Issue
- PPS second-boundary disambiguation has no software fix in this chrony build.
  Long-term fix: install gpsd to read `/dev/ttyACM0`; configure chrony `refclock SOCK`
  from gpsd (SOCK driver IS compiled in). Pipeline's `NmeaStream` must be migrated from
  direct serial to gpsd protocol (USB CDC-ACM does not allow multiple readers).

### Operational Procedure
- If chrony PPS oscillates (NTP sources all `^x`, residual freq >1000 ppm, last offset >0.3 s):
  `sudo systemctl restart chronyd` — do NOT run manual `chronyc makestep`.
  Allow 10–15 min for NTP to anchor the correct second then PPS re-lock.

## [4.6.1] - 2026-05-08 · Tier 1 Operational Hardening

### Fixed
- **Timing monitor false SPEC-004A.3 violations** — `TimingMonitor._read_pps_jitter()`
  now reads chronyc `System time` (current instantaneous offset) instead of `RMS offset`
  (historical running average). RMS offset stays at 6–8 seconds during initial PPS lock
  acquisition, causing constant false violations even with a healthy GPSDO.
- **Double dashboard/waterfall instances on boot** — Two autostart entries
  (`dslv-zpdi.desktop` + `dslv-zpdi-dashboard.desktop`) both called `launch_project.sh`,
  producing duplicate windows and a second pipeline restart loop.
  `dslv-zpdi-dashboard.desktop` disabled (`X-GNOME-Autostart-enabled=false`).
- **HackRF device contention (pipeline vs. dashboard)** — `launch.sh` was exporting
  `DSLV_DASHBOARD_REAL_SDR=1`, causing `hackrf_sweep` to start immediately and hold the
  HackRF exclusively, forcing the pipeline into SimulatedHAL on every service restart.
  Removed the auto-export; waterfall defaults to SIM, users toggle real-SDR with `r`.
- **HackRF probe retry** — `_verify_pyhackrf_clock()` now retries 3× with 2 s delay
  before falling back to SimulatedHAL, surviving brief contention windows at startup.

### Security / Hardware
- **HackRF amplifier hard lockout** — `WaterfallPanel.toggle_amp()` is now a permanent
  no-op; `_ingest_pyhackrf()` explicitly calls `set_amp_enable(0)` before every SDR
  capture; dashboard `a` key shows a hardware-fault warning instead of toggling.
  HackRF 1 front-end amp is blown — parts on order.

### System
- **GNOME Keyring auto-unlock** — Added `~/.config/autostart/keyring-unlock.desktop` to
  unlock the keyring via `gnome-keyring-daemon --replace --unlock` on auto-login sessions.
  Added `pam_gnome_keyring.so auto_start` to `/etc/pam.d/lightdm-autologin`.

## [4.6.0] - 2026-04-27

### Fixed
- Installer one-shot reliability: idempotent venv creation, bootstrap shallow-clone fix
- Dynamic REPO path resolution in preflight.sh, launch_project.sh, dashboard/launch.sh
- SoapySDR find command precedence in Tier-1 provisioning
- Version synchronization across pyproject.toml, README, CHANGELOG, and release notes


All notable changes to the DSLV-ZPDI project will be documented in this file.

## [4.5.2] - 2026-04-26

### Fixed
- **Silent data loss in main pipeline (SPEC-011.5).** When the timing
  monitor was unhealthy or the payload arrived as `SECONDARY_QUARANTINED`,
  the synchronous and threaded run loops both skipped the writer entirely,
  leaving no forensic record. Both paths now mutate the payload with a
  tagged quarantine reason (`timing_unhealthy` /
  `upstream_quarantine`) and route it through the writer so every
  observation lands in `secondary/quarantine.jsonl`.
- `TimingMonitor` no longer reads host `chronyc` when the pipeline is
  in simulator mode. A new `simulated=` flag selects a synthetic jitter
  source matching `DSLV_SIM_TIMING` (gpsdo: ~10 ns, ntp: ~3 ms),
  decoupling sim/CI runs from host clock health and eliminating the
  start-up race that dropped the first batch of payloads.
- `TimingMonitor.healthy` now starts `True` (optimistic) so payloads
  ingested between `start()` and the first jitter read are not dropped.
- `tests/test_hdf5_schema.py` — was passing only because the assertion
  was OR-ed against an HDF5 file count that was always 0; now exercises
  the new forensic-completeness guarantee.

### Added
- `PipelineState.note_quarantine()` — counts quarantine reasons and
  surfaces them through the SPEC-014 health endpoint
  (`/run/dslv-zpdi/health.json`).
- Health endpoint now exports `timing_jitter_ns`, `timing_threshold_ns`,
  and `quarantine_reasons` for downstream observability.
- Dashboard `PipelinePanel` rebuilt against the live health endpoint:
  surfaces PRIMARY/SECONDARY counts, integrity counters
  (`fail/miss/inv/rej`), baseline state, timing health + jitter,
  HDF5 byte volume, node ID, and HAL mode.
- Dashboard `SystemPanel` now shows data-partition disk usage with
  green/yellow/red banding.

### Changed
- `tests/test_integration.py` — assertion strengthened to require a
  non-empty `quarantine.jsonl`, locking in the no-silent-drop guarantee.
- `TimingMonitor` constructor signature extended (backwards compatible
  via keyword args).

## [4.5.1] - 2026-04-24

### Added
- `tools/health_check.sh` — 8-subsystem Tier 1 node validator (exit 0/1/2).
- `config/dslv-zpdi-tuning.service` — tracked in repo (CPU governor, USB power).
- Dashboard config integration: `app.py` loads `dashboard.toml` for refresh, theme, waterfall defaults, notifications.
- Dashboard keybindings: gain (+/-, g), amp (a), tune (</>), zoom (z/x).
- Waterfall hot-plug detection, timestamp tracking, linear interpolation resampling.
- Mapping temporal filters (`--since`, `--until`) and toggleable heatmap layer.
- Mapping `r_smooth`-weighted coordinate scatter for data-driven positioning.

### Changed
- `hal_hardware.py` — PPS jitter now uses interval-stdev ring buffer; IQ phase via `np.angle(complex_baseband)`; SoapySDR error handling; guarded NMEA parsing.
- `hal_simulated.py` — IQ phase extraction aligned to complex analytic signal.
- `coherence.py` — eliminated duplicate baseline sampling by delegating to `update_baseline()`.
- `wiring.py` — `CORE_PROCESSED` accepted for packet reprocessing.
- `main_pipeline.py` — captures coherence RoutingDecision, logs PRIMARY events, emits 60s status heartbeat; uses absolute output paths.
- `config/dslv-zpdi.service` — defaults to hardware mode; removed hardcoded `--simulator`.
- `config/dslv-zpdi-baseline.service` — correct paths and `dynogator` user.
- `config/deployment.yaml` — absolute paths throughout.

### Fixed
- PPS jitter modulo wrap-around bug (catastrophic offsets appeared as near-zero).
- Incorrect Hilbert transform on complex IQ data (discarded Q channel).
- Silent SoapySDR stream errors (return code ignored).
- Unhandled NMEA empty-field `ValueError` crashes.
- Dashboard filesystem probe performance (`find` → cached `os.listdir`).
- LogPanel infinite retry spam on missing systemd unit.
- Mapping `_tail_lines` double-pass performance issue.

## [4.5.0] - 2026-04-24

### Added
- Dashboard v2: 5" DSI-optimized layout, NOAA space-weather panel, storm/anomaly/weather/waterfall panels, TOML config.
- Auto-email telemetry pipeline (`tools/mailer/`): SMTP/SendGrid/SES backends, daily/alert dispatch, interactive configuration TUI.
- Interactive geospatial mapping (`tools/mapping/`): Folium HTML maps, HDF5 aggregation, quick-launch scripts.
- Project launcher (`tools/launch_project.sh`) with clean-boot preflight, dual-window spawn, and simulator toggle.
- Runtime configuration examples: `dashboard.toml.example`, `email.example.yaml`, `sensor_location.example.yaml`.
- `tests/conftest.py` with shared pytest fixtures.

### Changed
- `main_pipeline.py` — unified simulator resolution (`_resolve_simulator`), graceful signal handling, demo-node rotation mode.
- `wiring.py` — baseline state path resolution with env override.
- `hal_simulated.py` — simulator fidelity aligned to SPEC-005A.HAL-SIM.
- `.gitignore` — expanded agent-workspace and artefact coverage.
- README bumped to Rev 4.5.0 — LBE-1421 Hardened Operations Stack.

### Fixed
- Launcher race conditions on clean-boot dual-window startup.
- Pipeline baseline state not loaded into coherence engine on cold start.

## [4.4.0] - 2026-04-15

### Added
- `src/dslv_zpdi/main_pipeline.py` — SPEC-011 production pipeline loop with `--field` baseline mode.
- `tools/capture_baseline.py` — 72 h passive baseline capture script (SPEC-009.1).
- Canonical HAL factory `get_hal(tier, simulator)` per SPEC-005A.4.
- Hilbert phase extraction in `HardwareHAL` and `SimulatedHAL` (Layer 1, 64-item preview).
- Thermal/acoustic ingest hooks in `HardwareHAL` (Layer 1 modality expansion).
- udev rules (`99-pps.rules`, `52-hackrf.rules`) and `systemctl enable chrony` in installer.
- CI matrix expansion for Python 3.10–3.13 and Pi 5 self-hosted hardware runners.
- RP1 3.3V hard enforcement guard in `provision_tier1.py` and build sheet.

### Changed
- `hal_hardware.py` — NMEA telemetry integrated into `ingest_gps_pps()`, IQ serialization aligned to 64-item preview.
- Schema bumped to 3.2 in `payload.py`, `tier1_policy.py`, and `hdf5_writer.py`.
- Version alignment to Rev 4.4.0 across README, installer, tests, and release notes.

## [4.3.1] - 2026-04-15

### Added
- Canonical exception hierarchy in `core/exceptions.py` (SPEC-005A).
- Tier 1 policy contract module (`contracts/tier1_policy.py`) centralizing clock, baseline, and routing constants (SPEC-009).
- Event deduplication/cooldown in `CoherenceScorer` to prevent duplicate global-event flooding.
- Real HDF5 rotation tests verifying file close/open/reset behavior.
- Hardware failure-path mock tests covering SoapySDR, pyhackrf, serial/NMEA, and HDF5 unavailability.
- `mypy` and `ruff` to dev dependencies and `pyproject.toml` config.
- CI matrix expansion (local) for Python 3.10/3.11/3.12 and Debian bookworm/trixie.

### Changed
- SDR JSON serialization now emits serializable `[[I,Q],…]` pairs; `iq_samples` are digested unconditionally with a 64-item preview.
- `HardwareHAL` now raises `HardwareInitializationError`, `ClockVerificationError`, and `DriverUnavailableError` instead of calling `sys.exit(1)`.
- Clock verification fails closed: unknown/internal clock sources are rejected.
- `HDF5Writer.ingest()` enforces packet integrity before primary write; new stat counters added.
- `DualStreamRouter` uses dynamic baseline threshold for primary and `dynamic_threshold * 0.5` for candidate routing.
- `IngestionPayload.validate()` now validates modality, schema version, raw_value shape, phase bounds, and RF clock source.
- Renamed canonical HAL factory to `hal_factory.py`; `cm5_ingestion.py` retained as deprecated wrapper.
- README status updated from "Hardware Airtight" to "Beta — hardware transition complete; awaiting Tier 1 baseline capture validation".
- Canonical source banners added to build sheet and PDF guide folder.

### Fixed
- Potential runtime JSON serialization break on 512-length complex IQ sample lists.
- False-positive clock verification in pyhackrf fallback path.
- Missing live-gate enforcement for packet checksum verification.

## [4.3.0] - 2026-04-15

### Added
- **Multi-OS Support:** Formal validation for Raspberry Pi OS Trixie (Debian 13).
- **SoapySDR Venv Linkage:** Automated symlinking of system `python3-soapysdr` to venv.
- **OS Detection:** Added Debian codename and version detection to installer.

### Changed
- **Installer:** Hardened `install_dslv_zpdi.sh` for multi-OS firmware path compliance.
- **Version Alignment:** Synchronized to Rev 4.3.0.

## [4.2.1] - 2026-04-15

### Fixed
- **Dependencies:** Corrected `pyhackrf` version requirement from `>=1.0.0` (non-existent) to `>=0.2.0`.
- **Installer:** Resolved installation failure in `install_dslv_zpdi.sh` due to invalid `pyhackrf` version.

## [4.2.0] - 2026-04-11

### Added
- **LBE-1421 GPSDO Migration:** Migrated Clock Authority from Leo Bodnar Mini GPSDO to Leo Bodnar LBE-1421 GPSDO (USB-C, NMEA telemetry, 3.3V CMOS native output).
- **NMEA Telemetry:** Added `verify_nmea_telemetry()` to HardwareHAL and NMEA check to provisioning tool for GPS fix verification via virtual serial port.
- **RF/Magnetic Shielding Docs:** Created `docs/RF_MAGNETIC_SHIELDING.md` — cyberdeck chassis design with conduction cooling, compartmentalization, galvanic isolation, and pass-through security.
- **Hardware Change Justification:** Created `docs/HARDWARE_CHANGE_JUSTIFICATION.md` (SPEC-UPDATE-PHASE-2A-LBE-1421).
- **Updated BOM:** Added ANT500 antenna, SMA cabling, and jumper wire specifications to Tier 1 mandatory BOM.

### Changed
- **Dependencies:** Replaced `pyrtlsdr` with `pyhackrf` in core dependencies. RTL-SDR is Tier 2 only.
- **Version Alignment:** Synchronized all version references to 4.2.0 across pyproject.toml, README, installer, tests, specs, tools, and MASTER_SPEC documents.
- **RP1 Voltage Warning:** Updated to reflect LBE-1421 native 3.3V compatibility (no level-shifter needed).
- **Physical Routing Protocol:** Updated wiring instructions for LBE-1421-specific connections (USB-C power/telemetry, 3.3V PPS).
- **Installer:** Removed `rtl-sdr`/`librtlsdr0` from base packages (not on critical build path).

### Deprecated
- **Leo Bodnar Mini GPSDO:** Formally superseded by LBE-1421. Mini-USB connection unreliable for field ops.

## [4.0.2.4] - 2026-04-10

### Added
- **Architectural Hardening:** Implemented SPEC-010 (Packet Integrity), SPEC-009.1 (Atomic Baseline Persistence), SPEC-008.2 (Temporal Freshness), SPEC-005A.5 (Immutable IQ Digest), and SPEC-004A.3 (Continuous Timing Health Monitor).
- **Build Documentation:** Integrated `PHASE_2A_TIER_1_BUILD_SHEET.md` with explicit date/pricing disclaimers.

### Fixed
- **CI Reliability:** Resolved race condition in `orphan_checker.py` via robust parent-child mapping.
- **Test Environment:** Fixed `PYTHONPATH` and `sys.path` discrepancies in GitHub Actions and regression suite.
- **Code Integrity:** Resolved `E0602` (undefined logger) and multiple styling violations in core modules.

## [4.0.2] - 2026-04-09

### Added
- **Unified Installer:** Deployed `install_dslv_zpdi.sh` for automated deployment and hardware audit.
- **Hardware Agnostic Detection:** Expanded installer detection for CM4, CM5, Pi 4, and Pi 5 (SPEC-004A.1 compliance).
- **Simulator Mode:** Exposes `--simulator` flag for virtualized Tier 1 hardware audits.

### Changed
- **Installation Workflow:** Optimized dependency management and venv creation.
- **Root-Safe Execution:** Installer now handles `sudo` and `git safe.directory` protocols.

## [3.5.3] - 2026-04-09

### Added
- **Node Calibration:** Implemented `tools/factory_calibration.py` for drift analysis (SPEC-004A.CAL).
- **Watchdog Enforcement:** Deployed `src/watchdog/mvip6.py` health monitor (SPEC-011).
- **Regression Suite Expansion:** Added `tests/test_watchdog.py` and `tests/test_calibration.py`.

### Changed
- **Payload Security:** Upgraded checksum metadata and hardened IQ digestion logic.
- **Stability:** Fixed syntax and escaping errors in test files.

## [3.5.2] - 2026-04-09

### Added
- **Timing Verification:** Deployed `tools/check_timing.py` and `tools/provision_tier1.py` for SPEC-004A.1 enforcement.
- **Unit Testing:** Added `tests/test_payload.py` and `tests/test_coherence.py`.
- **Checksum Metadata:** Added `checksum_algo` to `IngestionPayload`.

### Changed
- **Payload Hardening:** `IngestionPayload.to_json()` now autonomously digests large IQ arrays and updates its own checksum.
- **HAL Correctness:** Fixed SDR phase extraction in `HardwareHAL` to preserve quadrature data.

## [3.5.1] - 2026-04-09

### Added
- **HAL Architecture:** Implemented `BaseHAL`, `HardwareHAL`, and `SimulatedHAL` to decouple software from hardware.
- **CI/CD Pipeline:** Deployed GitHub Actions for automated orphan checking and regression testing.
- **Project Metadata:** Updated `pyproject.toml` with complete author, license, and classifier info.
- **Persistence Spec:** Added Appendix E (HDF5 Schema Specification) to the Living Master.
- **Docker Support:** Created `Dockerfile` for reproducible development environments.
- **GitHub Templates:** Added issue and pull request templates.
- **Onboarding:** Established `CONTRIBUTING.md` and MIT `LICENSE`.

### Changed
- **Router Logic:** Integrated `SwarmIntegrityMonitor` into `DualStreamRouter` (SPEC-008).
- **Core Optimization:** Migrated `coherence.py` to NumPy-based vector operations.
- **Test Alignment:** Synchronized `test_pipeline.py` and auxiliary scripts with Rev 4.0.2.4/3.5 implementation.

### Fixed
- Resolved API mismatches in `HDF5Writer` constructor and method names.
- Corrected filename and group-naming typos in integration tests.
- Fixed CI environment failures by ensuring dependency installation.

## [3.4.0] - 2026-04-08
- Phase 1 Software Sandbox officially sealed.
- HDF5Writer with cryptographic attestation deployed.
- Dual-Stream Protocol (quarantine vs kill) enforced.
