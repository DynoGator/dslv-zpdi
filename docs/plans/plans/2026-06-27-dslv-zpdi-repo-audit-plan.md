# DSLV-ZPDI Repository Audit & Tier-1 Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile the local `main` branch with `origin/main`, refresh dependencies to close Dependabot noise, make every Tier-1 hardware reference unambiguous (RPi 5 + PlutoSDR+ + LBE-1421), add ASCII art and RF humor, and leave the repo with a green validation pipeline.

**Architecture:** This is a repo-maintenance pass, not a feature build. The work is sequential: backup → environment → validation baseline → git reconciliation → dependency refresh → re-validation → documentation polish → final push. Each step is gated on the previous one staying green.

**Tech Stack:** Python 3.13 venv, pip, pytest, ruff, mypy, git, GitHub REST API (curl), standard markdown.

---

## File Structure

| File | Responsibility in this plan |
|------|-----------------------------|
| `requirements.txt` | Pinned runtime deps; bump `certifi` and `pydantic-core` here. |
| `requirements-dev.txt` | Mobile/Tier-2 dev deps; bump `httpx` here. |
| `.github/workflows/docker.yml` | Docker CI; bump `setup-qemu-action`, `setup-buildx-action`, `login-action`, `build-push-action`. |
| `.github/workflows/ci.yml` | Main CI; bump `setup-buildx-action`. |
| `.github/workflows/release.yml` | Release; bump `action-gh-release`. |
| `README.md` | Main entry point; add Tier-1 block, ASCII banner, RF joke. |
| `AGENTS.md` | Agent instructions; add Tier-1 block and RF joke. |
| `install_dslv_zpdi.sh` | Production installer; verify simulator default. |
| `docs/hardware/LBE1421_PLUTO_WIRING.md` | Wiring guide; ensure Tier-1 stack is explicit. |
| `docs/PlutoSDR/1_PlutoSDR_Plus_Preparation_Guide.md` | Prep guide; reinforce PlutoSDR+ as Tier-1. |
| `docs/operations/PLUTO_TIER1_DEPLOYMENT.md` | Deployment guide; reinforce Tier-1 stack. |
| `REPORT.md` | Closeout append target. |

---

### Task 1: Create a local safety backup

**Files:**
- Create backup ref only (no file changes).

- [ ] **Step 1: Tag the pre-audit state**

```bash
cd /home/dynogator/Desktop/DSLV-ZPDI_GitHub_Dev/dslv-zpdi
git tag backup/2026-06-27-pre-audit
```

- [ ] **Step 2: Verify the tag exists**

```bash
git rev-parse backup/2026-06-27-pre-audit
```

Expected output: a 40-char SHA matching current `HEAD`.

---

### Task 2: Install project dev dependencies

**Files:**
- Modify: `.venv` state (no tracked file changes).

- [ ] **Step 1: Install editable package with dev extras**

```bash
cd /home/dynogator/Desktop/DSLV-ZPDI_GitHub_Dev/dslv-zpdi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
```

Expected: `Successfully installed dslv-zpdi ... pytest ... ruff ... mypy ...`.

- [ ] **Step 2: Confirm pytest is available**

```bash
.venv/bin/python -m pytest --version
```

Expected output shows pytest version, not `No module named pytest`.

---

### Task 3: Run the initial validation contract

**Files:**
- No tracked file changes.

- [ ] **Step 1: pip check**

```bash
.venv/bin/python -m pip check
```

Expected: `No broken requirements found.`

- [ ] **Step 2: Version sync check**

```bash
.venv/bin/python tools/check_version_sync.py
```

Expected: `[OK] Version sync clean: 5.0.0`

- [ ] **Step 3: Orphan checker**

```bash
.venv/bin/python tools/orphan_checker.py
```

Expected: no unmapped source files (exit 0).

- [ ] **Step 4: Repo guard**

```bash
.venv/bin/python tools/repo_guard.py
```

Expected: all checks `[OK]` and `Repo guard passed`.

- [ ] **Step 5: Ruff lint**

```bash
.venv/bin/python -m ruff check src/ tools/ tests/
```

Expected: no errors.

- [ ] **Step 6: Mypy (layer2_core only)**

```bash
.venv/bin/python -m mypy src/dslv_zpdi/layer2_core
```

Expected: `Success: no issues found in ... sources`.

- [ ] **Step 7: Pytest under simulator**

