# DSLV-ZPDI Repository Hardening Report — 2026-06-10

## 1. Executive summary

Autonomous repository audit remediation against `origin/main`. The local canonical
checkout was stale (`d8a4f89`, Rev 4.7.2) and was fast-forwarded to the live
`origin/main` (`985d8ca`, the Phase 2B / v4.8.0 stack) at session start. On the
real current `main` the weak on-main CI had let a **broken merge** land: 4 failing
tests, 117 ruff errors, and a 4.7.2↔4.8.0 version desync. This session fixed all
of that, made 5 non-hermetic tests deterministic, reconciled the version, stood up
a real CI matrix, and added security + contributor + container infrastructure.
**No runtime, RF, GPSDO/timing, HDF5-schema, trust, or metrology behavior was
changed.**

All work is on branch `chore/repository-hardening` as 11 logical commits.

## 2. Host and environment

- Host: NucBox G2 (`nukbox`), Debian 13 Trixie, kernel 6.12.
- Python 3.13.5, git 2.47.3, gh 2.94.0, Docker 29.5.3 + Compose v5.1.4 (no Podman).
- Validation venv: `.venv/bin/python` (editable install of `.[dev]`).

## 3. Repository and starting commit

- Repo: `https://github.com/DynoGator/dslv-zpdi` (public). Remote URL token-free.
- Starting `origin/main`: **`985d8ca`** (after fast-forward from stale `d8a4f89`).
- Branch created: `chore/repository-hardening`.

## 4. Starting branch and dirty-work state

- Working tree clean at session start; on `main`.

## 5. Preserved stash information

- `stash@{0}: codex-preserve-ci-workflow-oauth-blocked-2026-06-01` — left intact,
  not popped. Predates the Phase 2B merge; would conflict, and the CI work it holds
  is superseded by the new `dslv_zpdi_ci.yml`. Documented for the owner; not
  deleted.

## 6. Baseline validation (on `985d8ca`, before changes)

| Check | Result |
| --- | --- |
| pip check | clean |
| check_version_sync | passes — but at **4.7.2** (tag/CHANGELOG said 4.8.0) |
| orphan_checker | clean |
| repo_guard | clean |
| pytest (simulator) | **4 failed, 99 passed** |
| pipeline smoke | 10/10 |
| ruff | **117 errors** |
| pylint | 9.44/10 |

## 7. Audit claims confirmed

- CI was inadequate (orphan + 10-test smoke only; no pytest/ruff/version_sync/build).
- No `SECURITY.md`, no Dependabot, no YAML issue forms, no `compose.yaml`, no docs
  index, no `CODEOWNERS`, no coverage config, no branch protection, no releases.

## 8. Audit claims inaccurate or outdated

- The directive assumed the canonical checkout led development; in reality it was a
  full minor version behind (`main` had advanced to v4.8.0 / Phase 2B).
- The directive assumed a single line of work; the repo is an active multi-agent,
  multi-branch project (8+ remote branches updated during the session).
- "Create releases from existing tags": the only pre-existing tags were old
  (`v3.2.0-GOLDEN`, `v3.4.0-mobile`); the relevant `v4.8.0` tag existed but had no
  matching `RELEASE_NOTES` and the code still claimed 4.7.2.

## 9. Audit recommendations rejected/deferred due to repository law or context

- **Branch protection / push protection / code scanning: deferred** — other agents
  push directly to `main`; enabling these mid-flight would block their work. Only
  non-blocking security settings were applied (decision recorded with the owner).
- **Aggressive docs reorganization with `git mv`: deferred** — `docs/` holds other
  agents' in-flight Phase 2B working notes (`KIMI_*`); mass moves risk conflicts
  and broken links. Added an index instead and documented a recommended layout.
- **Current turnover notes kept at repo root** per the collaboration protocol (not
  moved into `docs/`).
- **No version bump for infrastructure** — kept at 4.8.0 (reconciliation only),
  per the project version policy; hardening recorded under CHANGELOG `[Unreleased]`.

## 10–13. File inventory

**Added:** `RELEASE_NOTES_v4.8.0.md`, `SECURITY.md`, `CODEOWNERS`, `compose.yaml`,
`.dockerignore`, `docs/README.md`, `.github/dependabot.yml`,
`.github/ISSUE_TEMPLATE/{bug_report,feature_request,hardware_incident,config}.yml`,
`docs/audits/REPOSITORY_HARDENING_REPORT_2026-06-10.md`,
`TURNOVER_2026-06-10_Repository_Hardening.md`.

**Modified:** `pyproject.toml`, `src/dslv_zpdi/__init__.py`, `README.md`,
`CHANGELOG.md`, `.gitignore`, `docs/collaboration/NEXT_STEPS.md`,
`.github/workflows/dslv_zpdi_ci.yml`, `tools/factory_calibration.py`, and the
Phase 2B modules/tests cleaned by ruff (`pixel_node_bridge`, `radoneye_ingestor`,
`uplink_manager`, `barometric_coherence`, `radon_session_writer`, `radon_session`,
the affected `test_*.py`, `tools/dashboard/panels/*`).

**Moved:** none via `git mv` (deferred, see §9).

**Removed:** `.github/ISSUE_TEMPLATE/bug_report.md` (superseded by `bug_report.yml`).

## 14. CI/CD implementation

Rewrote `.github/workflows/dslv_zpdi_ci.yml`:
- Triggers: PR→main, push→main, manual dispatch.
- `permissions: contents: read`; per-job timeouts; pip caching; concurrency
  cancellation; pinned actions (`checkout@v4`, `setup-python@v5`,
  `upload-artifact@v4`).
