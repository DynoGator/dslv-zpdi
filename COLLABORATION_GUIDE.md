# DSLV-ZPDI Collaboration Guide

**Quick entry point for all AI collaborators and Joe Fross.**

Full protocol: [`docs/collaboration/README.md`](docs/collaboration/README.md)

## Start Here

1. Read `GROK_BUILD_MEMORY.md` (latest session state)
2. Read `TURNOVER.md` (append-only handoff log)
3. Activate environment: `source ~/GROK-HOME/scripts/activate.sh` or `source .venv/bin/activate`
4. `git fetch origin` — **hold push/merge until Joe confirms Kimi restructure complete**

## Validation (Mobile Pixel Node)

```bash
pytest tests/ -v
bash tools/health_check_mobile.sh
python tools/orphan_checker.py    # 29 class-level SPEC gaps flagged — see GROK_BUILD_MEMORY.md
ruff check zpdi_*.py src/ tests/
```

## Key Conventions

- **SPEC-IDs** in every class/function docstring (enforced on `main` v4.7.2)
- **Conventional commits:** `feat(scope): Rev X.X — description`
- **APPEND-ONLY:** `CHANGELOG.md`, `TURNOVER.md`
- **Never commit:** `.env`, `data/*.h5`, `logs/*.jsonl`, `*.pid`
- **Termux:** bind to `127.0.0.1` only; `termux-sensor` is singleton

## Agent Homes on This Device

| Path | Agent |
|------|-------|
| `/root/GROK-HOME` | Grok Build |
| `/root/KIMI-HOME` | Kimi Code |
| `/root/CLAUDE-CODE` | Claude Code |
| `/root/.gemini` | Gemini CLI |

## Active Plans

- [`docs/collaboration/NEXT_STEPS.md`](docs/collaboration/NEXT_STEPS.md)
- [`docs/collaboration/TURNOVER_TEMPLATE.md`](docs/collaboration/TURNOVER_TEMPLATE.md)