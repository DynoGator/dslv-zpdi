# GROK_BUILD_MEMORY — Persistent Session State

**Agent:** Grok Build (xAI)
**Operator:** Joseph R. Fross
**Last updated:** 2026-06-06T01:15:00Z
**Device:** Pixel 9 Pro XL, GrapheneOS, Debian proot (aarch64)
**Agent home:** `/root/GROK-HOME`

> Read this file first on every Grok Build startup. Append session log at bottom; never delete prior entries.

---

## Current Git State

| Field | Value |
|-------|-------|
| Canonical checkout | `/root/dslv-zpdi` |
| Branch | `mobile-node-rev35` |
| Tracks | `origin/feat/mobile-node-hardening-phase2` |
| Local HEAD | `29613bc` (synced with remote feature branch) |
| `origin/main` | `d8a4f89` — Rev 4.7.2 (Kimi merge target, **95 commits ahead of local main**) |
| Open PRs | None |
| **Merge status** | **IN PROGRESS** — Kimi Code restructuring GitHub; **hold push to main** |

### Uncommitted at session start (now staged/committed this session)
- `supervisor.sh` — `.env` export, health log truncate, 35s grace period
- `tests/test_mobile_compliance.py` — daemon-aware skip for termux-sensor singleton
- Ruff auto-fixes (11 issues) across `zpdi_*.py`, `src/`, `tests/`
- New: `tools/`, `docs/collaboration/`, `specs/`, `COLLABORATION_GUIDE.md`, this file

---

## Operational Snapshot (2026-06-06)

| Service | Status |
|---------|--------|
| `supervisor.sh` | Running |
| `zpdi_mobile_node.py` | Running, sensors alive |
| `tier1_ingestion_server.py` | Running :8443, WSS connected |
| `zpdi_web_server.py` | Running :8000 |
| GPS | Active (~38.41°N, 105.00°W) |
| Tests | **41 passed, 1 skipped** (daemon holds sensor singleton) |
| Ruff | **All checks passed** (after fix) |
| `health_check_mobile.sh` | Available — run after reboot |

---

## Mobile Pipeline Caveats

1. **Tier-2 only** — all packets `SECONDARY_QUARANTINED`; PRIMARY HDF5 must not grow
2. **Historical HDF5** — ~21k pre-compliance rows in `data/zpdi_stream.h5` (archive TBD)
3. **termux-sensor singleton** — stop daemon before live integration test
4. **proot `--kill-on-exit`** — supervisor must stay foreground in proot session
5. **Web bind** — `127.0.0.1` only (Android Error 13 on `0.0.0.0`)
6. **Transport paths:**
   - Local WSS: `ws://127.0.0.1:8443/ingest` (SPEC-008, active)
   - Pi anchor (post-merge): `http://10.42.0.1:5775/api/v1/ingest` (JSON → HDF5)

---

## Tooling Alignment

| Tool | Location | Status |
|------|----------|--------|
| Python venv | `dslv-zpdi/.venv` | Active, ruff installed |
| Grok venv | `GROK-HOME/.venv` | ruff, pytest, httpx |
| Git hooks | `.githooks/` | pre-commit + pre-push active |
| Git auth | `configure_git_auth.sh` | PAT via credential helper |
| orphan_checker | `tools/orphan_checker.py` | **29 class-level SPEC gaps** — post-merge backfill |
| health_check_mobile | `tools/health_check_mobile.sh` | Tier-2 mobile validator |
| health_check (Tier-1) | on `main` only | HackRF/chrony/PPS — Pi 5 |
| patch_docs.py | on `main` only | MASTER_SPEC sync utility |

### orphan_checker known gaps (post-merge task)
Missing SPEC-ID on classes in: `gps_poller.py`, `payload.py`, `mobile_ingestion.py`, `fusion_engine.py`, `coherence.py`, `mobile_router.py`. Module-level docstrings exist; class-level backfill needed before strict CI on mobile branch.

---

## Hardware Readiness Notes

