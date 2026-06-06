# KIMI Branch Audit — Phase 2B Pre-Consolidation

**Date:** 2026-06-05
**Agent:** KIMI_CODE_CLI
**Branch:** `phase-2b/radon-metrology-fusion` (based on `main` @ `5399333`)

---

## Branch Inventory

```
* main                                      current trunk, v4.7.1
  remotes/origin/feat/mobile-architecture-compliance   18 ahead, 4 behind
  remotes/origin/feat/mobile-node-hardening-phase2     22 ahead, 4 behind
  remotes/origin/hotfix/rev-3.3-document-consolidation  0 ahead, 5 behind
  remotes/origin/main-tier1-anchor                      0 ahead, 2 behind
  remotes/origin/release/v3.4-phase2a-prep              0 ahead, 5 behind
```

---

## Classification

### `feat/mobile-architecture-compliance` → **(d) AMBIGUOUS — PI decision required**

- **Ahead of main:** 18 commits (real, unmerged work: dual-stream router, CoherenceScorer, IngestionPayload hardening, mobile ingestion driver, FastAPI skeleton, SQLite WAL cache, log rotation, health watchdog, pre-commit hooks, supervisor)
- **Behind main:** 4 commits (v4.7.1 dashboard finalization, node bridging, Pixel integration, pyhackrf/chronyc fixes)
- **Structural problem:** This branch shares **ZERO common ancestors** with `main`. `git merge` fails with `fatal: refusing to merge unrelated histories`.
- **Directory incompatibility:** The branch uses a **flat package structure** (`src/layer1_ingestion/`, `src/layer2_core/`, `src/layer3_telemetry/`) while `main` uses a **proper Python package** (`src/dslv_zpdi/layer1_ingestion/`, etc.).
- **Supersession status:** Much of this branch's intent (node receiver, Tier-2 quarantine, mobile node bridging) has been **independently reimplemented** in `main` between v4.4.0 and v4.7.1 with a superior structure.
- **Unique code not in main:** `mobile_ingestion.py` (flat structure), `zpdi_mobile_node.py`, `zpdi_verifier.py`, `zpdi_web_server.py` (all at repo root).

**Recommendation:** Do **NOT** mechanically merge. The branch is from a pre-v4 repo epoch. Any unique algorithms worth keeping should be manually ported into the modern `src/dslv_zpdi/` package during Phase 2B if needed.

---

### `feat/mobile-node-hardening-phase2` → **(d) AMBIGUOUS — PI decision required**

- **Ahead of main:** 22 commits (superset of `feat/mobile-architecture-compliance` PLUS: Termux/PRoot edge node installer, Tier-1 crypto-ingestion server, orientation-fusion engine, AES-256-GCM/HMAC auth, circuit-breaker WSS, GPS poller, expanded vectoring sensors, Rev 3.5 README)
- **Behind main:** 4 commits
- **Structural problem:** Same unrelated-history + flat-package issue as above. This branch is a direct descendant of `feat/mobile-architecture-compliance`, not of `main`.
- **Unique code not in main:** `src/layer1_ingestion/gps_poller.py`, `src/layer2_core/fusion_engine.py`, `tier1_ingestion_server.py`, `install_zpdi_mobile.sh`, `termux-boot/99-start-zpdi.sh`, `tests/test_tier1_server.py`.

**Recommendation:** Same as above — do **NOT** mechanically merge. The `fusion_engine.py` and `gps_poller.py` modules contain algorithms that **may** be useful for Phase 2B Pixel bridge work, but they must be rewritten inside the `src/dslv_zpdi/` package tree with proper SPEC-IDs rather than imported verbatim.

---

### `hotfix/rev-3.3-document-consolidation` → **(b) ALREADY MERGED**

- **Ahead of main:** 0 commits
- **Behind main:** 5 commits
- **Last commit:** 2026-04-08 — "fix(docs): Rev 3.3 — clean canonical master, 7-test regression suite, hdf5_writer timestamp fix"
- **Verdict:** All changes absorbed into `main`. Safe to ignore/delete.

---

### `main-tier1-anchor` → **(b) ALREADY MERGED**

- **Ahead of main:** 0 commits
- **Behind main:** 2 commits
- **Last commit:** 2026-05-30 — "feat: integrate Pixel 9 Pro XL as live Tier 2 node (10.128.24.165)"
- **Verdict:** This commit (`d16eccd`) is already in `main`. The branch tip equals an ancestor of `main`. Safe to ignore/delete.

---

### `release/v3.4-phase2a-prep` → **(b) ALREADY MERGED**

- **Ahead of main:** 0 commits
- **Behind main:** 5 commits
- **Last commit:** 2026-04-08 — "feat(arch): Rev 3.4 — router class parity, 10-test suite, HDF5 schema, purged orphaned specs"
- **Verdict:** All changes absorbed into subsequent `main` releases. Safe to ignore/delete.

---

## Merge Protocol Executed

1. **Created feature branch:** `phase-2b/radon-metrology-fusion` from `main` (`5399333`).
2. **Attempted merge of `feat/mobile-architecture-compliance`:** Failed with `fatal: refusing to merge unrelated histories`.
3. **Attempted merge of `feat/mobile-node-hardening-phase2`:** Not attempted — same unrelated-history lineage.
4. **Paused and documented:** This audit file records the structural conflict. No code was lost or rewritten.

---

## Conflict Resolution

**Conflict type:** Intent-level architectural divergence, not text-level merge conflict.
- **Option A (mechanical merge with `--allow-unrelated-histories`):** Would create duplicate file trees (`src/layer1_ingestion/` vs `src/dslv_zpdi/layer1_ingestion/`), break the package import graph, and regress the CI/test infrastructure. **REJECTED.**
- **Option B (manual port of unique algorithms):** Keep the modern `main` structure intact. During Phase 2B, if `fusion_engine.py` or `gps_poller.py` algorithms are needed for the Pixel bridge, port them surgically into `src/dslv_zpdi/` with fresh SPEC-IDs. **RECOMMENDED.**
- **Option C (abandon mobile branch code entirely):** The `main` branch already has node_receiver, HAL factory, dashboard, and HDF5 multi-node aggregation. The mobile branches' core value is the Termux installer and the fusion/orientation algorithms. If those aren't needed for radon metrology, this code can stay on the stale branch. **ACCEPTABLE.**

**Chosen path for Phase 2B:** Option B with a fallback to Option C. I will not mechanically merge either mobile branch. I will port useful unique code only if the Phase 2B Pixel bridge design requires it.

---

## Final Consolidated State

| Branch | Action | Reason |
|--------|--------|--------|
| `main` | Base trunk | v4.7.1, 47 tests green |
| `phase-2b/radon-metrology-fusion` | Active feature branch | Created from `main` |
| `feat/mobile-architecture-compliance` | **Left untouched** | Unrelated history, flat package, superseded by main |
| `feat/mobile-node-hardening-phase2` | **Left untouched** | Same as above |
| `hotfix/rev-3.3-document-consolidation` | **Safe to delete** | Already merged |
| `main-tier1-anchor` | **Safe to delete** | Already merged |
| `release/v3.4-phase2a-prep` | **Safe to delete** | Already merged |

**No history was rewritten. No force-push occurred.**
