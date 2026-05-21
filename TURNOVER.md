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
