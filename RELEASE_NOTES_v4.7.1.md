# Release Notes v4.7.1

## DSLV-ZPDI v4.7.1 — Dependency and Validation Alignment

### Summary
Maintenance release aligning the package version with the current runtime
dependency set and validation contract after the v4.7.0 node bridge,
multi-node HDF5 aggregation, and dashboard finalisation work.

### Changes
- Added Flask and psutil to the canonical Python dependency authority for the
  node receiver and web dashboard runtime paths.
- Kept project validation anchored on editable installs, pytest, orphan
  checking, version sync, and repo guard checks.
- Preserved v4.7.0 operational scope while making dependency installation
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
