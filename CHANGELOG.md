# Changelog

## [5.3.4] — Dashboard & System Hardening Fixes (2026-08-26)

### Added
- **Audio Dependencies**: Added `alsa-utils` and `pulseaudio-utils` to the Tier 1 installer `BASE_PACKAGES` to ensure `demod_app.py` has a functional `aplay` or `paplay` backend for audio output on fresh installs.
## [5.4.0] - 2026-08-26
### Added
- **Tier 1 Node Supervisor:** Engineered \`dslv_launch_supervisor.sh\`, a robust startup orchestrator that sequentially initializes and verifies the state of the Pi Alpha systemd service chain before attempting to launch the TUI dashboard.
- **Mobile Node Bridge Verification:** Explicit process checks to guarantee the webdash API is bound and listening before downstream nodes attempt to connect.

### Changed
- Replaced the legacy \`launch_project.sh\` script completely in favor of the new supervisor.
- Refactored TUI dashboard launch flow to inherently block duplicate sessions via process guards against \`dashboard.app\`.
- Cleaned up python imports to fix a \`NameError\` and \`UnboundLocalError\` affecting dashboard state toggles.

### Removed
- Extraneous logging warnings regarding missing \`PlutoSDRplus-tools\`.
- \`dslv-zpdi-tier1.service\` ghost systemd unit from launch targets.

- **Service Boot Delays**: Increased startup delays in `launch_project.sh` to allow background services to fully initialize before the UI launches.

### Fixed
- **Dashboard Dual-Launch Bug**: Fixed a bug in `launch_project.sh` where both a standalone waterfall window and an integrated dashboard window were spawning concurrently. It now strictly enforces a unified single-window layout.
- **Real SDR TUI Crash & WAIT State**: Re-wrote the `PlutoSDRplusSweepStream` in `waterfall.py` to directly instantiate and manage `PlutoIioBackend` via Python rather than relying on a non-existent `PlutoSDRplus_sweep` C++ binary, eliminating the eternal "WAIT" state and preventing TUI crashes.
- **Firewall SSH Lockout**: Patched `nftables-dslv-zpdi.rules` to correctly scope the rate limit (5/minute) exclusively to `ct state new` packets. The previous rule inadvertently rate-limited all established SSH traffic, which bricked active SSH handshakes.

## [5.3.3] — Tier 1 Installer Reliability & Hardware Support (2026-08-25)

### Added
- **Tier 1 Installer Upgrades**: `install_dslv_zpdi.sh` now configures the `end0` network interface via NetworkManager, auto-generates production HMAC keys, and deploys `99-gpio.rules` for sysfs permissions automatically to ensure 0-touch deployment on Debian Trixie.
- **HamGeek Pluto+ Support**: Included `52-PlutoSDRplus.rules` udev rules explicitly targeting 0456:b673 to support custom Zynq SDR nodes without sudo.

### Fixed
- **Dashboard Boot Crash**: Resolved a fatal `SyntaxError` in `waterfall.py` caused by a stray control character and fixed a class naming typo (`PlutoSweepStream` -> `PlutoSDRplusSweepStream`) that crashed the TUI when `REAL_SDR` was invoked.
- **Mobile Node Discovery**: Updated `.env.example` to explicitly surface the Tier 2 `DSLV_PIXEL_STATUS_URL` configuration to prevent the bridge from trying to poll dead legacy subnets.

## [5.3.2] — Real-Time SDR Demodulation & UI Snappiness (2026-08-10)

### Added
- **Real-SDR Mode for DemodApp**: The advanced Demodulation Suite now ingests live `PlutoIioBackend` data when `DSLV_DASHBOARD_REAL_SDR` is enabled, actively demodulating live over-the-air signals (FM, AM, etc.).
- **Agent Context Tracking**: Added `GEMINI.md` to persist the system state vector automatically for AI assistants on reboot.

### Fixed
- **Dashboard Lag Fixed**: Removed blocking `time.sleep()` from `app.py` and `demod_app.py`, implementing non-blocking `select.select()` for instantaneous keystroke responsiveness.
- **Demodulation Math Bug**: Fixed phase-wrapping glitch in FM synthesis and implemented the correct mathematically-sound polar discriminator for live WFM SDR captures in `demodulation.py`.
- **AM Demodulation**: Added proper DC blocking for AM streams.

## [5.3.1] — Advanced Demodulation UI and Reliability Overhaul (2026-08-07)

### Added
- **Standalone Advanced Demodulation Suite (`demod_app.py`)**: A comprehensive rich TUI pop-out module.
- **PIN-Protected Restricted Menu**: Obfuscated feature unlocking via hotkeys (`*` or `Ctrl+X`) requiring PIN `1988` to unlock sensitive features.
- **Fox Hunting (TDOA/RSSI Vectoring)**: Live target vectoring estimation and reporting added to restricted systems.
- **Frequency Hopping Monitor**: Automated detection and tracking of fast-hopping emitters on the baseband spectrum view.
- **Advanced Radio Controls**: Full manual capability to adjust frequency (`F`), bandwidth (`B`), gain (`G`), and squelch (`S`) dynamically in the DemodApp.
- **Listen Mode**: Direct audio routing toggle (`L`) added to DemodApp.

### Changed
- Refactored `tools/launch_project.sh` to introduce highly robust, self-healing service initialization. Replaced blind `start` commands with chronological check-and-retry loops (up to 3 attempts with 5-second pauses) and explicit failure diagnosis.
- Substantially improved Dashboard function footer/legend clarity, switching to expanded descriptions for better user experience.
- Increased default `fps` in `dashboard.toml` to 30 for enhanced UI responsiveness and reduced input latency.
- Refined dashboard initialization script (`launch.sh`) and system state icons mapping on the desktop.

## [5.3.0] — Zero-Copy Binary Ingestion Refactor (2026-08-06)

### Added
- Zero-copy binary ingestion.
- Metrology plasmoid humor integrated into the Tier-1 provisioning script.

### Changed
- Removed Dependabot configuration (`.github/dependabot.yml`) to permanently resolve automated interference that was causing the repository release workflow to stall at `v5.1.0`. 
- Re-tagged and force-pushed `v5.3.0` to the latest commit to successfully trigger the GitHub Actions release workflow.

### Fixed
- Addressed multiple undefined variable and type-hint issues (`IngestionPayload`) in Layer 1 ingestors (`pixel_node_bridge.py`, `radoneye_ingestor.py`).
- Resolved undefined fallback function call (`check_plutosdrplus_presence`) in `tools/provision_tier1.py`.
- Thoroughly cleaned up the repository by purging duplicate and obsolete cache directories (`.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `__pycache__`).
- Passed a strict Ruff linting sweep, fixing 120+ trailing whitespace, string syntax, and bare except warnings across the HTML dashboard and core Python scripts.

## [5.2.0] — Demodulation Engine and MIMO Vectoring (2026-07-28)

### Added
- Built intelligent Demodulation engine (layer1_ingestion) supporting audio, data, video, and telemetry formats with auto-presets.
- Integrated Full Duplex MIMO Vectoring framework for spatial multiplexing and signal vectoring.

### Changed
- Dashboard default configs updated: Live SDR enabled, gain 0.0, raw modulation, sweep mode, center freq 3 GHz, span 40 MHz, plasma palette, LNA 30, VGA 30, noise floor -75.0 dBm, ceiling -70.0 dBm.
- Dashboard banner disabled by default.
- Dashboard default layout changed from compact to 10-inch optimized.

### Fixed
- Fixed ingestion pipeline PPS qualification parameter parsing for Tier-1 external reference profiles.
- Resolved `UnboundLocalError` scoping bug in `hal_factory.py` preventing PlutoSDR backend fallback.
- Added support and SPEC-004A.HackRF (legacy/optional) compliance for HackRF (legacy/optional) and LibreSDR backends.
- Repaired real-SDR hardware detection probes in `dashboard/panels/hardware.py` to gracefully degrade on failure.

## [5.1.0] — Mobile Node and TUI Refinements (2026-07-28)

