# DSLV-ZPDI Continued Development Plan

**Status date:** 2026-06-11
**Baseline:** Rev 4.8.1 (Grok autonomous simulator session on Pixel proot host). Simulator suite 113 passed (full collection now works on no-lib hosts), ruff clean, version-sync clean, coverage ~53% (node_receiver now exercised by contract tests). See GROK_WORK_REPORT_2026-06-11.md and TURNOVER_2026-06-11_Grok_NodeBridgeHardening.md.

## Done In The 2026-06-10 Repository Hardening Session

- Fixed 4 failing async tests on `main` (added `pytest-asyncio`).
- Reconciled the 4.7.2→4.8.0 version desync across all authorities; added `RELEASE_NOTES_v4.8.0.md`.
- Cleared 117 ruff findings in the Phase 2B modules (no metrology semantics changed).
- Replaced the weak CI with a full Python 3.10–3.13 validation + package-build matrix.
- Added `SECURITY.md`, Dependabot, YAML issue forms, `CODEOWNERS`, `compose.yaml`, `.dockerignore`, `docs/README.md`, coverage config.
- Enabled Dependabot alerts + security updates.

See `docs/audits/REPOSITORY_HARDENING_REPORT_2026-06-10.md` for full detail.

## Done In The 2026-06-11 Grok Autonomous Simulator Session (Pixel proot, no hardware)
- Task A (critical): broadened native (ImportError, OSError) guards for libhackrf/Soapy (hal_hardware), h5py (writers), bleak (radoneye). Audit + justification for pure-Python guards left alone. Collection blast radius fixed; 113 passed on this host.
- Task B: test_pipeline.py now reads __version__ dynamically; banners conservatively appended.
- Task C (P2 Node Bridge Hardening): 10 new SPEC-014.8 contract tests for the three HTTP endpoints (malformed, missing, writer-fail, concurrent POSTs). specs/SPEC-014.md extended. Coverage lift on node_receiver from 0%. RadonEye kept secondary-only.
- Version 4.8.0→4.8.1 bump + full authority sync (pyproject, __init__, README, CHANGELOG, new RELEASE_NOTES_v4.8.1.md). 3 atomic commits, full §2 green before/after each and post-push.
- Deliverables: GROK_WORK_REPORT_2026-06-11.md, TURNOVER_2026-06-11_..., updated NEXT_STEPS.
- P2 items above now complete. P1 (hardware truth on Pi 5) is next priority.

See the TURNOVER file for exact reproduction commands and the work report for root-cause detail + coverage.

## Priority 0 - Keep The Repo Trustworthy

- Keep every function/class mapped to a real SPEC-ID; run `tools/orphan_checker.py` before commit.
- Keep `pyproject.toml`, README revision, `CHANGELOG.md`, and `RELEASE_NOTES_v*.md` synchronized.
- Require editable install validation in `.venv` before trusting pytest results.
- Keep all local machine checkouts fast-forwarded before development starts.

## Priority 1 - Hardware Truth Path

- Run a Tier 1 hardware validation session on the Pi 5 with LBE-1421, PPS, NMEA, and HackRF attached.
- Capture fresh validation evidence into `docs/validation-logs/` only after confirming it contains no secrets or machine-local noise.
- Confirm chrony PPS second-boundary behavior and decide whether gpsd SOCK integration should replace direct serial NMEA access.

## Priority 2 - Node Bridge Hardening (COMPLETE — 2026-06-11 Grok session)

- [x] Add contract tests for `/api/v1/ingest`, `/api/v1/ingest/radoneye`, and `/api/v1/health` around malformed JSON, missing fields, writer failure, and concurrent POSTs. (SPEC-014.8, 10 tests, `tests/test_node_receiver.py`)
- [x] Add schema documentation for Pixel/GrapheneOS mobile node telemetry. (Extended SPEC-014.md; no new public contract surface.)
- Deferred: queueing decision (not in scope; simulator host only).

See "Done In The 2026-06-11..." block + TURNOVER for details. Next work here only after P1 hardware baseline.

## Priority 3 - Dashboard And Field Operations

- Validate the 7 inch DSI layout on real hardware and capture screenshots or validation logs.
- Exercise `tools/launch_project.sh`, `tools/preflight.sh`, and systemd units after a cold boot.
- Confirm HackRF amplifier lockout remains enforced in both pipeline and dashboard paths.

## Priority 4 - SPEC-015 RadonEye Promotion

- Write the RadonEye calibration baseline specification before allowing any primary-stream promotion.
- Define units, sampling cadence, calibration evidence, and quarantine-to-primary acceptance rules.
- Keep current RadonEye endpoint secondary-only until SPEC-015 is complete.

## Priority 5 - Multi-Machine Discipline

- Every machine should use the same repo start protocol from `docs/collaboration/README.md`.
- Tool-specific checkouts may exist, but the central repo checkout remains canonical.
- Preserve dirty work in a named stash before fast-forwarding old tool checkouts.
- Record stashes and machine-specific state in turnover notes.