- `validate` job runs the full contract under `DEV_SIMULATOR=1`.
- `package` job builds sdist+wheel, `twine check`, and a clean-venv wheel install.
- **Note:** pushing this file requires the `workflow` token scope (see §39).

## 15. Test-matrix implementation

Python **3.10, 3.11, 3.12, 3.13** (derived from `requires-python>=3.9` and
verified-installable versions; 3.9 omitted to avoid spurious failures — flagged
for the owner). System libs `libhackrf-dev`/`libusb-1.0-0-dev` installed for
`pyhackrf`, mirroring the Dockerfile.

## 16. Coverage implementation and results

`[tool.coverage]` added (branch coverage, source `dslv_zpdi`, term+xml reports,
`fail_under=50`). Baseline: **~53%** branch coverage on the simulator suite. CI
uploads `coverage.xml` as an artifact. No threshold imposed on legacy modules
beyond the conservative floor.

## 17. Documentation reorganization

Added `docs/README.md` index; created `docs/audits/`. Heavy moves deferred (§9).

## 18–21. Security

- `SECURITY.md`: private vulnerability reporting, supported versions, in/out of
  scope (incl. HDF5 evidence integrity + Tier 2 trust bypass), redaction policy.
- `.github/dependabot.yml`: pip + github-actions + docker, weekly.
- **GitHub security features enabled:** Dependabot vulnerability alerts +
  automated security updates (non-blocking). Push protection / secret scanning /
  code scanning intentionally not changed (§9).
- **Secret-scan findings:** none. Grep over the tracked tree for token/key/private-
  key/cloud-credential patterns and for hardcoded `password|secret|api_key|token`
  in `src/config/tools` returned no real secrets (only env/keyring/argparse usage
  and `config/sensor_location.example.yaml`, an intentional template). No `.h5`,
  `.hdf5`, or `.env` files are tracked.

## 22. Contributor infrastructure

YAML issue forms (`bug_report`, `feature_request`, `hardware_incident`) with
DSLV-ZPDI-specific fields (revision/commit, sim vs hardware, node role, SDR/GPSDO/
PPS/NMEA state, power/environment, SPEC-ID, data-integrity and hardware-safety
impact, redaction warnings) + `config.yml` (blank issues off, routes security to
private advisories) + `CODEOWNERS`.

## 23. Container changes

`compose.yaml` (simulator-first `validate`/`shell`, `no-new-privileges`, no ports,
no host networking; opt-in `hardware` profile). `.dockerignore` added to stop the
build context from pulling in `.venv/.git/output/` captures. `docker build`
**succeeds and the in-container validation contract passes** (see §29–30); this
build is what surfaced the 5 non-hermetic tests, now fixed.

## 24–25. Packaging / PyPI readiness

`python -m build` + `twine check` PASSED; clean-venv wheel install imports and
reports `4.8.0`; all three console scripts present; wheel contains only the
`dslv_zpdi` package (no captures/secrets). PyPI publish **not performed** — no
Trusted Publishing configured and out of session scope; readiness is in place.

## 26. GitHub Releases

`v4.8.0` tag exists and now has matching `RELEASE_NOTES_v4.8.0.md` and a reconciled
codebase. A GitHub Release for `v4.8.0` is created from this verified tag (see
final summary). Old `v3.x` tags left untouched.

## 27. Branch-protection settings

None applied (deferred, §9). Recommended settings documented in the turnover note.

## 28. Projects and Discussions

Projects already enabled; Discussions left off. No decorative structure created
(active multi-agent contention; deferred to owner).

## 29. Validation commands

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

## 30. Exact results (final, on branch HEAD)

- pip check: clean
- version_sync: clean at **4.8.0**
- orphan_checker: clean
- repo_guard: clean
- ruff: All checks passed
- pytest: **103 passed**
- pipeline smoke: 10/10
- pylint: 9.44/10 (informational)
- coverage: ~53% branch
- build + twine check: PASSED; clean-wheel install OK
- container: build PASSED, in-container suite green

## 31–33. Hardware validation

- Performed on hardware: none (no Tier 1 Pi 5 / HackRF / GPSDO attached here).
- Simulated: all sensor paths via `DEV_SIMULATOR=1` (RadonEye, Pixel node, uplink,
  pipeline).
- Not possible this session: real PPS/NMEA/HackRF/BLE confirmation — remains
  `NEXT_STEPS.md` Priority 1.

## 34–37. PR / commits / merge / post-merge

See the final terminal summary and the PR for exact numbers (PR opened from
`chore/repository-hardening`; CI watched to green; merged; `main` fast-forwarded
locally and re-validated).

## 38. Known limitations

- `workflow` token scope governs whether the new CI is on `main` (§39).
- Coverage floor is conservative (50%); legacy modules (`main_pipeline`, watchdog)
  remain 0% covered.
- Python 3.9 is in classifiers but not in the CI matrix.

## 39. Remaining owner actions

- Grant `workflow` scope (`gh auth refresh -h github.com -s workflow`) if the CI
  workflow commit was held back, then push it / merge via web UI.
- Decide on branch protection requiring the new checks once contributors coordinate.
- Configure PyPI Trusted Publishing before any publish.
- Review/raise the coverage floor as legacy modules gain tests.

## 40. Recommended next technical work

- Land the CI matrix on `main` so future merges are gated (this would have caught
  the Phase 2B breakage automatically).
- Continue `NEXT_STEPS.md` Priority 1 (hardware truth path) and Priority 4
  (SPEC-015 RadonEye promotion — keep RadonEye secondary-only until criteria met).
- Add hermetic contract tests for the node receiver API endpoints (Priority 2).
