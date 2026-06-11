# Release Notes — v4.8.1

**Date:** 2026-06-11
**Phase:** 2B — Simulator hardening + Node Receiver contract tests (Pixel proot host)
**Tag:** `v4.8.1`
**Authority:** Joseph R. Fross (DynoGator Labs) — autonomous Grok execution on Pixel 9 Pro XL / GrapheneOS / Debian Trixie proot (aarch64, no HackRF attached)

## Summary

This patch release is the direct result of the autonomous work order executed on a **simulator-only** dev host (no libhackrf.so.0, no PPS/GPSDO hardware). The primary defect was that bare `except ImportError:` guards around native SDR libs allowed `OSError` (from `ctypes.CDLL` at import time inside third-party packages) to escape, making test collection impossible (0 tests collected) on any host without the native shared objects.

The fix broadens the guards for native-loading imports only. Pure-Python imports remain `ImportError`-only. All changes are SPEC-tied, orphan-clean, and preserve the existing fallback-to-simulator semantics.

113 tests now pass under `DEV_SIMULATOR=1` (was 103 on hw hosts; the two previously uncollectable modules now run). `test_pipeline.py` now dynamically reads the package version.

## Fixed

- **OSError vs ImportError guard defect (Task A, SPEC-005A.HAL-HW)**: 
  - `src/dslv_zpdi/layer1_ingestion/hal_hardware.py` (SoapySDR ~line 42, pyhackrf ~line 74): `except ImportError:` → `except (ImportError, OSError):`. Added Rev 4.8.x comments with exact root-cause narrative and SPEC reference.
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
- `RELEASE_NOTES_v4.8.1.md` (this file)
- `docs/collaboration/NEXT_STEPS.md` updated (P2 items marked done, new "Done in this session" block, points to P1 hardware-truth on Pi 5 next)

## Residual Risks / Deferred

- This host remains simulator-only; no hardware-truth evidence written to `docs/validation-logs/`.
- RadonEye endpoint stays explicitly secondary/quarantine-only (SPEC-015 stub exists but calibration baseline ratification is future hardware session work).
- Next priority (per TURNOVER): P1 "Hardware Truth Path" on the Pi 5 (HackRF + LBE-1421 + PPS validation).

The pushed tree is clean, remote-synced, and the full §2 contract is green on the post-push checkout.

**End of 4.8.1 release notes.** Safe for field simulator use; hardware sessions remain the source of truth for metrology claims.