| Component | Tier | Status |
|-----------|------|--------|
| Pixel 9 Pro XL sensors | Tier-2 | **Live** — ICM45631, MMC5616, ICP20100, gyro, rotation, gravity |
| LBE-1421 GPSDO | Tier-1 | Procurement per Phase 2A — not on Pixel |
| HackRF One + amp lockout | Tier-1 | Pi 5 only — verify on anchor post-merge |
| chrony PPS | Tier-1 | `/dev/pps0` absent on Pixel (expected) |
| RadonEye Pro | Tier-1 | SPEC-015 staging only — not promoted to primary |
| Pi 5 anchor | Tier-1 | `origin/main` v4.7.2 — node receiver port 5775 |
| PiRepo hotspot | Field | `10.42.0.1` gateway for swarm telemetry |

---

## Open Tasks

- [ ] Wait for Kimi merge completion → Joe green-lights push
- [ ] Reconcile `src/` flat layout with `src/dslv_zpdi/` package on main
- [ ] Backfill 29 class-level SPEC-IDs (orphan_checker clean pass)
- [ ] Wire TheForge PWA → `127.0.0.1:8000`
- [ ] SPEC-009 72-hour passive baseline capture
- [ ] Kuramoto tuning with real secondary stream data
- [ ] Resolve historical HDF5 archive semantics
- [ ] Port `repo_guard.py`, `check_version_sync.py` from main post-merge

---

## Flagged Issues (Failure-Mode Awareness)

| Issue | Severity | Notes |
|-------|----------|-------|
| WSS circuit breaker | Mitigated | Tier-1 server must run for WSS; fallback JSONL always available |
| Supervisor stale-health kill | Mitigated | 35s grace + health log truncate on restart |
| HackRF amp | N/A mobile | Tier-1 Pi concern — check `main` pipeline lockout |
| chrony PPS jitter | N/A mobile | Tier-1 only; mobile has `pps_jitter_ns=inf` |
| RadonEye staging | Open | SPEC-015 not ratified; endpoint secondary-only on Pi |
| Multi-tree drift | Active | 4 parallel checkouts — canonical pointer TBD post-merge |

---

## Next Milestones (Post-Restructure)

1. **Merge landing** — identify canonical branch + layout from Kimi
2. **Full mobile validation** — 42/42 tests with daemon stopped; WSS + HTTP 5775 paths
3. **Kuramoto tuning** — real `r_smooth` distributions from secondary JSONL
4. **Swarm scaling** — Pixel + Pi `source_node` attribution, `r_global` weighting
5. **Field calibration** — SPEC-009 baseline FSM, 72h passive listen
6. **TheForge live dashboard** — PWA + FastAPI on-device

---

## Resume Commands (Post-Reboot)

```bash
# 1. Termux → proot
proot-distro login debian

# 2. Activate
source ~/GROK-HOME/scripts/activate.sh

# 3. Verify stack (supervisor auto-starts via Termux:Boot)
bash ~/GROK-HOME/scripts/dev-status.sh
bash tools/health_check_mobile.sh

# 4. Start optional services if not running
source .venv/bin/activate && set -a && source .env && set +a
python3 tier1_ingestion_server.py >> logs/tier1_server.log 2>&1 &
python3 zpdi_web_server.py >> logs/web_server.log 2>&1 &

# 5. Run tests (stop daemon first for 42/42)
pytest tests/ -v
```

---

## Session Log (APPEND-ONLY)

### 2026-06-06 — Workspace Maximization & Shutdown Prep (Grok Build)
- Fetched `origin/main` d8a4f89 (Rev 4.7.2); mobile branch unchanged at 29613bc
- Ported Kimi collab docs from main; created mobile-adapted `docs/collaboration/`
- Added `tools/health_check_mobile.sh`, `tools/orphan_checker.py`, `specs/` stubs
- Ruff clean; 41/41+1skip tests pass; ruff installed in project `.venv`
- Started Tier-1 + web servers; WSS reconnected
- Created `COLLABORATION_GUIDE.md`, `GROK_BUILD_MEMORY.md`
- Committed session optimizations to feature branch (see git log)
- **READY_FOR_REBOOT**