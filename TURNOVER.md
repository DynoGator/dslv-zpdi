# Shift Turnover — dslv-zpdi Tier-1 Mobile Node

**APPEND-ONLY** — new entries added at bottom. Existing entries never modified.

---

## TURNOVER — 2026-05-21 (Audit & Hardening: Auto-Start + Daemon Supervisor)

**Date:** 2026-05-21
**Performed by:** Claude Code (claude-sonnet-4-6) on behalf of J.R. Fross

### What Was Found

**1. Auto-start root cause (FIXED)**
The `99-start-zpdi.sh` Termux:Boot script was running:
```
proot-distro login debian -- bash /root/dslv-zpdi/launch_daemon.sh
```
`launch_daemon.sh` backgrounded the daemon with `nohup` and exited. proot was compiled
with `--kill-on-exit`, which sends SIGKILL to all ptrace'd children when the proot process
exits. The daemon was killed the moment `launch_daemon.sh` completed.

Confirmed via `/proc/8864/status` → `TracerPid: 7654` (current interactive proot session,
NOT a boot proot). The running daemon was started manually from the interactive session.

**2. No crash supervisor (FIXED)**
If the daemon exited for any reason, nothing restarted it. `launch_daemon.sh` was a
single-shot launcher with no restart logic.

**3. Untracked launch scripts (FIXED)**
`launch_daemon.sh` and `run_node.sh` were not committed to the repository. A fresh clone
would not have them, and the boot script would fail silently.

**4. Git hooks not implemented (FIXED)**
`.githooks/README.md` reserved `pre-commit` and `pre-push` but both were empty.

**5. `DynoGater` typo (FIXED)**
`.env` and `configure_git_auth.sh` both referenced `DynoGater/dslv-zpdi` (wrong) instead
of `DynoGator/dslv-zpdi` (correct). The `.git/config` remote URL was already correct.

**6. Deprecated h5py API (FIXED)**
`zpdi_mobile_node.py` used `h5py.special_dtype(vlen=bytes)` (deprecated since h5py 3.0).
Replaced with `h5py.vlen_dtype(bytes)`. No behavioral change — existing HDF5 files are
compatible (the dtype only applies on dataset creation).

### What Was Done

- Created `supervisor.sh`: foreground supervisor loop inside proot; restarts daemon with
  exponential back-off (2s → 4 → 8 → … → 60s cap).
- Rewrote `launch_daemon.sh`: starts an **independent** proot session for the supervisor
  (`nohup proot-distro login debian -- bash supervisor.sh`). Session stays alive as long
  as supervisor runs; daemon restarts work because proot is present.
- Updated `99-start-zpdi.sh` (Termux:Boot): same independent-proot pattern; supervisor
  is the foreground process, `nohup + &` backgrounds the whole proot at boot.
- Committed `run_node.sh` and `launch_daemon.sh` (previously untracked).
- Implemented `.githooks/pre-commit` and `.githooks/pre-push`.
- Added `CHANGELOG.md` and this `TURNOVER.md`.

### Current State

| Component | Status |
|---|---|
| Daemon (pid 8864) | Running — started from interactive session; collecting data |
| HDF5 stream | Active — `data/zpdi_stream.h5` growing |
| WSS transport | Fallback mode (placeholder URI); `logs/zpdi_fallback.jsonl` accumulating |
| Supervisor | Not yet active — takes effect on next reboot or manual `./launch_daemon.sh` |
| Git hooks | Active — pre-commit and pre-push both installed and executable |

### Next Actions at Handoff

1. **Activate supervisor now (optional):** From Termux or inside proot, run
   `bash /root/dslv-zpdi/launch_daemon.sh` to migrate the running daemon to the supervised
   proot session. This will briefly interrupt data collection (~2s for SIGTERM + restart).
2. **Configure WSS endpoint:** When a real edge server is available, set `ZPDI_WSS_URI` in
   `.env` and restart. Until then, all data routes to `logs/zpdi_fallback.jsonl`.
3. **Rotate fallback log:** `zpdi_fallback.jsonl` is 1MB+ after ~8h; consider adding log
   rotation or periodic archive once WSS is live (at which point the fallback stays small).
4. **Phase 2A hardware:** Per Living Master Rev 3.3, next milestone is Intel i210-T1 NIC
   procurement for CM5 Tier-2 nodes. This Tier-1 mobile node continues collecting
   baseline data in the meantime.

---

*(Future turnovers appended below this line)*

## TURNOVER — 2026-05-21 (Audit Phase 2: Web Transition & Node Hardening)

**Date:** 2026-05-21
**Performed by:** Gemini CLI (Auto-Edit Mode)

### Completed Fixes (Phases 1-3)