### Added
- New standalone dashboard package `tools/zpdi_conditions/`:
  - Aggregates live space weather, surface weather, barometric, aerosol, and
    ionizing-radiation metrics for the Penrose, CO tracking footprint.
  - Sources: NOAA SWPC (Kp, RTSW wind/mag, scales), Open-Meteo (weather and
    air quality), NMDB real-time neutron monitor, EPA RadNet Colorado Springs.
  - Rich two-column TUI optimized for a 10" touchscreen with per-metric
    refresh intervals and last-refresh timestamps.
  - Manual refresh on spacebar; quit with `q` or `Ctrl+C`.
  - Self-checking collectors display source-specific errors inside each metric
    card instead of crashing the dashboard.
  - Launch script `launch.sh` and desktop icon `ZPDI_CONDITIONS.desktop` with
    `install_desktop_icon.sh` for one-click setup.
- No SDR, GPSDO, or radio hardware access; designed to run in parallel with the
  main `dslv-zpdi` stack without conflicts.

### Verified
- All 12 collectors return live data or clear errors.
- `pytest` 184 passed, 1 skipped; ruff/orphan/repo-guard/version-sync clean.
- Desktop icon installed and executable on the Tier-1 anchor node.

---

## [Unreleased] — Reboot preparation and local validation lock-in (2026-07-09)

### Added
- `docs/node_ops/REBOOT_PREP_REPORT.md` documenting the final local
  verification pass and expected post-reboot sequence.

### Changed
- Enabled `gpsd.service` so the LBE-1421 NMEA feed starts automatically on boot.
- Verified and locked in persistent boot configuration:
  - All DSLV systemd services are `enabled`.
  - Single autostart entry: `~/.config/autostart/dslv-zpdi-dashboard.desktop`.
  - Autologin for `dynogator` confirmed in LightDM and getty.
  - Passwordless sudo confirmed for the boot orchestrator.
- Synced installed systemd units from repo files; `diff` is clean across all
  DSLV services.
- Updated `docs/node_ops/WORK_LOG.md` and `docs/node_ops/TURNOVER_NOTES.md` with
  the reboot preparation checklist and post-reboot expectations.

### Verified
- Web dashboard `/api/status` shows real hardware state:
  - `chrony_stratum: 1`, PPS1 reference, RMS offset ~786 ns.
  - `sdr.mode: REAL`, `clock_src: external`, PlutoSDR+ reachable.
  - UPS telemetry live from MAX17048 on I2C-1.
- Pipeline baseline `LOCKED`; PRIMARY HDF5 events actively written.
- `pytest` 184 passed, 1 skipped; orphan/version-sync/repo-guard clean.

### Caveats
- Rich TUI waterfall panel remains SIM because no HackRF (legacy/optional) is connected; all
  other dashboard data is real.
- Touchscreen layout not visually verified in this session.

---

## [Unreleased] — Mono-node dev mode and automatic baseline lock (2026-07-09)

### Added
- **`DSLV_MIN_CONFIRMING_NODES`** environment variable support in
  `src/dslv_zpdi/layer2_core/wiring.py`; defaults to `4` for backward
  compatibility but is set to `1` on this node for standalone development.
- **Automatic baseline finalization**: `main_pipeline.py` now calls
  `coherence_engine.finalize_baseline()` every 60 seconds so the baseline FSM
  can transition `LEARNING → LOCKED` without manual intervention.
- **Optional fixed event threshold**: `DSLV_BASELINE_FIXED_THRESHOLD` in
  `src/dslv_zpdi/layer2_core/coherence.py` overrides the 3-sigma calculation
  for development environments.
- **Real `specs/SPEC-009.md`** documenting the baseline-learning FSM, state
  transitions, persistence, and environment parameters (was a placeholder stub).

### Changed
- **Mono-node configuration** in `.env`:
  - `DSLV_MIN_CONFIRMING_NODES=1`
  - `DSLV_BASELINE_HOURS=0.02`
  - `DSLV_MIN_BASELINE_SAMPLES=30`
  - `DSLV_BASELINE_FIXED_THRESHOLD=0.30`
- **`CoherenceScorer.start_baseline()`** is now idempotent for the `LEARNING`
  state, preserving accumulated samples and start time across pipeline restarts.
- **Service file cleanup**: corrected stale `/home/dynogator/Desktop/KIMI/...`
  paths in `config/dslv-zpdi-webdash.service`,
  `config/dslv-zpdi-preflight.service`, and
  `config/dslv-zpdi-tuning.service`; added resource/restart limits to webdash
  and UPS services.
- **Main pipeline unit hardening**: added `ProtectClock=true`,
  `ProtectHostname=true`, `RestrictAddressFamilies`, `SystemCallFilter=@system-service`,
  and timeout settings.

### Verified
- Full test suite: 184 passed, 1 skipped, 2 SWIG deprecation warnings.
- `tools/orphan_checker.py`, `tools/check_version_sync.py`, and
  `tools/repo_guard.py` all report clean.
- All systemd services active after service-file sync and restart.
- Web dashboard `/api/status` reports `baseline_state: LOCKED` and
  `pipeline.primary_written` > 0.
- Primary HDF5 file created in `output/primary/`.

### Caveats
- This is **development mono-node mode**. PRIMARY events are confirmed with a
  single node and a fixed low threshold. Revert to multi-node settings before
  production deployment.

---

## [Unreleased] — Tier-1 Pi 5 optimization & boot orchestrator (2026-07-09)

### Added
- **Retro ASCII boot orchestrator** (`tools/boot_orchestrator.py`) for the Tier-1
  Pi 5 touchscreen autostart path. It verifies/starts the systemd service chain in
  order, renders a Rich TUI with ASCII art, sequential stage list, rotating snark
  messages, and a status footer, then execs the operations dashboard on success.
- **Boot orchestrator desktop autostart** at
  `~/.config/autostart/dslv-zpdi-dashboard.desktop`; launches the orchestrator in
  a 120×40 `lxterminal` on Wayland login.
- **`docs/node_ops/TOOLCHAIN_AUDIT.md`** — full component-by-component evaluation
  of timing discipline, SDR ingestion, persistence/trust, UPS/power, dashboards,
  and process supervision, with alternatives and future-tool recommendations.
- **`docs/node_ops/TURNOVER_NOTES.md`** — concise collaborator hand-off covering
  node state, credentials, service commands, dashboard URLs, and caveats.
- **Live telemetry bridge through `/run/dslv-zpdi/health.json`**:
  `main_pipeline.py` now publishes `sdr_health`, `pps`, and `ups` snapshots every
  10 payloads; the web dashboard and TUI hardware panel consume them directly.
- **`SdrHealth.external_reference_configured`** field; `PlutoIioBackend.health()`
  populates it so the dashboard reports `clock_src: external` for GPSDO-disciplined
  PlutoSDR+ operation.

### Changed
- **Main pipeline systemd unit hardening**
  (`config/os-hardening/dslv-zpdi.service`): `ProtectSystem=strict`,
  `ProtectHome=read-only`, explicit `ReadWritePaths`, `CPUAffinity=2 3`,
  `MemoryMax=2G`, `LimitNOFILE=65536`, and `StartLimitIntervalSec=120` /
  `StartLimitBurst=3`. Installed unit synced and `daemon-reload` run.
- **PPS jitter metric stability**: `TimingMonitor` and `tools/check_timing.py`
  now read `RMS offset` from `chronyc tracking` instead of `System time` for a
  stable figure after chrony convergence.
- **Dashboard telemetry decoupling**: `tools/dashboard/web_server.py` and
  `tools/dashboard/panels/hardware.py` no longer re-probe hardware every refresh;
  they read the shared health JSON written by the pipeline.

### Security
- Project GitHub credentials stored in `.secrets/` (`git-credentials` and
  `github-account.txt`) with mode `0600`; `.gitignore` keeps them out of the repo.
  `./configure_git_auth.sh` activates a repo-scoped credential helper.

### Verified
- Full test suite: 184 passed, 1 skipped, 2 SWIG deprecation warnings.
- `tools/orphan_checker.py`, `tools/check_version_sync.py`, and
  `tools/repo_guard.py` all report clean.
- All systemd services active: `dslv-zpdi-tuning`, `dslv-zpdi-preflight`,
  `dslv-zpdi`, `dslv-zpdi-ups`, `dslv-zpdi-webdash`, `chrony`, `gpsd`.
- Web dashboard `/api/status` returns live system, pipeline, SDR (`clock_src:
  external`), UPS, and node-registry data.
- Boot orchestrator `--no-start` confirms the required service chain is active.

### Caveats
- The Rich TUI dashboard is configured to autostart via the orchestrator but has
  not been visually verified on the touchscreen in this session.
