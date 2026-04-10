# Changelog

All notable changes to the DSLV-ZPDI project will be documented in this file.

## [4.0.2.4] - 2026-04-10

### Added
- **Architectural Hardening:** Implemented SPEC-010 (Packet Integrity), SPEC-009.1 (Atomic Baseline Persistence), SPEC-008.2 (Temporal Freshness), SPEC-005A.5 (Immutable IQ Digest), and SPEC-004A.2 (PTP Watchdog).
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
- **PTP Verification:** Deployed `tools/check_ptp.py` and `tools/provision_tier1.py` for SPEC-004A.1 enforcement.
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
