# DSLV-ZPDI Repository Audit & Tier-1 Alignment Design

**Date:** 2026-06-27  
**Topic:** `dslv-zpdi` repo hardening, GitHub alignment, Tier-1 hardware narrative, and professional documentation polish.  
**Approach:** Conservative audit-and-align (Option A).

---

## 1. Goal

Bring the local `dslv-zpdi` repository, the GitHub remote, the dependency tree, the validation pipeline, and the hardware documentation into a single coherent, production-ready state where:

- All local commits are merged to `main` and pushed.
- All open Dependabot noise is resolved.
- Lint, type-check, and test suites pass under `DEV_SIMULATOR=1`.
- The Tier-1 node (RPi 5 + HamGeek PlutoSDR+ + Leo Bodnar LBE-1421 GPSDO) is unambiguously documented as the primary reference platform.
- The repo remains well structured, highly documented, and sprinkled with the requested cheesy RF jokes and corny ASCII artwork.

Out of scope: physical firmware flashing, OS package updates, and changes that require user-provided hardware access.

---

## 2. Current State

| Item | State |
|------|-------|
| Active local branch | `main` |
| Local `main` tip | `677bb90` (design doc commit) |
| Local `main` vs `origin/main` | 10 ahead, 13 behind (`origin/main` at `c4504cf8`) — non-fast-forward |
| Codex hardening branch | `codex/repo-hardening-2026-06-17` at `9ac03ae`; its commits are already incorporated into local `main` |
| Uncommitted changes | `install_dslv_zpdi.sh` (simulator-default logic) |
| Untracked files | `replace_text.py` |
| `.venv` test tooling | `pytest` not installed |
| GitHub open PRs | 8 Dependabot bumps (pip + GitHub Actions) |
| GitHub open issues | Same 8 Dependabot items |
| Version sync | Clean at `5.0.0` |
| Repo guard / pip check | Passing |
| Hardware profile in `AGENTS.md` | Already RPi 5 + PlutoSDR+ + LBE-1421 |

---

## 3. Target State

1. `main` contains all local work plus the dependency refresh.
2. `origin/main` matches local `main` (push succeeds or is clearly documented).
3. Dependabot PRs/issues are closed by a single consolidated dependency update commit.
4. `DEV_SIMULATOR=1` test suite, ruff, mypy, and repo guard all pass.
5. README, AGENTS, and key hardware docs reinforce the Tier-1 platform and include ASCII art + RF humor.
6. No uncommitted changes or stray untracked files remain.

---

## 4. Design Sections

### 4.1 Local State Cleanup

- Inspect `replace_text.py`; if it is a one-off helper, either delete it or move it into `tools/` with a docstring and a SPEC mapping.
- Decide the fate of the `install_dslv_zpdi.sh` hunk. The change removes the GPSDO-presence fallback to simulator mode, making `--simulator` explicit. This matches the “Tier-1 hardware is primary” goal, so it should be committed as a dedicated fixup commit.
- Run `git status` again before any merges to ensure no other working-tree surprises.

### 4.2 Development Environment & Validation

- Install the project in editable mode with dev extras: `pip install -e ".[dev]"`.
- Run the validation contract in order:
  1. `pip check`
  2. `tools/check_version_sync.py`
  3. `tools/orphan_checker.py`
  4. `tools/repo_guard.py`
  5. `ruff check src/ tools/ tests/`
  6. `mypy src/dslv_zpdi/layer2_core`
  7. `DEV_SIMULATOR=1 pytest tests/ -q --cov --cov-report=term-missing`
  8. `DEV_SIMULATOR=1 python tests/test_pipeline.py`
- Any failures are fixed in-place if they are low-hanging; blockers are reported to the user.

### 4.3 Branch Reconciliation & Remote Push

- The `codex/repo-hardening-2026-06-17` commits are already on local `main`; no separate branch merge is required.
- Because local `main` and `origin/main` have diverged (10 ahead, 13 behind), a plain push will be non-fast-forward.
- First attempt a merge of `origin/main` into local `main` to reconcile the divergence:
  - `git fetch origin`
  - `git merge origin/main` (or rebase if history is clean enough)
  - Resolve any conflicts in favor of the local work unless they are stale.