- Baseline remains in `LEARNING` state; PRIMARY HDF5 output is gated until SPEC-009
  baseline locks and a 4-node confirmed event occurs.

---

## [Unreleased] — Tier-1 Pi 5 node commissioning (2026-07-09)

### Added
- **Geekworm X-1202 UPS integration** (SPEC-004A.8):
  - `tools/x1202_ups_monitor.py` daemon polls fuel gauge and triggers graceful
    shutdown on low battery or extended AC loss.
  - `config/dslv-zpdi-ups.service` runs the monitor under systemd.
  - `docs/hardware/GEEKWORM_X1202_UPS.md` operator reference.
  - UPS telemetry now appears in the Flask web dashboard (`/api/status` + HTML
    power card).
- **Production HMAC key wiring**: `main_pipeline.py` supplies an explicit
  `KeyProvider` to `HDF5Writer`; profile now requires the production key. Key
  stored at `/etc/dslv-zpdi/hmac.key` with mode `0600`.
- **Baseline learning start**: `main_pipeline.py` now calls
  `coherence_engine.start_baseline()` so SPEC-009 learning actually begins.
- **Environment-driven baseline config**: `src/dslv_zpdi/layer2_core/wiring.py`
  reads `DSLV_BASELINE_HOURS`, `DSLV_MIN_BASELINE_SAMPLES`, and
  `DSLV_BASELINE_STATE_PATH` instead of hard-coded defaults.

### Fixed
- `PpsListener` now reads `/sys/class/pps/pps0/assert` and computes jitter from
  kernel timestamps. The `PPS_FETCH` ioctl failed on the Pi 5 kernel with
  "Inappropriate ioctl for device".
- `NmeaStream` now supports `gpsd://host:port` URLs, allowing `gpsd` to own the
  LBE-1421 USB-C serial port while the pipeline still receives GGA sentences.
- `dslv-zpdi.service` uses `RuntimeDirectory=dslv-zpdi` so
  `/run/dslv-zpdi/health.json` is written at the expected path.
- TUI dashboard autostart desktop entry points to the lightweight
  `tools/dashboard/launch.sh --compact` for the 1024×600 touchscreen.

### Verified
- All 184 tests pass (1 skipped, 2 SWIG deprecation warnings).
- `tools/orphan_checker.py`, `tools/check_version_sync.py`, and
  `tools/repo_guard.py` all report clean.
- `tools/provision_tier1.py` reports Tier-1 compliance.
- Pipeline service active; health endpoint shows `timing_healthy: true`,
  `chrony_stratum: 1`, `baseline_state: LEARNING`.
- Synthetic primary-write test confirms HDF5 file creation, SHA-256 event-chain
  hashing, and HMAC-SHA256 manifest attestation with the production key.

---

## [Unreleased] — Dashboard node-registry wiring and reboot prep (2026-06-19)

### Fixed
- `tier1_ingestion_server.py`: `_register_node_seen()` now called on every
  ACCEPTED packet, writing `output/secondary/node_registry.jsonl` (throttled to
  once per 30 s per node). This populates `telemetry_nodes` in the Flask
  dashboard, which previously always returned an empty array.

### Verified
- All 184 tests pass (1 skipped) after the dashboard fix.
- Repo fully clean: 0 open branches beyond `main`, 0 open issues, 0 open PRs.
- Termux:Boot script (`~/.termux/boot/99-start-zpdi.sh`) confirmed to launch
  `supervisor.sh`, which starts all three services (tier1 :8443, daemon,
  dashboard :8080) automatically on device boot.

---

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
- Optional dependency groups `[pluto]`, `[PlutoSDRplus]`, `[hardware]` in `pyproject.toml`.

### Changed
- Tier-1 canonical RF instrument is now a capability-qualified PlutoSDR+ class device; PlutoSDRplus is the legacy minimum reference floor.
- Timing claims are no longer collapsed into a single `phase_lock_verified` Boolean; each evidence dimension is represented separately.
- `pyPlutoSDRplus` moved from mandatory to optional `[PlutoSDRplus]` dependency group.

### Security
- Production HMAC key absence now blocks primary output when `allow_development_key=False`.
- Event hash chain detects deleted, reordered, altered, or injected events.

### Documentation
- Baseline audit in `docs/audits/PLUTOSDR_PIVOT_BASELINE_AUDIT.md`.
- Implementation plan in `docs/superpowers/plans/2026-06-15-plutosdr-tier1-pivot.md`.

## [4.8.1] — Grok autonomous Pixel simulator session (2026-06-11)

### Fixed
- **Task A (critical)**: `hal_hardware.py` SoapySDR and pyPlutoSDRplus top-level guards changed from bare `except ImportError:` to `except (ImportError, OSError):`. The `PlutoSDRplus` package (and Soapy) execute `CDLL('libPlutoSDRplus.so.0')` (and equiv) at *import time*, raising `OSError` (not `ImportError`) when the native shared object is absent (this proot Pixel / GrapheneOS simulator-only host has no libPlutoSDRplus). This previously caused 0 tests collected (test_hardware_failure_paths + test_timing_monitor via lock_monitor). Now 113 tests collected + passing on no-hw host. Added Rev 5.0.x explanatory comments referencing governing `SPEC-005A.HAL-HW`.
- Audit of sibling native guards: broadened h5py guards in `hdf5_writer.py` (SPEC-007) and `radon_session_writer.py` (SPEC-018); broadened bleak/dbus guards (existing + bare `from bleak` sites) in `radoneye_ingestor.py` (SPEC-015). Pure-Python guards (flask in node_receiver.py, pyserial inside funcs in hal_hardware.py:827 and nmea_stream.py:92) left as `ImportError`-only — they never load .so at import time; their OSErrors are runtime port/serial conditions already handled separately. Justified in work report.
- **Task B**: stray hardcoded "Rev 5.0.1" in `tests/test_pipeline.py:145` replaced by `from dslv_zpdi import __version__` (now prints Rev 5.0.1 and can never desync). `check_version_sync.py` remains clean. Cosmetic banner appends in hal_*.py docstrings (no orphan noise).
- **Task C** (per NEXT_STEPS P2): added 10 new contract tests in `tests/test_node_receiver.py` (SPEC-014.8) covering `/api/v1/ingest`, `/api/v1/ingest/radoneye`, `/api/v1/health` for malformed JSON, missing required, writer-failure (500), and concurrent POSTs. Uses Flask test client + injected writers for isolation. Node receiver coverage lifted from 0%. Extended `specs/SPEC-014.md` with test section. No new public contracts; RadonEye remains secondary-only. No Tier-1 promotion, no metrology changes.
- All per `AGENTS.md` / `CONTRIBUTING.md` / orphan_checker / repo_guard. Full §2 contract green before/after each commit. 113 passed / ruff clean / version-sync clean / coverage ~53%+ (node_receiver now exercised).

### Changed
- Version bump 4.8.0 → 4.8.1 (behavior change for simulator hosts + new test surface coverage). All authorities synchronized: pyproject.toml, __init__.py, README revision line, CHANGELOG.md, new RELEASE_NOTES_v5.0.0.md.

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
  while the `v5.0.0` tag and CHANGELOG already named 4.8.0. Reconciled all version
  authorities to 4.8.0 and added `RELEASE_NOTES_v5.0.0.md`. `check_version_sync`
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
- **LBE-1421→LBE-1421 typos** in `V3_DSLV-ZPDI_LIVING_MASTER.md` — two instances where dual-output GPSDO was misidentified as single-output.
- **Dual-output architecture clarity** in `PHASE_2A_TIER_1_BUILD_SHEET.md` — new section documenting LBE-1421 Out1 (1 PPS → GPIO 8) and Out2 (10 MHz → PlutoSDRplus CLKIN) independence.

### Changed
- `tools/dashboard/app.py` — imports + instantiates 3 new panels; layout builder and render loop updated. Toggle keys `4` (RADON), `5` (MOBILE), `6` (BCI) added.
- `tools/dashboard/config.py` — `PanelsCfg` extended with `radon`, `mobile`, `bci` booleans.
- `tools/dashboard/humor.py` — 11 radon-themed snark lines added to pool.
- `pyproject.toml` / `requirements.txt` — `bleak>=0.21.0` added.

