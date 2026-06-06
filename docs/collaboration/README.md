# DSLV-ZPDI Multi-Agent Collaboration Workspace

**Purpose:** Shared operating map for Grok Build, Kimi Code, Claude Code, Codex CLI, and Gemini CLI.
**Canonical repository:** https://github.com/DynoGator/dslv-zpdi
**This device checkout:** `/root/dslv-zpdi` (Pixel 9 Pro XL, GrapheneOS, Debian proot)
**Grok agent home:** `/root/GROK-HOME`
**Active mobile revision:** Rev 3.5 (Tier-2 swarm node)
**Upstream anchor revision:** Rev 4.7.2+ on `origin/main` (Pi 5 Tier-1 — merge in progress by Kimi Code)

## Dual-Tree Awareness (Critical)

Two architectures coexist until Kimi Code completes the GitHub restructure:

| Tree | Branch | Layout | Role |
|------|--------|--------|------|
| `/root/dslv-zpdi` | `mobile-node-rev35` | Flat `src/` + top-level daemons | **Live Pixel Tier-2 node** |
| `origin/main` | `main` | `src/dslv_zpdi/` package | **Pi 5 Tier-1 anchor v4.7.2** |
| `/root/CLAUDE-CODE/dslv-zpdi` | local mirror | v4.7.x reference | Spec docs, tools templates |
| `/root/KIMI-HOME` | feature branch copy | mobile layout | Kimi parallel checkout |

**Do not force-merge `main` into mobile without Joe's approval.** Fetch first; record stash names before rebasing.

## Source of Truth

- `MASTER_SPEC.md` / `V3_DSLV-ZPDI_LIVING_MASTER.md` — canonical law (on `main`; symlinked in `GROK-HOME/refs/`)
- `CONTRIBUTING.md`, `AGENTS.md` — agent behavior and commit protocol
- `AUDIT_VIOLATIONS.md` — mobile compliance baseline
- `TURNOVER.md` — APPEND-ONLY session handoffs
- `GROK_BUILD_MEMORY.md` — Grok Build persistent session state
- `docs/collaboration/NEXT_STEPS.md` — active forward plan

Tool-specific homes (`GROK-HOME/`, `KIMI-HOME/`, `CLAUDE-CODE/`) are context, not canonical law.

## Session Start Protocol

```bash
# Termux: enter proot first
proot-distro login debian

cd /root/dslv-zpdi
source .venv/bin/activate
# or: source ~/GROK-HOME/scripts/activate.sh

git fetch origin
git status --short --branch
```

**Hold `git push` and branch merges until Joe confirms Kimi restructure is complete.**

Preserve dirty work before updating:

```bash
git stash push -u -m "<agent>-preserve-$(date +%Y%m%d)"
```

## Mobile Validation Contract

```bash
source .venv/bin/activate
pytest tests/ -v                           # 42 tests (41 pass + 1 skip if daemon running)
bash tools/health_check_mobile.sh        # Tier-2 operational snapshot
python tools/orphan_checker.py           # SPEC-ID compliance (src/ + specs/)
ruff check zpdi_*.py src/ tests/         # lint (ruff in .venv)
```

**Tier-1 Pi validation** (HackRF, chrony PPS, RadonEye) runs on Pi 5 only via `tools/health_check.sh` on `main` — not applicable on Pixel.

## Mobile-Specific Caveats

1. **proot `--kill-on-exit`** — daemon must run under persistent proot (`supervisor.sh` foreground)
2. **`termux-sensor` singleton** — only one streaming consumer; stop daemon before live integration tests
3. **Bind web services to `127.0.0.1`** — `0.0.0.0` causes Android Error 13
4. **Tier-2 quarantine** — all packets → `SECONDARY`; PRIMARY HDF5 must not grow
5. **WSS transport** — mobile → Tier-1 via `tier1_ingestion_server.py` (SPEC-008) or Pi receiver port 5775 (post-merge)
6. **PiRepo hotspot** — Pi anchor at `10.42.0.1:5775/api/v1/ingest` when field-deployed

## Turnover Protocol

Append to `TURNOVER.md` or create `TURNOVER_YYYY-MM-DD_<Topic>.md` using `docs/collaboration/TURNOVER_TEMPLATE.md`.

Each handoff must include: agent name, branch, commits, validation results, stashes, next actions.

## Git Hygiene

- Conventional commits: `<type>(<scope>): Rev <version> — <description>`
- pre-commit blocks: `.env`, `data/*.h5`, `logs/*.jsonl`, `*.pid`
- pre-push requires `GITHUB_PAT` via `./configure_git_auth.sh`
- Never embed tokens in remote URLs

## Agent Roles (Suggested)

| Agent | Primary focus |
|-------|---------------|
| **Grok Build** | Mobile pipeline, PWA wiring, local validation, collaboration docs |
| **Kimi Code** | GitHub restructure, branch merges, spec alignment |
| **Claude Code** | Tier-1 anchor hardening, v4.7.x package, dashboard |
| **Codex CLI** | Validation contracts, CI, repo guard |
| **Gemini CLI** | Web stack, FastAPI ↔ Vite bridge |
| **Joe Fross** | Hardware procurement, credentials, merge approval |