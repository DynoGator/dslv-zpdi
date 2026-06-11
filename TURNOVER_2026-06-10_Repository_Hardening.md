# TURNOVER 2026-06-10 — Repository Hardening (Rev 4.8.0)

## Purpose

Autonomous repository audit remediation: reconcile the version desync, fix the
breakage that the weak on-main CI let through, and stand up real CI + security +
contributor infrastructure. **No runtime, RF, GPSDO/timing, HDF5-schema, trust,
or metrology behavior was changed.**

## Context

- **Machine / OS:** NucBox G2 (`nukbox`), Debian 13 Trixie, Python 3.13.5.
- **Checkout:** `/home/dynogator/Desktop/DSLV-ZPDI_GitHub_Dev/dslv-zpdi`
- **Remote:** `https://github.com/DynoGator/dslv-zpdi.git` (no token in remote URL).
- **Starting commit (origin/main):** `985d8ca` — local checkout was stale at
  `d8a4f89` and was fast-forwarded to `985d8ca` (v4.8.0 / Phase 2B) at session start.
- **Branch:** `chore/repository-hardening` (PR #1, merged as `4b8a2be`); CI workflow
  landed via follow-up branch `ci/real-validation-matrix` (PR #2) once the `workflow`
  token scope was granted.
- **PR:** #1 (hardening, merged) + #2 (CI workflow, merged).
- **Ending main commit:** PR #2 merge (see GitHub); `main` green on the new matrix.

## Starting State Found On `main` (985d8ca)

The weak on-main workflow (`dslv_zpdi_ci.yml`) ran only the orphan checker + a
10-test smoke, so the Phase 2B merge had landed **broken but "green"**:

- `pytest`: **4 failed**, 99 passed (async tests never executed — `pytest-asyncio`
  missing).
- `ruff`: **117 errors**.
- **Version desync:** code declared 4.7.2 but tag `v4.8.0` + CHANGELOG said 4.8.0.
- `pip check`, `orphan_checker`, `repo_guard`, pipeline smoke: clean.

## Major Changes (one logical commit each)

1. `style(lint)` — cleared 117 ruff findings (annotation modernization, import
   hygiene, 2 dead vars). Unit-encoded schema names kept via scoped `# noqa`.
2. `chore(release)` — reconciled version to 4.8.0 (pyproject, `__init__.py`,
   README, new `RELEASE_NOTES_v4.8.0.md`) + added `pytest-asyncio` / `asyncio_mode`.
3. `security(repo)` — `SECURITY.md` + `.github/dependabot.yml`.
4. `docs(github)` — YAML issue forms (bug/feature/hardware_incident) + config +
   `CODEOWNERS`.
5. `build(container)` — `compose.yaml` (simulator-first, opt-in hardware profile).
6. `test(coverage)` — `[tool.coverage]` config + artifact ignores.
7. `docs(structure)` — `docs/README.md` index.
8. `build(container)` — `.dockerignore`.
9. `ci(github)` — rewrote `dslv_zpdi_ci.yml` into a full 3.10–3.13 matrix +
   package-build job. **(Requires `workflow` token scope to push — see Warnings.)**
10. `docs(turnover)` — this note + hardening report + CHANGELOG + NEXT_STEPS.

## Validation (exact commands)

```bash
.venv/bin/python -m pip check
.venv/bin/python tools/check_version_sync.py
.venv/bin/python tools/orphan_checker.py
.venv/bin/python tools/repo_guard.py
.venv/bin/ruff check src/ tools/ tests/
DEV_SIMULATOR=1 .venv/bin/python -m pytest tests/ -q --cov
DEV_SIMULATOR=1 .venv/bin/python tests/test_pipeline.py
.venv/bin/python -m build && .venv/bin/twine check dist/*
docker build -t dslv-zpdi:sim .
```

### Results

- pip check: clean
- version_sync: **clean at 4.8.0**
- orphan_checker: clean
- repo_guard: clean
- ruff: **All checks passed**
- pytest: **103 passed**
- pipeline smoke: **10/10**
- pylint: 9.44/10 (Phase 2B code; informational, not a gate)
- coverage: **~53%** (branch), `fail_under=50`
- build + twine check: **PASSED**; clean-venv wheel install imports 4.8.0
- container build: see hardening report
- CI on PR / merge: see hardening report

## GitHub Settings Changed

- Enabled **Dependabot vulnerability alerts** + **automated security updates**.
- **No** branch protection / push protection / code scanning changed — other
  agents are actively pushing directly to `main`; non-blocking settings only, by
  decision.

## Preserved Stashes

- `stash@{0}: codex-preserve-ci-workflow-oauth-blocked-2026-06-01` — left
  **intact**, not popped. It predates the Phase 2B merge and would conflict; the
  CI work it represents is superseded by the new `dslv_zpdi_ci.yml`. Do not blindly
  pop it; diff first.

## Warnings For The Next Coder

- **`workflow` token scope:** the GitHub token (`gist, read:org, repo`) cannot push
  `.github/workflows/`. If the CI commit is not on `main`, it was held back; add it
  via `gh auth refresh -s workflow` then push, or paste the file via the web UI.
- The on-main `dslv_zpdi_ci.yml` is intentionally weak. Until the new matrix is on
  `main`, **green CI does not mean the suite passes** — run the full local contract.
- Other agents push directly to `main` and to many feature branches; fast-forward
  and re-run the contract before trusting state.

## Next Actionable Work

- Land the CI matrix on `main` (workflow scope) so future merges are gated.
- Consider branch protection requiring the new checks once contributors coordinate.
- Continue `NEXT_STEPS.md` Priority 1 (Tier 1 hardware truth path) and Priority 4
  (SPEC-015 RadonEye promotion — keep RadonEye secondary-only).

## Recovery / Rollback

- All work is on `chore/repository-hardening`; revert the PR merge to undo.
- No history rewrite, no force push, no `reset --hard`/`clean` were used.