```bash
DEV_SIMULATOR=1 .venv/bin/python -m pytest tests/ -q --tb=short
```

Expected: all tests pass.

- [ ] **Step 8: Pipeline golden test**

```bash
DEV_SIMULATOR=1 .venv/bin/python tests/test_pipeline.py
```

Expected: exit 0.

---

### Task 4: Reconcile local `main` with `origin/main`

**Files:**
- Modify: `main` branch history (merge commit).

- [ ] **Step 1: Fetch origin**

```bash
git fetch origin
```

Expected: fetches `origin/main` and the Dependabot branches.

- [ ] **Step 2: Attempt merge of `origin/main`**

```bash
git merge origin/main --no-edit
```

Expected outcomes:
- Clean merge: proceed.
- Conflicts: resolve in favor of local changes unless the incoming `origin/main` change is clearly newer hardware guidance. For `install_dslv_zpdi.sh`, prefer the local simulator-explicit default. For docs, prefer the most accurate Tier-1 description.

- [ ] **Step 3: If merge is too messy, abort and escalate**

```bash
git merge --abort
```

Use only if conflicts cannot be resolved safely without user input.

---

### Task 5: Batch-update dependencies to close Dependabot noise

**Files:**
- Modify: `requirements.txt`
- Modify: `requirements-dev.txt`
- Modify: `.github/workflows/docker.yml`
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/release.yml`

- [ ] **Step 1: Bump `certifi` in `requirements.txt`**

Replace:
```text
certifi==2026.5.20
```
with:
```text
certifi==2026.6.17
```

- [ ] **Step 2: Bump `pydantic-core` in `requirements.txt`**

Replace:
```text
pydantic-core==2.46.4
```
with:
```text
pydantic-core==2.47.0
```

- [ ] **Step 3: Bump `httpx` in `requirements-dev.txt`**

Replace:
```text
httpx>=0.28
```
with:
```text
httpx>=0.28.1
```

- [ ] **Step 4: Bump Docker workflow actions in `.github/workflows/docker.yml`**

Replace all occurrences:
- `docker/setup-qemu-action@v3` → `docker/setup-qemu-action@v4`
- `docker/setup-buildx-action@v3` → `docker/setup-buildx-action@v4`
- `docker/login-action@v3` → `docker/login-action@v4`
- `docker/build-push-action@v6` → `docker/build-push-action@v7`

- [ ] **Step 5: Bump Buildx action in `.github/workflows/ci.yml`**

Replace:
```yaml
        uses: docker/setup-buildx-action@v3
```
with:
```yaml
        uses: docker/setup-buildx-action@v4
```

- [ ] **Step 6: Bump release action in `.github/workflows/release.yml`**

Replace:
```yaml
        uses: softprops/action-gh-release@v2
```
with:
```yaml
        uses: softprops/action-gh-release@v3
```

- [ ] **Step 7: Commit the dependency refresh**

```bash
git add -A
git commit -m "chore(deps): batch dependency refresh to close Dependabot noise

- certifi 2026.5.20 -> 2026.6.17
- pydantic-core 2.46.4 -> 2.47.0
- httpx >=0.28 -> >=0.28.1
- docker/setup-qemu-action v3 -> v4
- docker/setup-buildx-action v3 -> v4
- docker/login-action v3 -> v4
- docker/build-push-action v6 -> v7
- softprops/action-gh-release v2 -> v3"
```

---

### Task 6: Re-run the full validation contract

**Files:**
- No tracked file changes.

- [ ] **Step 1: Re-run all validation commands from Task 3**

```bash
.venv/bin/python -m pip check
.venv/bin/python tools/check_version_sync.py
.venv/bin/python tools/orphan_checker.py
.venv/bin/python tools/repo_guard.py
.venv/bin/python -m ruff check src/ tools/ tests/
.venv/bin/python -m mypy src/dslv_zpdi/layer2_core
DEV_SIMULATOR=1 .venv/bin/python -m pytest tests/ -q --tb=short
DEV_SIMULATOR=1 .venv/bin/python tests/test_pipeline.py
```

Expected: all green. If any step fails, fix before proceeding.

---

### Task 7: Verify Tier-1 defaults in the installer

**Files:**
- Modify: `install_dslv_zpdi.sh` (only if the simulator default is wrong).

- [ ] **Step 1: Inspect the simulator-default block around line 592**

```bash
sed -n '588,597p' install_dslv_zpdi.sh
```

Expected content:
```bash
    if [[ "$SIMULATOR_MODE" -eq 1 ]]; then
        # Use simulator mode only if explicitly requested via --simulator flag
        PIPE_EXEC="${PIPE_EXEC} --simulator"
        PIPE_ENV="Environment=DEV_SIMULATOR=1"
    fi