### Tests
- 56 new tests added across 6 modules (SPEC-015 through SPEC-020). All green.
- Total suite: 94 passing (excluding 2 pre-existing flaky hardware tests tied to real PlutoSDRplus state).
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
- **pyPlutoSDRplus LNA/VGA Gain Log Spam** — removed redundant print statements in `pyPlutoSDRplus` site-package that caused severe stdout spam during rapid SDR capture cycles.
- **ComplexWarning in hal_hardware.py** — corrected the pyPlutoSDRplus ingestion flow which was redundantly converting complex data from `read_samples` into interleaved structures, discarding the imaginary parts and raising a `ComplexWarning`.
- **NMEA Stream Serial Exception** — implemented exception handling for the `pyserial` bug where the device reports readiness to read but returns no data, avoiding pipeline restarts and silent drops on `/dev/ttyACM0`.
- **Chronyc Jitter Monitor Stability** — resolved large PPS jitter reporting by forcing chronyc to step the system clock (`chronyc makestep`), aligning the system time with the GPSDO time.
- **Validation Compliance Repair** — restored clean version-sync and orphan-checker results by adding v5.0.0 release notes, synchronizing the README revision, and adding missing SPEC-ID coverage in new ingestion and node receiver paths.

### Added
- **Shared Collaboration Workspace** — added `docs/collaboration/` as the common operating layer for Gemini CLI, Claude Code, Kimi Code, and Codex CLI with setup, validation, turnover, asset, and next-step guidance.

## [4.7.0] - 2026-05-30 · Node Bridging, HDF5 Multi-Node Aggregation & Dashboard Finalisation

### Added
- **PiRepo hotspot configuration** (`config/PiRepo.nmconnection`) — NetworkManager keyfile
  to create a 2.4 GHz AP (SSID `PiRepo`) on `wlan0`. The Pi 5 holds static IP
  `10.42.0.1/24`. Pixel 9 Pro XL (GrapheneOS) and additional swarm nodes connect here.
- **PlutoSDRplus boot initialisation service** (`config/dslv-zpdi-PlutoSDRplus-init.service`) — runs
  `PlutoSDRplus_info` once after udev settles USB, waking the device out of cold-start before
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
- **HardwareHAL SoapySDR/pyPlutoSDRplus fallback** — when SoapySDR raises `DriverUnavailableError`
  and `PYPlutoSDRplus_AVAILABLE` is False (no fallback driver), the original exception is now
  re-raised instead of being silently swallowed. Previously the constructor succeeded with
  no SDR initialised, masking the configuration error. Fixes
  `test_no_devices_found_raises_driver_unavailable`.
- **Concurrent HDF5 writes** — `HDF5Writer._write_primary` now acquires a
  `threading.Lock` before touching the HDF5 file handle, preventing data corruption when
  the pipeline and the node-receiver HTTP server write to the same file concurrently.

### Changed
- **PlutoSDRplus / real-SDR ON by default** — dashboard now sets
  `DSLV_DASHBOARD_REAL_SDR=1` at startup. Use `--no-real-sdr` CLI flag to start in
  simulated mode. Waterfall panel and footer SDR indicator reflect live PlutoSDRplus data
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
  The recommended NMEA + `lock GPS` configuration from the v5.0.0 session report cannot
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
- **PlutoSDRplus device contention (pipeline vs. dashboard)** — `launch.sh` was exporting
  `DSLV_DASHBOARD_REAL_SDR=1`, causing `PlutoSDRplus_sweep` to start immediately and hold the
  PlutoSDRplus exclusively, forcing the pipeline into SimulatedHAL on every service restart.
  Removed the auto-export; waterfall defaults to SIM, users toggle real-SDR with `r`.
- **PlutoSDRplus probe retry** — `_verify_pyPlutoSDRplus_clock()` now retries 3× with 2 s delay
  before falling back to SimulatedHAL, surviving brief contention windows at startup.

### Security / Hardware
- **PlutoSDRplus amplifier hard lockout** — `WaterfallPanel.toggle_amp()` is now a permanent
  no-op; `_ingest_pyPlutoSDRplus()` explicitly calls `set_amp_enable(0)` before every SDR
  capture; dashboard `a` key shows a hardware-fault warning instead of toggling.
  PlutoSDRplus 1 front-end amp is blown — parts on order.

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
- Dashboard v2: 10" Lenovo HDMI touchscreen-optimized layout, NOAA space-weather panel, storm/anomaly/weather/waterfall panels, TOML config.
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
- README bumped to Rev 5.0.0 — LBE-1421 Hardened Operations Stack.

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
- udev rules (`99-pps.rules`, `52-PlutoSDRplus.rules`) and `systemctl enable chrony` in installer.
- CI matrix expansion for Python 3.10–3.13 and Pi 5 self-hosted hardware runners.
- RP1 3.3V hard enforcement guard in `provision_tier1.py` and build sheet.

### Changed
- `hal_hardware.py` — NMEA telemetry integrated into `ingest_gps_pps()`, IQ serialization aligned to 64-item preview.
- Schema bumped to 3.2 in `payload.py`, `tier1_policy.py`, and `hdf5_writer.py`.
- Version alignment to Rev 5.0.0 across README, installer, tests, and release notes.

## [4.3.1] - 2026-04-15

### Added
- Canonical exception hierarchy in `core/exceptions.py` (SPEC-005A).
- Tier 1 policy contract module (`contracts/tier1_policy.py`) centralizing clock, baseline, and routing constants (SPEC-009).
- Event deduplication/cooldown in `CoherenceScorer` to prevent duplicate global-event flooding.
- Real HDF5 rotation tests verifying file close/open/reset behavior.
- Hardware failure-path mock tests covering SoapySDR, pyPlutoSDRplus, serial/NMEA, and HDF5 unavailability.
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
- False-positive clock verification in pyPlutoSDRplus fallback path.
- Missing live-gate enforcement for packet checksum verification.

## [4.3.0] - 2026-04-15

### Added
- **Multi-OS Support:** Formal validation for Raspberry Pi OS Trixie (Debian 13).
- **SoapySDR Venv Linkage:** Automated symlinking of system `python3-soapysdr` to venv.
- **OS Detection:** Added Debian codename and version detection to installer.

### Changed
- **Installer:** Hardened `install_dslv_zpdi.sh` for multi-OS firmware path compliance.
- **Version Alignment:** Synchronized to Rev 5.0.0.

## [4.2.1] - 2026-04-15

### Fixed
- **Dependencies:** Corrected `pyPlutoSDRplus` version requirement from `>=1.0.0` (non-existent) to `>=0.2.0`.
- **Installer:** Resolved installation failure in `install_dslv_zpdi.sh` due to invalid `pyPlutoSDRplus` version.

## [4.2.0] - 2026-04-11

### Added
- **LBE-1421 GPSDO Migration:** Migrated Clock Authority from Leo Bodnar Mini GPSDO to Leo Bodnar LBE-1421 GPSDO (USB-C, NMEA telemetry, 3.3V CMOS native output).
- **NMEA Telemetry:** Added `verify_nmea_telemetry()` to HardwareHAL and NMEA check to provisioning tool for GPS fix verification via virtual serial port.
- **RF/Magnetic Shielding Docs:** Created `docs/RF_MAGNETIC_SHIELDING.md` — cyberdeck chassis design with conduction cooling, compartmentalization, galvanic isolation, and pass-through security.
- **Hardware Change Justification:** Created `docs/HARDWARE_CHANGE_JUSTIFICATION.md` (SPEC-UPDATE-PHASE-2A-LBE-1421).
- **Updated BOM:** Added ANT500 antenna, SMA cabling, and jumper wire specifications to Tier 1 mandatory BOM.

### Changed
- **Dependencies:** Replaced `pyrtlsdr` with `pyPlutoSDRplus` in core dependencies. RTL-SDR is Tier 2 only.
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
- **Test Alignment:** Synchronized `test_pipeline.py` and auxiliary scripts with Rev 5.0.2.4/3.5 implementation.

### Fixed
- Resolved API mismatches in `HDF5Writer` constructor and method names.
- Corrected filename and group-naming typos in integration tests.
- Fixed CI environment failures by ensuring dependency installation.

## [3.4.0] - 2026-04-08
- Phase 1 Software Sandbox officially sealed.
- HDF5Writer with cryptographic attestation deployed.
- Dual-Stream Protocol (quarantine vs kill) enforced.
# DSLV-ZPDI Release Notes: v5.0.0
**Date:** 2026-04-09  
**Revision:** Rev 5.0.2 (Airtight Baseline)

