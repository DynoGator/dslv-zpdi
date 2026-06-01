# TURNOVER 2026-06-01 — Claude Hardening Pass (Rev 4.7.2)

## Context

- Machine: this workstation (canonical checkout)
- Checkout: `/home/dynogator/Desktop/DSLV-ZPDI_GitHub_Dev/dslv-zpdi`
- Remote: `https://github.com/DynoGator/dslv-zpdi.git`
- Starting commit: `4e58c6c` (Rev 4.7.1)
- Active revision after pass: **Rev 4.7.2**
- Agent: Claude Code, continuing the Codex CLI local-update session

## Work Completed

Project-wide robustness / reliability / security hardening pass. Full detail in
`SESSION_REPORT_2026-06-01_Hardening.md`; release detail in
`RELEASE_NOTES_v4.7.2.md`.

- **Data integrity:** replaced `os._exit(0)` SIGINT teardown in `main_pipeline.py`
  with a cooperative SIGINT/SIGTERM drain that flushes and closes the HDF5 writer,
  timing monitor, and health reporter.
- **Latent bug:** fixed `cm5_ingestion` `ImportError` by re-exporting the canonical
  HAL surface (`__all__`) from `hal_factory`; all 31 submodules now import.
- **Security:** node receiver request-size cap (1 MiB); atomic + locked
  `node_registry.jsonl` writes; numeric validation for RadonEye `radon_bq_m3`;
  loud warning when `HDF5Writer` uses the development HMAC key.
- **Code health:** ruff clean across `src/ tools/ tests/` (~240 findings cleared);
  pylint 9.31 → 9.64/10; PEP 585/604 type modernization behind
  `from __future__ import annotations`.
- **Versioning:** added `dslv_zpdi.__version__` and made `check_version_sync.py`
  enforce it; bumped `pyproject`, README, CHANGELOG; added `RELEASE_NOTES_v4.7.2.md`.

## Validation

```bash
.venv/bin/python -m pip check
.venv/bin/python tools/check_version_sync.py
.venv/bin/python tools/orphan_checker.py
.venv/bin/python tools/repo_guard.py
.venv/bin/ruff check src/ tools/ tests/
.venv/bin/pylint src/dslv_zpdi/
DEV_SIMULATOR=1 .venv/bin/python -m pytest tests/ -v
DEV_SIMULATOR=1 .venv/bin/python tests/test_pipeline.py
```

Result:

- pip check: clean
- version_sync: clean at 4.7.2
- orphan_checker: clean
- repo_guard: passed
- ruff: All checks passed
- pylint: 9.64/10
- pytest: 47 passed
- simulator smoke: 10/10 passed

## Preserved Local Work

- Stashes: `stash@{0}: codex-preserve-ci-workflow-oauth-blocked-2026-06-01`
  (GitHub Actions hardening patch; cannot be pushed without `workflow`-scope
  credential). This commit intentionally excludes `.github/workflows/`.

## Risks / Notes

- No functional behaviour of the trust pipeline changed; changes are hardening and
  hygiene only. Simulator path fully validated; hardware-only paths
  (`hal_hardware`, `lock_monitor`, PPS/NMEA) were edited for lint/robustness but
  must still be re-confirmed on the Tier 1 Pi 5 per `NEXT_STEPS.md` Priority 1.

## Next Actions

- Continue with `docs/collaboration/NEXT_STEPS.md` (hardware truth path, node
  bridge contract tests, dashboard field checks, SPEC-015 RadonEye promotion).
- When a `workflow`-scoped credential is available, pop `stash@{0}` and push the
  CI hardening patch.