```

- [ ] **Step 2: If the block still falls back to simulator when GPSDO is absent, fix it**

Replace:
```bash
    if [[ "$SIMULATOR_MODE" -eq 1 ]] || [[ -z "${GPSDO_PRESENT:-}" ]]; then
        # Default to simulator mode until GPSDO delivery is confirmed
```
with:
```bash
    if [[ "$SIMULATOR_MODE" -eq 1 ]]; then
        # Use simulator mode only if explicitly requested via --simulator flag
```

- [ ] **Step 3: Commit if changed**

```bash
git add install_dslv_zpdi.sh
git commit -m "fix(install): require explicit --simulator; Tier-1 hardware is default"
```

---

### Task 8: Reinforce Tier-1 hardware in key docs

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/hardware/LBE1421_PLUTO_WIRING.md` (if stale)
- Modify: `docs/PlutoSDR/1_PlutoSDR_Plus_Preparation_Guide.md` (if stale)
- Modify: `docs/operations/PLUTO_TIER1_DEPLOYMENT.md` (if stale)

- [ ] **Step 1: Insert Tier-1 Reference Node block into `README.md` near the top**

Add immediately after the first-level title (`# DSLV-ZPDI`):

```markdown
## Tier-1 Reference Node

The canonical production node for this repository is:

- **Compute:** Raspberry Pi 5
- **SDR:** HamGeek PlutoSDR+ (AD9363, 1 GB RAM)
- **Timing:** Leo Bodnar LBE-1421 GPSDO
- **Clocking:** LBE-1421 10 MHz Out2 → PlutoSDR+ CLKIN
- **PPS:** LBE-1421 1 PPS Out1 → Raspberry Pi GPIO 18

Other hardware (HackRF (legacy/optional) One, Pixel 9 Pro XL mobile node, etc.) is supported as Tier-2 or experimental configurations.
```

- [ ] **Step 2: Insert or update Tier-1 block in `AGENTS.md`**

Replace the existing `## Hardware Profile` section with:

```markdown
## Hardware Profile

Verified local notes identify this current Tier-1 profile:

- Raspberry Pi 5 anchor.
- HamGeek PlutoSDR+ 1 GB / AD9363 at `ip:192.168.3.80`.
- Leo Bodnar LBE-1421 GPSDO.
- LBE-1421 10 MHz Out2 to PlutoSDR+ CLKIN.
- LBE-1421 1 PPS Out1 to Pi GPIO 18.
- Pixel 9 Pro XL GrapheneOS as the Tier-2 mobile node.

Do not mark physical hardware validation as passing unless it was actually run against the node and the command output was recorded.
```

- [ ] **Step 3: Spot-check remaining hardware docs for stale primary-node language**

Search for old primary-node phrasing:

```bash
grep -Rni "HackRF (legacy/optional).*primary\|primary.*HackRF (legacy/optional)\|lbe-1420.*tier-1\|tier-1.*lbe-1420" docs/ README.md AGENTS.md || true
```

If any false positives appear, fix them. If nothing appears, no changes needed.

- [ ] **Step 4: Commit docs updates**

```bash
git add -A
git commit -m "docs: unambiguous Tier-1 hardware profile (RPi 5 + PlutoSDR+ + LBE-1421)"
```

---

### Task 9: Add ASCII art and RF humor

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Insert ASCII banner into `README.md` after the Tier-1 block**

```text
```text
                           _.-.
                         _/ .   \_.
                        /    .-.    \
                       /    /   \    \
                      /    /     \    \
                     /    /       \    \
                    /    /_________\    \
                   /     DSLV-ZPDI  \    \
                  /    Tier-1 Node   \    \
                 /______/_________\____\    \
                       |    |    |
                    .--'     |     '--.
                  LBE-1421  |   PlutoSDR+
                   GPSDO     |    AD9363
              10 MHz + 1 PPS |   1 GB RAM
                       |     |
                      RPi 5
```
```

- [ ] **Step 2: Add an RF joke under the banner in `README.md`**

```markdown
> **RF Dad Joke #1:** Why did the SDR break up with the oscillator? It needed more space… 10 MHz of it.
```