- Only attempt `git push origin main` after the merge/rebase and full validation pass.
- If merge conflicts are complex or push credentials are missing, stop and report rather than force-push.

### 4.4 Dependency Refresh & Dependabot Closure

- Read the 8 open Dependabot PRs/issues and identify the target versions.
- Apply the bumps directly to `pyproject.toml` / `requirements.txt` / GitHub Actions workflows as a single `chore(deps): batch dependency refresh` commit.
- Run the full validation contract again.
- If push access is available, close the Dependabot PRs/issues via GitHub API with a reference to the consolidating commit. Otherwise, document the closure steps for the user.

### 4.5 Hardware Docs Alignment

- Audit `AGENTS.md`, `README.md`, `PHASE_2A_TIER_1_BUILD_SHEET.md`, `docs/hardware/LBE1421_PLUTO_WIRING.md`, `docs/PlutoSDR/*.md`, and `docs/operations/PLUTO_TIER1_DEPLOYMENT.md`.
- Ensure every Tier-1 reference uses the canonical stack: Raspberry Pi 5, HamGeek PlutoSDR+ (AD9363, 1 GB), Leo Bodnar LBE-1421 GPSDO, with LBE-1421 10 MHz → Pluto CLKIN and LBE-1421 1 PPS → Pi GPIO 8.
- Remove any stale references that imply HackRF (legacy/optional) One or older LBE-1421/LBE-1421 confusion as the primary node.
- Add a short “Tier-1 Reference Node” block near the top of README and AGENTS.

### 4.6 ASCII Art & RF Humor

- Insert a corny ASCII banner at the top of `README.md` (e.g., a PlutoSDR+/GPSDO/Pi constellation).
- Add one to three groan-worthy RF jokes in `AGENTS.md` and `README.md` (e.g., “Why did the SDR break up with the oscillator? It needed more space… 10 MHz of it.”).
- Keep humor tasteful, on-brand, and clearly marked so it does not interfere with operational instructions.

### 4.7 Final Validation & Sign-Off

- Run the validation contract one last time on the consolidated `main`.
- Produce a short `AUDIT_CLOSEOUT.md` or append to `REPORT.md` summarizing what was merged, what was updated, and what remains user-owned (physical firmware, Dependabot closure if push failed).
- Ensure the working tree is clean.

---

## 5. Error Handling & Rollback

- Before any destructive merge, create a local backup branch: `git branch backup/2026-06-27-pre-audit`.
- If tests fail after a change, fix the change before merging to `main`; do not push a red `main`.
- If push fails, leave `main` green and document the push command for the user.
- If Dependabot bumps conflict, resolve them in the consolidated dependency commit rather than merging each PR individually.

---

## 6. Testing Strategy

- Use the existing test suite under `DEV_SIMULATOR=1`.
- Add no new feature code; therefore, no new tests are required.
- If docs-only changes are made, rely on the lint/ruff/repo-guard checks and a manual markdown render check.
- All validation commands must pass before the final push.

---

## 7. Files Likely to Change

- `install_dslv_zpdi.sh`
- `pyproject.toml`
- `requirements.txt`
- `.github/workflows/*.yml`
- `README.md`
- `AGENTS.md`
- `PHASE_2A_TIER_1_BUILD_SHEET.md`
- `docs/hardware/LBE1421_PLUTO_WIRING.md`
- `docs/PlutoSDR/1_PlutoSDR_Plus_Preparation_Guide.md`
- `docs/PlutoSDR/2_PlutoSDR_Plus_Troubleshooting_Reference.md`
- `docs/operations/PLUTO_TIER1_DEPLOYMENT.md`
- Possibly `tools/replace_text.py` if the untracked helper is promoted.
- New: `docs/superpowers/plans/2026-06-27-dslv-zpdi-repo-audit-plan.md` (implementation plan).
