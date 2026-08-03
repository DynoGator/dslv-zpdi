# DSLV-ZPDI Agent Instructions

> **⚠️ AGENT DOCTRINE — READ FIRST**
> This section is binding for all autonomous agents. Violations risk hardware damage, data corruption, or security compromise.

## MANDATORY READING BEFORE ANY ACTION

Read these files in order and confirm you have read them:

1. `/root/dslv-zpdi/CREW_MEMORY.md` — live crew state, current branch, next step
2. `/root/dslv-zpdi/AGENTS.md` — this file (project conventions)
3. `/root/dslv-zpdi/MASTER_SPEC.md` — canonical architecture specification
4. `/root/dslv-zpdi/COLLABORATION_GUIDE.md` — branch/merge/commit rules
5. `/data/data/com.termux/files/home/PIXEL_DEV_PLAN.md` — current Pixel C2 node trajectory
6. `/root/dslv-zpdi/SECURITY.md` — security policy

## CURRENT MISSION

The active development track is the **Pixel 9 Pro XL Tier-2 C2 Control Node** feature:

- Native Android command dashboard (PWA now, APK later)
- Secure C2 control-plane backend
- Read-only HDF5 telemetry query adapter
- Local cluster network anchor via LocalOnlyHotspot
- Tier-2 metrology contribution continues in background

## SCOPE BOUNDARIES — NON-NEGOTIABLE

1. The Raspberry Pi 5 remains the canonical Tier-1 timing, SDR, and HDF5 authority.
2. The Pixel is the DEFAULT control plane but is NEVER required for the swarm to function.
3. Existing Layer-1, Layer-2, and Layer-3 metrology semantics must NOT change.
4. All new behavior must be additive and feature-flagged.
5. Main repo code changes must be minimal, reviewable, and justified.
6. Local Pixel-specific overlays live in `/root/dslv-zpdi-local/`, not in the main repo.

## SECURITY — ZERO EXCEPTIONS

1. NEVER commit secrets, credentials, tokens, or private keys.
2. NEVER store the GitHub PAT in `.env`. It lives in `/root/.config/dslv-zpdi/github_pat` (mode 600).
3. NEVER expose arbitrary command execution or remote shell endpoints.
4. C2 commands require Bearer auth, capability authorization, expiry, idempotency, and audit logging.
5. HDF5 access from the UI is read-only through a bounded query adapter.
6. The Android APK never receives GitHub tokens, agent credentials, or shell access.
7. Prefer Unix sockets / localhost over network ports when possible.

## WORKFLOW — FOLLOW EXACTLY

1. INSPECT before editing. State exact files you will change.
2. Produce a written design + test plan before writing code.
3. Work only in your assigned branch/worktree.
4. Source `/root/dslv-zpdi-local/scripts/start_dev_session.sh` before working.
5. Run `bash /root/dslv-zpdi-local/scripts/validate.sh` before and after changes.
6. Add tests for every new command and failure path.
7. Never merge, force-push, reset, or delete data without explicit approval.
8. Record unresolved assumptions instead of fabricating implementations.
9. Commit small, reviewable changes with Conventional Commits.
10. End each session with a turnover note: changed files, test results, known failures, security implications, next action.

## VALIDATION PIPELINE

Run in this order:

```bash
source /root/dslv-zpdi-local/scripts/start_dev_session.sh
bash /root/dslv-zpdi-local/scripts/validate.sh
```

This executes: `pip check`, `check_version_sync.py`, `orphan_checker.py`, `repo_guard.py`, `ruff check`, `mypy layer2_core`, `pytest tests/`, `git diff --check`.

## AGENT ROLES

- **Claude Code**: Lead architect / security reviewer. Owns multi-file design and threat modeling.
- **Codex CLI**: Terminal executor / engineer. Owns implementation and validation.
- **Kimi Code**: High-output craftsman. Owns boilerplate, refactors, and SPEC compliance.
- **Grok Build**: Edge-case analyst / prototyping. Owns failure-mode analysis and performance review.
- **Gemini CLI**: QA / test engineer. Owns test plans and final validation.

## FORBIDDEN ACTIONS

- Do not modify `/root/dslv-zpdi/.env` to add secrets.
- Do not run `git reset --hard`.
- Do not force-push to `main` or shared branches.
- Do not disable tests or reduce coverage floors.
- Do not add new dependencies without explicit approval.
- Do not expose services on `0.0.0.0` without security review.
- Do not write arbitrary shell execution into C2 endpoints.
- Do not make the Pixel the Tier-1 authority.

## COMMUNICATION

- Be concise. State what you did, what passed, and what is blocked.
- If a requirement conflicts with this doctrine, STOP and ask for clarification.
- Never claim hardware validation passed unless you ran the command and captured output.

---

## Project Purpose