**1. WebSocket State & Queue Robustness**
- Switched `zpdi_mobile_node.py` to use `websockets.protocol.State` enum for connection checks.
- Hardened the "drop-oldest" queue logic in the node's main loop to prevent race conditions during heavy fan-out.

**2. Security & Integrity**
- Modified `configure_git_auth.sh` to use a dynamic credential helper. GITHUB_PAT is no longer stored in `.git/config` in plaintext; it is now read from `.env` at runtime by the git helper process.
- Added message type validation to `edge_listener_stub.py` to handle non-canonical payloads gracefully.

**3. Web Server Transition (FastAPI Skeleton)**
- Implemented `zpdi_web_server.py`: A FastAPI backend that acts as the bridge between the metrology daemon and the upcoming `TheForge_PWA` (Vite) frontend.
- Added a **Lightweight Query Cache**: The mobile node now maintains a single-row SQLite WAL database (`./data/zpdi_cache.db`). This allows the web server to poll the latest state without hitting the global HDF5 lock or competing for HDF5 SWMR resources.
- Created `README_WEB.md` documenting the critical Termux network interface constraint (Error 13).

### Instructions for Next Developer

**1. Bridging FastAPI to Vite**
- The FastAPI server runs on `127.0.0.1:8000` by default.
- Use `GET /latest` for one-shot status updates.
- Use `WS /ws/live` for real-time sensor visualization in the PWA.
- **Important:** Vite **must** be run with `--host 127.0.0.1` to avoid Android permission errors.

**2. Scaling the Cache**
- The current `SQLiteCache` only stores the *latest* sample. If the frontend requires a historical "sparkline" or windowed view, expand the `latest_state` table to a circular buffer or use the `ZPDI_MAX_QUERY_WINDOW_S` parameter to query a time-range from SQLite (though HDF5 remains the primary archive).

**3. Testing the Web Stack**
- Start the node: `./run_node.sh`
- Start the web server: `python3 zpdi_web_server.py` (ensure `.env` is populated)
- Verify via `curl http://127.0.0.1:8000/health`


## TURNOVER — 2026-05-21 (Mobile Node Architecture Compliance — SPEC-005/006/007)

**Date:** 2026-05-21
**Performed by:** Kimi Code CLI (k2.6) on behalf of J.R. Fross
**Session directive:** Bring `main` branch into three-layer architecture compliance without breaking the running daemon.

### What Was Found

**1. SPEC Violations on `main` (pre-compliance)**
- `zpdi_mobile_node.py` was a flat-file monolith with no `IngestionPayload`, no trust-state machine, no coherence engine, and no dual-stream router.
- All sensor data was dumped into a single HDF5 file — a **SPEC-003 total pipeline kill condition** because Tier-2 mobile data was commingled with primary-stream semantics.
- Node self-identified as `"dslv-zpdi/tier1"` despite having no PPS, no GPSDO, and no hardware clock.
- `AUDIT_VIOLATIONS.md` was produced documenting every kill condition currently violated.

### What Was Done

**STEP 1 — Audit & Violation Baseline**
- Produced `AUDIT_VIOLATIONS.md` comparing `zpdi_mobile_node.py`, `zpdi_verifier.py`, and `edge_listener_stub.py` against `V3_DSLV-ZPDI_LIVING_MASTER.md` Rev 4.3.0.
- Committed: `docs(audit): SPEC violation baseline for mobile node`

**STEP 2 — Canonical `src/` Structure**
- Ported `src/layer1_ingestion/`, `src/layer2_core/`, `src/layer3_telemetry/` package structure from commit `3a32be4`.
- Created `mobile_ingestion.py` with exact Pixel 9 Pro XL sensor names (`ICM45631 Accelerometer`, `MMC5616 Magnetometer`, `ICP20100 Pressure Sensor`) and numpy-based Hilbert transform for Layer 1 phase extraction.
- Committed: `feat(layer1): port canonical src/ structure and add mobile ingestion driver`

**STEP 3 — Hardened `IngestionPayload` & Trust-State Machine**
- Implemented full `IngestionPayload` dataclass per SPEC-005A.1b with all mandatory fields (`spec_id`, `schema_version`, `payload_uuid`, `hardware_tier=2`, `pps_jitter_ns=inf`, etc.).
- `validate()` returns `(trust_state, reason)`: structural corruption → `KILLED`; GPS/PPS failure → `SECONDARY_QUARANTINED`; valid → `ASSEMBLED`.
- `to_json()` embeds truncated SHA-256 checksum and blocks `KILLED` packets from serialization.
- Committed: `feat(layer1): hardened IngestionPayload with trust-state validation per SPEC-005A`

