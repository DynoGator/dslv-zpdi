# DSLV-ZPDI Continued Development Plan — Mobile + Merge Track

**Status date:** 2026-06-06
**Baseline:** Rev 3.5 mobile (Pixel Tier-2 live), Rev 4.7.2 on `origin/main` (Pi Tier-1)
**Blocker:** Kimi Code GitHub restructure/merge in progress — hold remote pushes until Joe approves

## Priority 0 — Repo Trustworthiness (Both Trees)

- Keep SPEC-IDs on all new functions/classes; run `python tools/orphan_checker.py`
- Keep `CHANGELOG.md` and `TURNOVER.md` APPEND-ONLY
- Never commit `.env`, HDF5 streams, or JSONL logs
- Fast-forward only after named stash preservation

## Priority 1 — Post-Merge Reconciliation (Kimi + Grok)

- Merge `origin/main` v4.7.2 package layout with mobile Tier-2 modules
- Unify transport: WSS (SPEC-008) + HTTP JSON → port 5775 → HDF5 on Pi anchor
- Port `tools/health_check.sh`, `repo_guard.py`, `check_version_sync.py` from main
- Resolve `src/` flat layout vs `src/dslv_zpdi/` package naming

## Priority 2 — Mobile Node Validation (Pixel)

- End-to-end: sensors → coherence → SECONDARY JSONL → WSS → Tier-1 server
- Confirm supervisor grace period + `.env` export (committed this session)
- Wire TheForge PWA proxy to `127.0.0.1:8000` (FastAPI) not remote Pi
- 72-hour passive baseline per SPEC-009 before threshold tuning

## Priority 3 — Tier-1 Anchor (Pi 5 — post-merge)

- LBE-1421 GPSDO + PPS chrony validation
- HackRF amp lockout enforcement (flag if bypassed in pipeline/dashboard)
- RadonEye staging remains SECONDARY until SPEC-015 ratified
- Node receiver contract tests on port 5775

## Priority 4 — Swarm & Kuramoto Tuning

- Multi-node `r_global` weighting with real secondary stream data
- `source_node` attribution across Pixel + Pi ingest paths
- Simulator compatibility: `DEV_SIMULATOR=1` on main tree CI

## Priority 5 — Field Operations

- Termux:Boot auto-start verification after reboot
- PiRepo hotspot telemetry path documentation
- Validation evidence → `docs/validation-logs/` (no secrets)