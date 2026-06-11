# DSLV-ZPDI Continued Development Plan

**Status date:** 2026-06-10
**Baseline:** Rev 4.8.0 (Phase 2B radon metrology stack merged), Tier 1 Pi 5 anchor operational, Pixel 9 Pro XL Tier 2 bridge active. Simulator suite 103 passed, ruff clean, version-sync clean, coverage ~53%.

## Done In The 2026-06-10 Repository Hardening Session

- Fixed 4 failing async tests on `main` (added `pytest-asyncio`).
- Reconciled the 4.7.2→4.8.0 version desync across all authorities; added `RELEASE_NOTES_v4.8.0.md`.
- Cleared 117 ruff findings in the Phase 2B modules (no metrology semantics changed).
- Replaced the weak CI with a full Python 3.10–3.13 validation + package-build matrix.
- Added `SECURITY.md`, Dependabot, YAML issue forms, `CODEOWNERS`, `compose.yaml`, `.dockerignore`, `docs/README.md`, coverage config.
- Enabled Dependabot alerts + security updates.

See `docs/audits/REPOSITORY_HARDENING_REPORT_2026-06-10.md` for full detail.

## Priority 0 - Keep The Repo Trustworthy

- Keep every function/class mapped to a real SPEC-ID; run `tools/orphan_checker.py` before commit.
- Keep `pyproject.toml`, README revision, `CHANGELOG.md`, and `RELEASE_NOTES_v*.md` synchronized.
- Require editable install validation in `.venv` before trusting pytest results.
- Keep all local machine checkouts fast-forwarded before development starts.

## Priority 1 - Hardware Truth Path

- Run a Tier 1 hardware validation session on the Pi 5 with LBE-1421, PPS, NMEA, and HackRF attached.
- Capture fresh validation evidence into `docs/validation-logs/` only after confirming it contains no secrets or machine-local noise.
- Confirm chrony PPS second-boundary behavior and decide whether gpsd SOCK integration should replace direct serial NMEA access.

## Priority 2 - Node Bridge Hardening

- Add contract tests for `/api/v1/ingest`, `/api/v1/ingest/radoneye`, and `/api/v1/health` around malformed JSON, missing fields, writer failure, and concurrent POSTs.
- Add schema documentation for Pixel/GrapheneOS mobile node telemetry.
- Decide whether node receiver writes should remain direct-to-HDF5 or move behind a queue for burst tolerance.

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