## 🚀 Overview
Version 4.0.2 introduces a robust, unified installer script (`install_dslv_zpdi.sh`) that automates the deployment, dependency management, and hardware audit protocols for Tier 1 Anchor Nodes. This release also synchronizes the entire repository with the Rev 5.0.2 baseline, ensuring 100% compliance with SPEC-004A.1 timing mandates.

## 🛠️ Key Changes
1. **Unified Installer Deployed:**
   - Automates `apt` dependency installation for PTP/timing.
   - Handles `python` venv creation and package management.
   - Implements hardware-safe detection (CM4, CM5, Pi 4, Pi 5).
   - Includes `--simulator` mode for non-hardware validation.
2. **Version Alignment:**
   - Bumped version to 4.0.2 across `pyproject.toml`, `README.md`, `CHANGELOG.md`, and all `tools/`.
   - Updated `V3_DSLV-ZPDI_LIVING_MASTER.md` with Session 19 turnover notes.
3. **Hardware Auditing:**
   - Installer now validates `igb` driver, `udev` rules, and PTP jitter (<50ns) via integrated Tier 1 audit.
4. **Git Protocol Hardening:**
   - Automated `git safe.directory` configuration for root-level execution.

## 🧪 Verification & QA
- **Regression Suite:** All 16+ integration and unit tests passed with 100% success rate.
- **Orphan Checker:** 100% SPEC-ID compliance verified (no orphaned claims).
- **Installer Logic:** Verified in simulated environment with `--simulator` and `--skip-apt` flags.

## 📦 Installation
```bash
sudo ./install_dslv_zpdi.sh --tier1
```

---
**Status:** Software is 100% PRODUCTION READY.
**Next Steps:** Proceed to physical timing surgery and node commissioning.
# DSLV-ZPDI Release Notes — v5.0.0

**Revision:** Rev 5.0.0 (LBE-1421 Hardware Pivot)
**Date:** 2026-04-11
**Codename:** LBE-1421

## Summary

Version 4.2.0 implements the mandatory hardware migration from the Leo Bodnar Mini GPSDO to the **Leo Bodnar LBE-1421 GPSDO** across the entire project. This update eliminates the fragile Mini-USB connection, adds software-observable NMEA telemetry, and leverages the LBE-1421's native 3.3V CMOS output for direct Pi 5 GPIO compatibility without level-shifting.

Additionally, this release introduces the RF & Magnetic Shielding design documentation for the cyberdeck chassis build.

## Breaking Changes

- **GPSDO Model:** Leo Bodnar Mini GPSDO is formally **deprecated**. All Tier 1 deployments must use the LBE-1421.
- **Dependencies:** `pyrtlsdr` removed from core dependencies (Tier 2 only). Replaced with `pyPlutoSDRplus` as core SDR dependency.
- **BOM Updated:** ANT500 antenna, SMA cabling, and jumper wires added to mandatory Tier 1 BOM.

## Changes

### Hardware
- Migrated Clock Authority from Leo Bodnar Mini GPSDO to **LBE-1421 GPSDO** (USB-C, NMEA, 3.3V CMOS)
- Added Great Scott Gadgets **ANT500** antenna (75 MHz - 1 GHz) to Tier 1 BOM
- Added SMA Male-to-Male coaxial cable (50 Ohm, ≤ 1FT) specification
- Added premium F-to-F jumper wire (2.54mm pitch) specification for PPS interconnect
- Updated physical routing protocol with LBE-1421-specific wiring instructions
- Removed level-shifter requirement for PPS line (LBE-1421 outputs 3.3V natively)

### Software
- Added `verify_nmea_telemetry()` method to `HardwareHAL` for LBE-1421 NMEA stream verification
- Added NMEA check to `provision_tier1.py` validation suite
- Updated `hal_hardware.py` source strings from `gpsdo_leo_bodnar_mini` to `gpsdo_leo_bodnar_lbe1420`
- Removed `pyrtlsdr` from core dependencies (moved to optional/Tier 2)
- Added `pyPlutoSDRplus>=1.0.0` to core dependencies
- Added Python 3.12/3.13 classifiers to pyproject.toml
- Updated installer script to Rev 5.0.0, removed `rtl-sdr`/`librtlsdr0` from base packages

### Documentation
- Created `docs/HARDWARE_CHANGE_JUSTIFICATION.md` (SPEC-UPDATE-PHASE-2A-LBE-1421)
- Created `docs/RF_MAGNETIC_SHIELDING.md` — cyberdeck chassis shielding design
- Updated all hardware references across 20+ files from Mini GPSDO to LBE-1421
- Synchronized version strings to 4.2.0 across pyproject.toml, README, installer, tests, specs, and tools
- Updated RP1 voltage warnings to reflect LBE-1421 native 3.3V compatibility

### Version Alignment
- `pyproject.toml`: 4.0.2.4 → 4.2.0
- `README.md`: Rev 5.0-PIVOT → Rev 5.0.0
- `install_dslv_zpdi.sh`: Rev 5.0.2.4 → Rev 5.0.0
- `CONTRIBUTING.md`: Rev 5.0.2 → Rev 5.0.0
- `MASTER_SPEC.md` / `V3_DSLV-ZPDI_LIVING_MASTER.md`: Rev 5.0.2 → Rev 5.0.0
- All HAL modules: Rev 5.0-FORGE/4.1-PIVOT → Rev 5.0-LBE-1421

## Validation

- 31/31 tests passing
- SPEC-ID orphan checker: clean
- Version sync: aligned
# DSLV-ZPDI Release Notes — v5.0.0

**Revision:** Rev 5.0.1 (Dependency Hotfix)
**Date:** 2026-04-15
**Codename:** LBE-1421-HOTFIX

## Summary

Version 4.2.1 is a maintenance release that corrects an invalid dependency requirement in the core software stack. Version 4.2.0 incorrectly specified `pyPlutoSDRplus>=1.0.0`, which is not currently available on PyPI (latest stable is 0.2.0). This prevented clean installation via `pip` and the automated installer.

## Changes

### Software
- Updated `pyproject.toml` and `requirements.txt` to require `pyPlutoSDRplus>=0.2.0`.
- Verified 100% test pass rate with the corrected dependency.

### Installation
- Updated `install_dslv_zpdi.sh` to Rev 5.0.1.
- Validated installer in `--simulator` mode.

## Version Alignment
- `pyproject.toml`: 4.2.0 → 4.2.1
- `README.md`: Rev 5.0.0 → Rev 5.0.1
- `install_dslv_zpdi.sh`: Rev 5.0.0 → Rev 5.0.1
- `MASTER_SPEC.md` / `V3_DSLV-ZPDI_LIVING_MASTER.md`: Rev 5.0.0 → Rev 5.0.1

## Validation
- 31/31 tests passing
- SPEC-ID orphan checker: clean
- Version sync: aligned
# DSLV-ZPDI Release Notes — v5.0.0

**Revision:** Rev 5.0.0 (Multi-OS Compliance & Installer Hardening)
**Date:** 2026-04-15
**Codename:** MULTI-OS-PIVOT

## Summary

Version 4.3.0 introduces a hardened, multi-OS compatible deployment architecture. It formally validates and supports **Raspberry Pi OS Trixie (Debian 13)** alongside **Bookworm (Debian 12)**. This release also addresses the "SoapySDR Venv Isolation" problem by introducing an automated linkage layer for hardware-agnostic SDR drivers.

## Changes

### Installation & Deployment
- **OS Detection:** `install_dslv_zpdi.sh` now detects Debian version and codename to ensure path compliance (e.g., firmware config location).
- **SoapySDR Linkage:** Automatically symlinks system `python3-soapysdr` into the project's virtual environment. This enables the high-performance C++ bindings to be used within the isolated Python environment without requiring complex source builds.
- **Improved venv creation:** Hardened venv setup for Python 3.12/3.13 compatibility.

### Compatibility
- **Trixie (Debian 13) Support:** Validated on Python 3.13.5. All core algorithms (Kuramoto coherence, HDF5 persistence) are verified stable.
- **Bookworm (Debian 12) Support:** Retained 100% compatibility for existing Phase 2A deployments.

