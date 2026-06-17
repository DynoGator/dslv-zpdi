# DSLV-ZPDI Agent Instructions

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
- LBE-1421 1 PPS Out1 to Pi GPIO 18.
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