DSLV-ZPDI is a SPEC-driven Python project for GPS-disciplined, multi-modal field
telemetry. The current Rev 5.0.0 codebase pivots Tier-1 RF ingestion to a
PlutoSDR+ class SDR with LBE-1421 timing evidence, a composed HAL, Kuramoto
coherence processing, and tamper-evident HDF5 persistence.

Read `CREW_MEMORY.md` before changing files. It contains the latest local
hardware notes and session state. Treat historical agent folders and archived
reports as context, not as current truth unless verified against the repo.

## Repository Structure

- `src/dslv_zpdi/` - package source.
- `src/dslv_zpdi/layer1_ingestion/` - HAL, SDR, timing, mobile/radon ingestion.
- `src/dslv_zpdi/layer2_core/` - coherence, baseline FSM, swarm integrity.
- `src/dslv_zpdi/layer3_telemetry/` - routing and HDF5/secondary persistence.
- `config/node_profiles/` - validated node profiles.
- `specs/` and `MASTER_SPEC.md` - canonical SPEC references.
- `tests/` - simulator and contract tests.
- `tools/` - repository guardrails, version checks, dashboard and utility tools.
- `docs/` - build, collaboration, audit, hardware, and validation notes.

Every new source module, class, and significant function must map to a real
SPEC-ID in its docstring. `tools/orphan_checker.py` enforces this contract.

## Development Environment

Supported Python policy is 3.10 through 3.14. Use Python 3.13 for local
development and lockfile regeneration unless a change specifically targets a
matrix version. The Docker image validates on Python 3.14.

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
```

Runtime pins in `requirements.txt` are generated from `pyproject.toml` with
Python 3.13. Development dependencies live in the `dev` optional dependency
group, not in `requirements.txt`.

## Hardware Profile

Verified local notes identify this current Tier-1 profile:

- Raspberry Pi 5 anchor.
- HamGeek PlutoSDR+ 1 GB / AD9363 at `ip:192.168.3.80`.
- Leo Bodnar LBE-1421 GPSDO.
- LBE-1421 10 MHz Out2 to PlutoSDR+ CLKIN.
- LBE-1421 1 PPS Out1 to Pi GPIO 24 (physical pin 18).
- Pixel 9 Pro XL GrapheneOS as the Tier-2 mobile node.

Do not mark physical hardware validation as passing unless it was actually run
against the node and the command output was recorded.

## Validation

Run the applicable local contract before committing:

```bash
.venv/bin/python -m pip check
.venv/bin/python tools/check_version_sync.py
.venv/bin/python tools/orphan_checker.py
.venv/bin/python tools/repo_guard.py
.venv/bin/python -m ruff check src/ tools/ tests/
.venv/bin/python -m mypy src/dslv_zpdi/layer2_core
DEV_SIMULATOR=1 .venv/bin/python -m pytest tests/ -q --cov --cov-report=term-missing
DEV_SIMULATOR=1 .venv/bin/python tests/test_pipeline.py
```

Format with Black if a file already requires formatting:

```bash
.venv/bin/python -m black src/ tools/ tests/
```

## Security Scanning

Use the configured GitHub security workflow for CodeQL. Local scans are useful
before larger changes:

```bash
.venv/bin/python -m pip_audit
.venv/bin/python -m bandit -q -r src tools
git diff --check
```

Security vulnerabilities and evidence-integrity issues must be reported through
private GitHub security advisories, not public issues.

## Docker

Build the default validation image:

```bash
docker build -t dslv-zpdi:local .
```

Multi-architecture CI builds `linux/amd64` and `linux/arm64`, generates SBOM and
provenance, scans an AMD64 image with Trivy, and publishes only from non-PR
events. Pull-request builds must not publish images.

## Release

Release tags must match `pyproject.toml` exactly, for example `v5.0.0`. The
release workflow builds a wheel and sdist, validates metadata with `twine`,
generates SHA-256 checksums, and attaches artifacts to the GitHub release.

## Git Conventions

Use Conventional Commits:

```text
type(optional-scope)!: concise summary
```

Allowed types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`,
`chore`, `revert`, and `security`.

Run this once in each clone so committed hooks are active:

```bash
git config core.hooksPath .githooks
```

Do not force-push, bypass branch protection, or commit unrelated generated
artifacts.

## Files That Must Not Be Committed

- `.env`, `.env.*`, `*.pat`, `*.token`, credential directories, or private keys.
- HDF5 captures and runtime data: `data/*.h5`, `data/*.hdf5`, `*.h5`, `*.hdf5`.
- Runtime outputs: `output/`, health files, PID files, logs, and caches.
- Virtual environments, build outputs, coverage outputs, and Docker scratch data.
- Exact private coordinates, credentials, serials, or personal data in issue logs.

## Definition of Done

- Source changes are scoped to the requested behavior.
- Simulator tests pass without physical hardware.
- Hardware-dependent claims are either validated on hardware or explicitly marked
  unavailable.
- Version, docs, requirements, workflows, and tests are consistent.
- Security-sensitive changes fail closed and preserve forensic secondary output.
- `git diff --check` is clean.