## Version Alignment
- `pyproject.toml`: 4.2.1 → 4.3.0
- `README.md`: Rev 5.0.1 → Rev 5.0.0
- `install_dslv_zpdi.sh`: Rev 5.0.1 → Rev 5.0.0
- `MASTER_SPEC.md` / `V3_DSLV-ZPDI_LIVING_MASTER.md`: Rev 5.0.1 → Rev 5.0.0

## Validation
- 31/31 tests passing on Trixie (Python 3.13)
- SPEC-ID orphan checker: clean
- Version sync: aligned
- SoapySDR venv linkage: VERIFIED
# Release Notes v5.0.0

**Date:** 2026-04-15

## Summary
Production pipeline loop, live HardwareHAL wiring, canonical HAL factory, field baseline capture script, installer hardening, and modality expansion hooks.

## Added
- `src/dslv_zpdi/main_pipeline.py` — SPEC-011 production pipeline loop with `--field` baseline mode.
- `tools/capture_baseline.py` — 72 h passive baseline capture script (SPEC-009.1).
- `src/dslv_zpdi/layer1_ingestion/hal_factory.py` — canonical SPEC-005A.4 factory with typed `get_hal()`.
- Hilbert phase extraction in `HardwareHAL` and `SimulatedHAL` (Layer 1 per SPEC-005).
- Thermal/acoustic ingest hooks in `HardwareHAL` (Layer 1 modality expansion).
- udev rules deployment (`99-pps.rules`, `52-PlutoSDRplus.rules`) and `systemctl enable chrony` in installer.
- CI matrix expansion for Python 3.10–3.13 and Pi 5 self-hosted hardware runners.
- RP1 3.3V hard enforcement guard in `provision_tier1.py` and build sheet.

## Changed
- `hal_hardware.py` — integrated NMEA telemetry into `ingest_gps_pps()`, 64-item IQ preview, Hilbert phase extraction.
- `payload.py`, `tier1_policy.py`, `hdf5_writer.py` — schema bumped to 3.2.
- Version alignment to Rev 5.0.0 across all canonical sources.
# Release Notes v5.0.0

**Date:** 2026-04-24

## Summary
LBE-1421 hardened operations stack with fully instrumented dashboard, automated email telemetry pipeline, interactive geospatial mapping, hardened project launcher, and field baseline coherence integration.

## Added
- **Dashboard v2** (`tools/dashboard/`)
  - 10" Lenovo HDMI touchscreen-optimized layout with compact/full banner modes and startup animation.
  - NOAA Space Weather integration (`noaa.py`) for real-time Kp, solar wind, and aurora alerts.
  - New panels: RF Anomaly, Storm Watch, Weather Overlay, Waterfall spectrogram, enhanced Hardware/Logs/Notifications/Pipeline/System views.
  - `config.py` with TOML-based runtime configuration (`config/dashboard.toml.example`).
- **Auto-Email Pipeline** (`tools/mailer/`)
  - Modular backends (`backends.py`) supporting SMTP, SendGrid, and AWS SES.
  - `send_data.py` — daily/alert-triggered telemetry dispatch with HDF5 attachment support.
  - `configure.py` — interactive TUI for credential and recipient management.
  - `send_now.sh` — one-shot manual send wrapper.
  - Example config: `config/email.example.yaml`.
- **Interactive Mapping** (`tools/mapping/`)
  - `render_map.py` — Folium-based HTML map generation with anomaly clustering and GPS track overlay.
  - `aggregate.py` — HDF5 telemetry aggregator for multi-node map layers.
  - `open_map.sh` / `open_hdf5_browser.sh` — quick-launch helpers.
- **Project Launcher** (`tools/launch_project.sh`)
  - Clean-boot sequence with preflight checks, dual-window terminal spawn (dashboard + logs), and autostart integration.
  - `tools/toggle_simulator.sh` — runtime simulator/hardware mode switch with systemd service restart.
- **Test Infrastructure**
  - `tests/conftest.py` — shared pytest fixtures and monkey-patched HAL helpers.
- **Configuration Examples**
  - `config/dashboard.toml.example`
  - `config/email.example.yaml`
  - `config/sensor_location.example.yaml`

## Changed
- `main_pipeline.py` — integrated simulator resolution via `_resolve_simulator()` with env/CLI priority; graceful signal handling (`SIGINT`/`SIGTERM`); `DSLV_SIM_DEMO` mode for 4-node rotation gate testing.
- `wiring.py` — baseline state path resolution with env override (`DSLV_BASELINE_STATE_PATH`).
- `hal_simulated.py` — simulator fidelity improvements aligned to SPEC-005A.HAL-SIM.
- `.gitignore` — expanded to cover agent workspaces (`GEMINI-HOME/`, `CLAUDE-HOME/`), local runtime configs, and artefact directories.
- `README.md` — bumped to Rev 5.0.0 with LBE-1421 hardened operations stack documentation.

## Fixed
- Launcher race conditions on clean-boot dual-window startup (lxterminal UTF-8 codec guard, service dependency ordering).
- Pipeline baseline state not loaded into coherence engine on cold start.

## Version Alignment
- Project version bumped to **4.5.0** across `pyproject.toml`, `README.md`, `CHANGELOG.md`, `install_dslv_zpdi.sh`, and `tests/test_pipeline.py`.
# Release Notes v5.0.0

## DSLV-ZPDI v5.0.0 — LBE-1421 Hardened Operations Stack

### Summary
Production-hardened release integrating Leo Bodnar LBE-1421 GPSDO timing
discipline, installer robustness fixes, and Tier-1 baseline validation.

### Changes
- Installer idempotency and bootstrap reliability improvements
- Dynamic path resolution in shell scripts (preflight, launch, dashboard)
- SoapySDR linkage fix for virtual environment provisioning
- Version synchronization across all authority files

### Verification
- pytest: 49 passed
- orphan_checker: clean
- repo_guard: passed
- version_sync: clean
# Release Notes v5.0.0

## DSLV-ZPDI v5.0.0 — Dependency and Validation Alignment

### Summary
Maintenance release aligning the package version with the current runtime
dependency set and validation contract after the v5.0.0 node bridge,
multi-node HDF5 aggregation, and dashboard finalisation work.

### Changes
- Added Flask and psutil to the canonical Python dependency authority for the
  node receiver and web dashboard runtime paths.
- Kept project validation anchored on editable installs, pytest, orphan
  checking, version sync, and repo guard checks.
- Preserved v5.0.0 operational scope while making dependency installation
  reproducible on new development machines.
- Added shared collaboration documentation and turnover process for Gemini CLI,
  Claude Code, Kimi Code, and Codex CLI.

### Verification
- pip check: clean
- version_sync: clean
- orphan_checker: clean
- repo_guard: passed
- pytest: 47 passed
- simulator smoke path: 10/10 passed
# Release Notes — v5.0.0

**Date:** 2026-06-01
**Theme:** Robustness, Reliability & Security Hardening
**Baseline:** Rev 5.0.1 → Rev 5.0.2

This is a quality-and-hardening release. The trust pipeline's behaviour is
unchanged; the work makes shutdown safe for the data on disk, shrinks the swarm
receiver's attack surface, and raises overall code health. The objective for the
pass was system stability and trustworthy data output.

## Highlights

