# DSLV-ZPDI Collaborative Development Workspace

**Purpose:** Shared operating map for Gemini CLI, Claude Code, Kimi Code, and Codex CLI.
**Canonical repository:** `https://github.com/DynoGator/dslv-zpdi`
**Local canonical checkout on this machine:** `/home/dynogator/Desktop/DSLV-ZPDI_GitHub_Dev/dslv-zpdi`
**Active revision:** Rev 5.0.0

## Source of Truth

- `AGENTS.md` - agent behavior and project operating directives.
- `CONTRIBUTING.md` - mandatory SPEC-ID, testing, and commit protocol.
- `MASTER_SPEC.md` and `V3_DSLV-ZPDI_LIVING_MASTER.md` - canonical project law layer.
- `repo_manifest.yaml` - validation contract and repository guardrails.
- `docs/collaboration/NEXT_STEPS.md` - active forward development plan.
- Root `TURNOVER_YYYY-MM-DD_<topic>.md` files - session handoff notes.

Tool-specific historical folders such as `CLAUDE-HOME/` and `GEM-HOME/` are useful context, but they are not the source of truth for current development decisions.

## Session Start Protocol

Run these from the canonical checkout before changing files:

```bash
git fetch origin
git status --short --branch
git pull --ff-only --autostash origin main
```

If uncommitted work exists from another tool, preserve it before updating:

```bash
git stash push -u -m "<agent>-preserve-before-YYYY-MM-DD-update"
```

Record the stash name in the next turnover note. Do not overwrite another agent's dirty work.

## Local Development Environment

Each machine should build a local editable virtual environment:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Use `.venv/bin/python` for tests and tools. The supported Python range is 3.10
through 3.14; use 3.13 for normal local development. Avoid relying on a global
`python` executable or a globally installed `dslv_zpdi` package, because stale
imports can hide current checkout defects.

## Validation Contract

Run the full local contract before commit and push:

```bash
.venv/bin/python -m pip check
.venv/bin/python tools/check_version_sync.py
.venv/bin/python tools/orphan_checker.py
.venv/bin/python tools/repo_guard.py
.venv/bin/python -m ruff check src/ tools/ tests/
.venv/bin/python -m mypy src/dslv_zpdi/layer2_core
DEV_SIMULATOR=1 .venv/bin/python -m pytest tests/ -v
DEV_SIMULATOR=1 .venv/bin/python tests/test_pipeline.py
```

Use simulator mode for CI and laptop validation. Hardware-only checks belong in session notes unless they were actually run on the Tier 1 node.

## Turnover Notes

Create one root-level turnover file per substantial session:

```text
TURNOVER_YYYY-MM-DD_<ShortTopic>.md
```

Each turnover should include:

- Starting commit and ending commit if known.
- Machine or checkout used.
- Files changed and why.
- Validation commands and exact pass/fail result.
- Any preserved stash names.
- Next actionable work.

## Asset Locations

- `docs/build-guides/` - generated PDFs for field distribution. Markdown remains canonical.
- `docs/validation-logs/` - committed validation evidence snapshots.
- `config/*.example.*` and `config/*example*` - shareable configuration templates.
- `tools/dashboard/` - Rich TUI and web dashboard assets.
- `tools/mapping/` - HDF5 aggregation and map rendering tools.
- `output/`, `*.h5`, `*.hdf5`, `.venv/`, and caches are runtime artifacts and must not be committed.

## Git Hygiene

- Use Conventional Commits: `type(optional-scope)!: summary`.
- Keep one logical change per commit.
- Fetch before work, validate before commit, push after commit.
- Remove embedded credentials from local remotes. Use `https://github.com/DynoGator/dslv-zpdi.git` or SSH, never a token-bearing remote URL.