- [ ] **Step 3: Add an RF joke to `AGENTS.md` after the validation section**

```markdown
> **RF Dad Joke #2:** Our Tier-1 node is so phase-locked that even the jitter calls in sick.
```

- [ ] **Step 4: Commit the artwork and jokes**

```bash
git add README.md AGENTS.md
git commit -m "docs: ASCII banner and RF dad jokes for Tier-1 node"
```

---

### Task 10: Final validation before push

**Files:**
- No tracked file changes.

- [ ] **Step 1: Full validation pass**

Run the same contract as Task 6:

```bash
.venv/bin/python -m pip check
.venv/bin/python tools/check_version_sync.py
.venv/bin/python tools/orphan_checker.py
.venv/bin/python tools/repo_guard.py
.venv/bin/python -m ruff check src/ tools/ tests/
.venv/bin/python -m mypy src/dslv_zpdi/layer2_core
DEV_SIMULATOR=1 .venv/bin/python -m pytest tests/ -q --tb=short
DEV_SIMULATOR=1 .venv/bin/python tests/test_pipeline.py
```

Expected: all green.

- [ ] **Step 2: Confirm working tree is clean**

```bash
git status
```

Expected: `nothing to commit, working tree clean`.

---

### Task 11: Push `main` to origin

**Files:**
- Modify: remote `main` branch.

- [ ] **Step 1: Attempt fast-forward-safe push**

```bash
git push origin main
```

Expected: `* [new tag] ...` or `main -> main`.

- [ ] **Step 2: If push is rejected as non-fast-forward, do not force**

Stop and report the rejection. Do **not** run `git push --force` without explicit user approval.

---

### Task 12: Close Dependabot PRs and issues

**Files:**
- Modify: GitHub PR/issue state only.

- [ ] **Step 1: Identify the local merge commit SHA**

```bash
git rev-parse HEAD
```

Capture the SHA (e.g., `abc1234`).

- [ ] **Step 2: Close each open Dependabot PR with a reference**

For each of the 8 open PRs (#8–#15), run:

```bash
curl -s -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  https://api.github.com/repos/DynoGator/dslv-zpdi/pulls/<PR_NUMBER>/comments \
  -d '{"body":"Consolidated into dependency refresh commit <SHA>. Closing."}'

curl -s -X PATCH \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  https://api.github.com/repos/DynoGator/dslv-zpdi/pulls/<PR_NUMBER> \
  -d '{"state":"closed"}'
```

If `GITHUB_TOKEN` is not available, skip the API calls and document the closure URLs for the user.

---

### Task 13: Write closeout report

**Files:**
- Modify: `REPORT.md`

- [ ] **Step 1: Append a closeout section to `REPORT.md`**

```markdown
## 2026-06-27 Repository Audit Closeout

- Reconciled local `main` with `origin/main`.
- Installed dev dependencies and validated:
  - `pip check`: pass
  - `check_version_sync.py`: 5.0.0
  - `orphan_checker.py`: pass
  - `repo_guard.py`: pass
  - `ruff check`: pass
  - `mypy src/dslv_zpdi/layer2_core`: pass
  - `DEV_SIMULATOR=1 pytest tests/`: pass
  - `DEV_SIMULATOR=1 python tests/test_pipeline.py`: pass
- Batch-updated dependencies to close Dependabot PRs #8–#15.
- Reinforced Tier-1 hardware profile (RPi 5 + HamGeek PlutoSDR+ + Leo Bodnar LBE-1421 GPSDO).
- Added ASCII art and RF dad jokes to README and AGENTS.
- Pushed `main` to origin (or documented push blocker).

Remaining user-owned items:
- Physical firmware/OS updates on the actual Tier-1 node.
- Any hardware validation that must be run against live hardware.
```

- [ ] **Step 2: Commit the closeout**

```bash
git add REPORT.md
git commit -m "docs: 2026-06-27 repository audit closeout"
```

If Task 11 push already happened, run `git push origin main` again to include this commit.

---

## Self-Review Checklist

- [ ] Spec coverage: every design section (cleanup, validation, reconciliation, deps, docs, humor, push, closeout) maps to one or more tasks.
- [ ] Placeholder scan: no `TBD`, `TODO`, or vague "handle edge cases" steps.
- [ ] Type consistency: N/A for this maintenance pass; no new code signatures introduced.
- [ ] Safety: no `--force` push; escalation path defined for messy merges.