### Reliability / data integrity
- **Graceful shutdown.** `main_pipeline.py` previously terminated via
  `os._exit(0)` inside the signal handler, which could leave the open HDF5 file
  truncated. Shutdown is now cooperative: SIGINT/SIGTERM stop the worker threads,
  join them, then flush and close the HDF5 writer, timing monitor, and health
  reporter. `SIGTERM` (systemd's stop signal) is now handled as well as `SIGINT`.
- **Latent import crash fixed.** The deprecated `cm5_ingestion` shim imported
  `BaseHAL` from `hal_factory`, which never exported it — importing the module
  raised `ImportError`. `hal_factory` now re-exports the canonical HAL surface and
  every package submodule imports cleanly.

### Security
- **Request-size cap** on the Flask node receiver (`MAX_CONTENT_LENGTH = 1 MiB`)
  rejects oversized bodies before they are buffered into memory.
- **Atomic, locked node registry** writes remove a read-modify-write corruption
  race under concurrent POSTs.
- **RadonEye numeric validation** returns a clean `422` for a non-numeric
  `radon_bq_m3` reading instead of a later `500`.
- **Loud insecure-key warning** when `HDF5Writer` falls back to the development
  HMAC key, so weakened attestation cannot silently ship to the field.

### Code health
- Ruff is clean across `src/`, `tools/`, and `tests/` (~240 findings resolved).
- Pylint rating improved from **9.31 → 9.64 / 10**.
- Type hints modernized to PEP 585/604 behind `from __future__ import annotations`
  (3.9-safe).
- `dslv_zpdi.__version__` is now defined and enforced against `pyproject.toml` by
  `tools/check_version_sync.py`.

## Verification

Run from the editable `.venv`:

- `pip check`: clean
- `tools/check_version_sync.py`: clean at 4.7.2
- `tools/orphan_checker.py`: clean
- `tools/repo_guard.py`: passed
- `ruff check src/ tools/ tests/`: all checks passed
- `pylint src/dslv_zpdi/`: 9.64/10
- `DEV_SIMULATOR=1 pytest tests/ -v`: 47 passed
- `DEV_SIMULATOR=1 tests/test_pipeline.py`: 10/10 passed

## Upgrade notes

No configuration or schema changes. Operators running the node receiver behind a
reverse proxy may align the proxy body-size limit with the new 1 MiB cap.
# Release Notes — v5.0.0

**Date:** 2026-06-05 (release notes reconciled 2026-06-10)
**Phase:** 2B — Radon Validation Metrology Stack (Tier 2)
**Tag:** `v5.0.0`

## Summary

Phase 2B adds a Tier 2 radon-validation metrology stack alongside the existing
Tier 1 RF/GPSDO anchor. The new stack is additive and trust-subordinate: nothing
in this release alters the Tier 1 primary stream, the Kuramoto coherence core, or
the existing HDF5 event schema. All new sensor paths ship with a simulator so the
full suite validates with `DEV_SIMULATOR=1` and no physical hardware.

## Added

- **RadonEye Pro RD200P ingestor** (SPEC-015) — BLE GATT primary transport with
  HTTP fallback and a CI simulator. Reads radon concentration with BLE → HTTP →
  SIM graceful degradation. Remains **secondary-only** pending SPEC-015 promotion
  criteria.
- **Pixel 9 Pro XL mobile node bridge** (SPEC-016) — HTTP polling bridge with
  trust scoring (0.0–1.0); surfaces magnetometer, GPS fix, and camera perceptual
  hash. Sub-threshold scores are flagged for review.
- **Pi–Pixel uplink manager** (SPEC-017) — classifies hotspot connectivity as
  online / offline / degraded and triggers backfill replay on restore. Never
  blocks the Tier 1 primary stream.
- **HDF5 schema extension** (SPEC-018) — five new top-level branches
  (`certified_crm`, `macro_atmosphere`, `space_weather`, `mobile_node_tier2`,
  `validation_index`) with a signed manifest (per-branch SHA-256 + HMAC
  attestation). Existing event groups are unchanged.
- **Barometric coherence engine** (SPEC-019) — χ(τ) cross-correlation between
  radon and barometric pressure with optional RH weighting. The review flag is
  explicitly subordinate to certified CRM data and never overrides it.
- **48-hour session orchestrator** (SPEC-020) — full campaign lifecycle
  (init → run → finalize → summary) with resume-from-cache and a compound `.h5`
  audit file plus a human-readable summary.
- **Dashboard panel suite** (SPEC-021) — RADON, MOBILE/T2, and BCI panels added
  to the existing compact/wide layout with zero regression to current panels.
- **`SensorModality.RADON`** added to the ingestion enum contract.
- **`bleak>=0.21.0`** dependency for BLE GATT transport.

## Fixed

- Closed 27 pre-existing SPEC-ID orphan gaps (`node_receiver`, `pps_listener`,
  `nmea_stream`, `hal_hardware`) and added real `specs/SPEC-014.md`.
- Corrected LBE-1421 → LBE-1421 dual-output references in the living master and
  build sheet.

## Validation

- Full simulator suite green (`DEV_SIMULATOR=1`).
- `orphan_checker`, `repo_guard`, and `pip check` clean.

## Notes

Hardware-only paths (BLE radon transport, PPS/NMEA, PlutoSDRplus) are validated in
simulator mode here and must still be confirmed on the Tier 1 Pi 5 per
`docs/collaboration/NEXT_STEPS.md`.
# Release Notes — v5.0.0

**Date:** 2026-06-11
**Phase:** 2B — Simulator hardening + Node Receiver contract tests (Pixel proot host)
**Tag:** `v5.0.0`
**Authority:** Joseph R. Fross (DynoGator Labs) — autonomous Grok execution on Pixel 9 Pro XL / GrapheneOS / Debian Trixie proot (aarch64, no PlutoSDRplus attached)

## Summary

This patch release is the direct result of the autonomous work order executed on a **simulator-only** dev host (no libPlutoSDRplus.so.0, no PPS/GPSDO hardware). The primary defect was that bare `except ImportError:` guards around native SDR libs allowed `OSError` (from `ctypes.CDLL` at import time inside third-party packages) to escape, making test collection impossible (0 tests collected) on any host without the native shared objects.

The fix broadens the guards for native-loading imports only. Pure-Python imports remain `ImportError`-only. All changes are SPEC-tied, orphan-clean, and preserve the existing fallback-to-simulator semantics.

113 tests now pass under `DEV_SIMULATOR=1` (was 103 on hw hosts; the two previously uncollectable modules now run). `test_pipeline.py` now dynamically reads the package version.

## Fixed

- **OSError vs ImportError guard defect (Task A, SPEC-005A.HAL-HW)**: 
  - `src/dslv_zpdi/layer1_ingestion/hal_hardware.py` (SoapySDR ~line 42, pyPlutoSDRplus ~line 74): `except ImportError:` → `except (ImportError, OSError):`. Added Rev 5.0.x comments with exact root-cause narrative and SPEC reference.
  - Audit + same treatment for h5py (hdf5_writer.py, radon_session_writer.py) and bleak (radoneye_ingestor.py, including previously unguarded `from bleak import BleakClient` call sites).
  - Pure-Python left unchanged: flask (node_receiver), pyserial (inner imports in hal_hardware + nmea_stream). Justification: these never perform CDLL / .so load at import time; OSError paths for them are runtime (port open, serial errors) and already caught separately.
  - Result: on this host, full suite collects and 113 pass; `test_pipeline.py` prints all 10 PASS.

- **Stray version string (Task B)**: `tests/test_pipeline.py` no longer hard-codes "4.7.1"; imports `__version__` so it stays in lockstep forever. `tools/check_version_sync.py` green.

- Cosmetic banner rev notes appended (not rewritten) to hal_hardware.py / hal_simulated.py.

## Added

- **Node receiver contract tests (Task C, P2 per NEXT_STEPS.md, SPEC-014.8)**: new `tests/test_node_receiver.py` (10 tests) exercising the public HTTP surface:
  - `/api/v1/ingest`: happy path, malformed JSON (400), empty body (400), missing node_id stamping.
  - `/api/v1/ingest/radoneye`: missing required fields (422), non-numeric radon (422), valid staging to secondary JSONL (202 + SPEC-015-PENDING note).
  - `/api/v1/health`: 200 + stats.
  - Writer-failure injection: raises → 500 (storage kill condition exercised).
  - Concurrent POSTs (8 workers): all succeed, registry lock + no crashes.
- All test functions/classes carry SPEC-014.8 (or cross-ref 014.4/5/6) docstrings.
- `specs/SPEC-014.md` extended with `## Test Coverage` section for SPEC-014.8.
- Coverage on `layer3_telemetry/node_receiver.py` lifted from 0 % (now meaningfully exercised). `pixel_node_bridge.py` coverage remains high.

## Compliance & Validation

- Full canonical contract (§2 of work order) executed at baseline (Task A collection failure reproduced), after Task A, after B/C, and before every commit.
- 113 passed / ruff clean / pip check / version-sync clean / orphan_checker clean / repo_guard clean.
- No new SPEC-IDs minted without `specs/SPEC-*.md` backing.
- No metrology changes, no Tier-1 promotion of Tier-2/RadonEye data, no amplifier lockout relaxation.
- Git: atomic commits (Task A with 4.8.1 bump, Task B, Task C), ff-only, post-push re-verification of full contract on clean fetch.

## Deliverables (committed + pushed)

- `docs/audits/GROK_WORK_REPORT_2026-06-11.md`
- `TURNOVER_2026-06-11_Grok_NodeBridgeHardening.md` (at root)
- `CHANGELOG.md` (prepended 4.8.1 section)
- `RELEASE_NOTES_v5.0.0.md` (this file)
- `docs/collaboration/NEXT_STEPS.md` updated (P2 items marked done, new "Done in this session" block, points to P1 hardware-truth on Pi 5 next)

## Residual Risks / Deferred

- This host remains simulator-only; no hardware-truth evidence written to `docs/validation-logs/`.
- RadonEye endpoint stays explicitly secondary/quarantine-only (SPEC-015 stub exists but calibration baseline ratification is future hardware session work).
- Next priority (per TURNOVER): P1 "Hardware Truth Path" on the Pi 5 (PlutoSDRplus + LBE-1421 + PPS validation).

The pushed tree is clean, remote-synced, and the full §2 contract is green on the post-push checkout.

**End of 4.8.1 release notes.** Safe for field simulator use; hardware sessions remain the source of truth for metrology claims.# DSLV-ZPDI Release Notes — Rev 5.0.0

**Release Date:** 2026-06-15  
**Milestone:** Tier-1 RF metrology hardware pivot to PlutoSDR+ class devices  
**Status:** Beta — software architecture complete, hardware qualification pending physical verification gates

## Summary

Rev 5.0.0 replaces the PlutoSDRplus as the canonical Tier-1 RF metrology target
with a capability-based qualification model centered on the HamGeek AD9363
PlutoSDR+ class device and the Leo Bodnar LBE-1421 GPSDO. The PlutoSDRplus
remains supported as an optional legacy backend and historical performance
floor.

This is a major architectural refactor:

- Timing authority, SDR backend, frequency translation, and qualification
  policy are now decoupled and composable.
- Timing evidence is represented explicitly and granularly; no more misleading
  `phase_lock_verified` Boolean.
- HDF5 finalization is atomic and includes an event hash chain.
- Production HMAC key handling is hardened and fails closed.

## New Components

| Component | Path | SPEC |
|-----------|------|------|
| Composed HAL | `src/dslv_zpdi/layer1_ingestion/hardware_hal.py` | SPEC-005A.HAL |
| Timing subpackage | `src/dslv_zpdi/layer1_ingestion/timing/` | SPEC-005A.TIMING |
| SDR backend subpackage | `src/dslv_zpdi/layer1_ingestion/sdr/` | SPEC-004A |
| Pluto IIO backend | `src/dslv_zpdi/layer1_ingestion/sdr/pluto_iio.py` | SPEC-004A.PLUTO |
| Qualification engine | `src/dslv_zpdi/layer1_ingestion/sdr/qualification.py` | SPEC-004A.QUAL |
| Frequency translation | `src/dslv_zpdi/layer1_ingestion/frequency_translation/` | SPEC-004A.FREQ |
| Key provider | `src/dslv_zpdi/core/key_provider.py` | SPEC-018 |
| Config models | `src/dslv_zpdi/config_models.py` | SPEC-004A.CONFIG |
| CLI package | `src/dslv_zpdi/cli/` | SPEC-011.CLI |
| Node profiles | `config/node_profiles/` | SPEC-004A |

## Validation

- 143 tests pass in simulator mode.
- Orphan checker, version sync, and repo guard pass.
- ruff lint passes.

## Known Limitations / Remaining Physical Gates

- Exact HamGeek PCB revision: UNVERIFIED_PHYSICAL_PROPERTY
- Timing connector family (U.FL/MMCX/etc.): UNVERIFIED_PHYSICAL_PROPERTY
- 10 MHz/PPS direction and electrical levels: UNVERIFIED_PHYSICAL_PROPERTY
- SDR PPS input reaching FPGA fabric: UNVERIFIED_PHYSICAL_PROPERTY
- External reference software detection on the device: UNVERIFIED_PHYSICAL_PROPERTY

Primary institutional output remains fail-closed until these gates pass.
# DSLV-ZPDI v5.1.0 (Consolidation & Housekeeping)
**Date:** 2026-07-18

This is a consolidation release focused on integrating the Pi5 node work (`tools/zpdi_conditions/`) and executing a do-no-harm housekeeping pass on the repository.

- **No behavior change to Pluto/GPSDO stack**. The operational SDR/timing paths remain locked and active.
- **HackRF (legacy/optional) legacy support reaffirmed**. Backwards compatibility with HackRF (legacy/optional) paths has been verified and retained.
- Dependabot PRs with failing CI tests have been closed as stale.

All tests remain green (184/184) and the version strings are synchronized.
# DSLV-ZPDI Release Notes — Rev 5.2.0

**Release Date:** 2026-07-28
**Milestone:** Demodulation engine, Full Duplex MIMO vectoring, and mobile-node dashboard refinements
**Status:** Beta — builds on the Rev 5.0.0 PlutoSDR+ / LBE-1421 Tier-1 architecture

## Summary

Rev 5.2.0 extends the Rev 5.x Tier-1 stack with an intelligent demodulation
engine and a Full Duplex MIMO vectoring framework, and folds in the Rev 5.1.0
mobile-node and TUI refinements (including the standalone `ZPDI_CONDITIONS`
conditions dashboard). Dashboard defaults are tuned for live SDR monitoring
out of the box.

## New in 5.2.0

- **Demodulation engine** (`layer1_ingestion`) — supports audio, data, video,
  and telemetry formats with auto-presets.
- **Full Duplex MIMO Vectoring framework** — spatial multiplexing and signal
  vectoring.

### Changed

- Dashboard default configs: Live SDR enabled, gain 0.0, raw modulation,
  sweep mode, center freq 3 GHz, span 40 MHz, plasma palette, LNA 30, VGA 30,
  noise floor -75.0 dBm, ceiling -70.0 dBm.
- Dashboard banner disabled by default.

## Carried forward from 5.1.0 (Mobile Node and TUI Refinements)

- New standalone dashboard package `tools/zpdi_conditions/` aggregating live
  space weather, surface weather, barometric, aerosol, and ionizing-radiation
  metrics for the Penrose, CO tracking footprint (NOAA SWPC, Open-Meteo,
  NMDB neutron monitor, EPA RadNet Colorado Springs).
- Rich two-column TUI optimized for a 10" touchscreen with per-metric refresh
  intervals, self-checking collectors, launch script, and desktop icon.
- No SDR, GPSDO, or radio hardware access; runs in parallel with the main
  `dslv-zpdi` stack without conflicts.
- Mobile node WSS transport: exponential-backoff circuit breaker and corrected
  default ingest URI (`ws://127.0.0.1:8443/`).

## Validation

- `pytest` suite green on simulator (`DEV_SIMULATOR=1`); ruff, mypy,
  orphan-checker, repo-guard, and version-sync all clean.
- Hardware-dependent claims remain gated on physical verification per
  `AGENTS.md` doctrine.
# DSLV-ZPDI v5.3.0

## Zero-Copy Binary Ingestion & Hardware-Anchored Chain of Custody Refactor

This major release implements a complete end-to-end binary payload ingestion pipeline, removing all intermediate text/JSON serialization from SDR capture to HDF5 storage.

### Key Changes
*   **Zero-Copy Binary Pipeline:** Raw SDR data is now directly packed into structured binary structs without intermediate JSON processing, significantly reducing CPU overhead.
*   **Hardware-Anchored Cryptographic Hashing:** BLAKE2b hashing is now performed immediately upon payload generation directly on the binary buffer, enforcing a zero-trust hardware-anchored chain of custody.
*   **Strict Binary Coherence Engine:** The layer-2 Coherence Engine and DualStreamRouter were refactored to work seamlessly with binary configurations, accepting pre-extracted metrics and routing efficiently without un-packaging the primary streams.
*   **100% Test Suite Stability:** Resolved all legacy `test_payload.py` and `test_pipeline.py` assumptions. All 230 system and integration tests are verified passing for the new binary structure.
*   **Dashboard Preservation:** The peripheral Layer-3 dashboards remain fully operational. `quarantine.jsonl` and `health.json` outputs remain decoupled from the primary `HDF5Writer`, ensuring dashboards continue parsing without conflict.
*   **Dependency Update:** Rebuilt and upgraded the local `.venv` dependencies, including `h5py`, `numpy`, `msgpack`, and `cryptography` to support native binary interactions.
