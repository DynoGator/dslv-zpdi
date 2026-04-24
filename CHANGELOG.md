# Changelog

All notable changes to the DSLV-ZPDI project will be documented in this file.

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
- README bumped to Rev 4.5.0 — LBE-1420 Hardened Operations Stack.

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
- **LBE-1420 GPSDO Migration:** Migrated Clock Authority from Leo Bodnar Mini GPSDO to Leo Bodnar LBE-1420 GPSDO (USB-C, NMEA telemetry, 3.3V CMOS native output).
- **NMEA Telemetry:** Added `verify_nmea_telemetry()` to HardwareHAL and NMEA check to provisioning tool for GPS fix verification via virtual serial port.
- **RF/Magnetic Shielding Docs:** Created `docs/RF_MAGNETIC_SHIELDING.md` — cyberdeck chassis design with conduction cooling, compartmentalization, galvanic isolation, and pass-through security.
- **Hardware Change Justification:** Created `docs/HARDWARE_CHANGE_JUSTIFICATION.md` (SPEC-UPDATE-PHASE-2A-LBE1420).
- **Updated BOM:** Added ANT500 antenna, SMA cabling, and jumper wire specifications to Tier 1 mandatory BOM.

### Changed
- **Dependencies:** Replaced `pyrtlsdr` with `pyhackrf` in core dependencies. RTL-SDR is Tier 2 only.
- **Version Alignment:** Synchronized all version references to 4.2.0 across pyproject.toml, README, installer, tests, specs, tools, and MASTER_SPEC documents.
- **RP1 Voltage Warning:** Updated to reflect LBE-1420 native 3.3V compatibility (no level-shifter needed).
- **Physical Routing Protocol:** Updated wiring instructions for LBE-1420-specific connections (USB-C power/telemetry, 3.3V PPS).
- **Installer:** Removed `rtl-sdr`/`librtlsdr0` from base packages (not on critical build path).

### Deprecated
- **Leo Bodnar Mini GPSDO:** Formally superseded by LBE-1420. Mini-USB connection unreliable for field ops.

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