**STEP 4 — Refactored Mobile Daemon**
- Replaced ad-hoc `_build_payload()` with `build_mobile_payload()` + `_ingestion_to_legacy()` backward-compat wrapper.
- `_consume_stream` now produces one `IngestionPayload` per sensor (3× throughput vs one bundled dict).
- Live smoke test confirmed daemon starts and streams without crash.
- Committed: `refactor(node): integrate IngestionPayload into mobile daemon stream`

**STEP 5 — Layer 2 Coherence Engine**
- Ported `coherence.py` with `CoherenceScorer` implementing Kuramoto `r_local`, EWMA `r_smooth`, and fleet-weighted `r_global` per SPEC-006.
- Ported `wiring.py` with canonical `wire_to_coherence()` and mobile-specific `wire_mobile_to_coherence()`.
- `score_mobile_payload()` helper feeds pre-extracted phases from Layer 1 directly into the scorer.
- Committed: `feat(layer2): port CoherenceScorer and wiring per SPEC-006`

**STEP 6 — Dual-Stream Router (SPEC-007)**
- Created `mobile_router.py` with `route_packet()` enforcing:
  - `hardware_tier=2` → **always** `SECONDARY_QUARANTINED`
  - `r_smooth >= 0.40` → reason `anomalous_candidate_tier2`
  - `0.15 <= r_smooth < 0.40` → reason `structured_background_tier2`
  - `r_smooth < 0.15` → reason `noise_tier2`
- `HDF5Sink.append()` now rejects any packet where `route["stream"] != "PRIMARY"`. Mobile primary dataset is intentionally empty.
- `_transport_consumer` writes every packet to `SecondaryLog` (JSONL) before attempting WSS.
- Committed: `feat(layer3): dual-stream router enforcing Tier-2 quarantine per SPEC-007`

**STEP 7 — Test Suite & Live Validation**
- Ported 7-test regression suite and added 7 mobile-specific tests (14 total).
- All tests pass: `pytest tests/ -v` → **14/14 passed**.
- Live 60-second run verified:
  - `data/zpdi_stream.h5`: **zero new rows** (correct for Tier-2)
  - `logs/zpdi_fallback.jsonl`: new rows, all `trust_state=SECONDARY_QUARANTINED`, `hardware_tier=2`, quarantine reason present
  - `zpdi_verifier.py`: **PASS** on existing HDF5 (100% integrity)
- Committed: `test(integration): mobile node dual-stream validation suite`

**STEP 8 — Operational Hardening**
- Added 10 MB log rotation with gzip to `SecondaryLog` (keeps 5 backups).
- Added `_health_watchdog` writing `logs/health.jsonl` every 30s with PID, sensor liveness, queue depths, and WSS connection state.
- Updated `supervisor.sh` to poll health log age; if stale > 90s, sends SIGTERM → SIGKILL and restarts.
- Committed: `feat(ops): log rotation and health watchdog for mobile node`

**STEP 9 — Documentation**
- Updated `CHANGELOG.md` with all conventional commits under `[Unreleased]`.
- Updated `README.md` with Tier-2 Swarm disclaimer and new `src/` layout.
- Updated `TURNOVER.md` with this handoff entry.
- Committed: `docs(turnover): append session log and update canonical docs`

### Current State

| Component | Status |
|---|---|
| Daemon | Stopped (was running for live validation; safe to restart via `./launch_daemon.sh`) |
| Primary HDF5 | Empty for new data (correct for Tier-2); retains ~21k historical pre-compliance rows |
| Secondary JSONL | Active; `logs/zpdi_fallback.jsonl` ≈ 10.9 MB |
| Tests | **14/14 passing** |
| Health watchdog | Writes to `logs/health.jsonl` every 30s when daemon is running |
| Supervisor | Monitors health staleness (>90s triggers restart) |
| Git | `main` ahead of `origin/main` by 14 commits |

### Next Actions for Next Developer

1. **Restart daemon if needed:** `./launch_daemon.sh` (supervisor will keep it alive and monitor health).
2. **Configure WSS endpoint:** When a real edge server is available, set `ZPDI_WSS_URI` in `.env`. Until then, all data routes to `logs/zpdi_fallback.jsonl`.
3. **Verify health log:** After restart, confirm `logs/health.jsonl` is being updated every 30s and supervisor log shows no forced restarts.
4. **Field calibration (SPEC-009):** If deploying this mobile node as part of a swarm, run 72-hour passive listening to build adaptive baselines before using `r_smooth` thresholds for vectoring.
5. **Tier-1 procurement:** Per SPEC-004A.2, institutional-grade primary output requires Raspberry Pi 5/CM5 + HackRF One + Leo Bodnar LBE-1421 GPSDO (or equivalent with external 10 MHz CLKIN + 1 PPS GPIO).

---

*(Future turnovers appended below this line)*
