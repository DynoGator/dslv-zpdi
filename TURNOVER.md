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
