# TURNOVER — 2026-06-19 — Dashboard Fix + Reboot Prep

**Session:** Claude (Sonnet 4.6) — continuation of MobileSync session
**Machine:** Pixel 9 Pro XL / GrapheneOS / PRoot Debian
**Checkout:** `/root/dslv-zpdi`
**Start commit:** `3ddf299` (docs mobile documentation pass)
**End commit:** see below after final push

---

## What Was Done

### 1. Dashboard `telemetry_nodes` fix
- **Root cause:** `tier1_ingestion_server.py` was writing accepted packets to
  `logs/tier1_secondary.jsonl` but the Flask dashboard reads node presence from
  `output/secondary/node_registry.jsonl`. These paths were never connected.
- **Fix:** Added `_register_node_seen(node_id: str)` to `tier1_ingestion_server.py`
  and called it after every `ACCEPTED` log line in `_process_message()`.
  - Throttled to once per 30 s per node to avoid constant disk I/O.
  - Writes `output/secondary/node_registry.jsonl` in the format the webdash expects.
- **Commit:** `f286942` — pushed to `origin/main`.
- **Verified:** `curl http://127.0.0.1:8080/api/status` → `telemetry_nodes: [{node_id: "dslv-zpdi/mobile-tier2", online: true, last_seen_s: ~15}]`

### 2. Branch / issue / test audit
- Only `main` branch exists — nothing to merge.
- 0 open GitHub issues, 0 open PRs.
- Test suite: **184 passed, 1 skipped** (66 s).

### 3. Boot survival confirmed
- `~/.termux/boot/99-start-zpdi.sh` is in place and correct.
- It launches `supervisor.sh` inside proot-distro debian as a background foreground process.
- `supervisor.sh` starts all three services and watchdogs them:
  - `tier1_ingestion_server.py` → ws://127.0.0.1:8443
  - `zpdi_mobile_node.py` → sensor daemon
  - `tools/dashboard/web_server.py` → http://0.0.0.0:8080
- Dashboard service was already included in supervisor since the MobileSync session; no changes needed.

### 4. Pre-reboot state
- All services gracefully running at time of reboot prep.
- Repo fully pushed; `git status` clean; `origin/main` == `HEAD`.
- `.env` on disk at `/root/dslv-zpdi/.env` — survives reboot (filesystem persists in PRoot).
- `output/secondary/node_registry.jsonl` — runtime artifact, will be repopulated within 30 s of first accepted packet after boot.

---

## Services Running Before Reboot

| Process | PID | Port |
|---|---|---|
| `tier1_ingestion_server.py` | 7254 | :8443 |
| `supervisor.sh` | 10627 | — |
| `zpdi_mobile_node.py` | 10643 | — |
| `web_server.py` (Flask dashboard) | 16255 | :8080 |

---

## Post-Reboot Checklist

After the device restarts, Termux:Boot should auto-start everything within ~60 s. To verify:

```bash
# In Termux (outside proot):
proot-distro login debian -- bash -c "ps aux | grep python3 | grep -v grep"

# Or inside proot:
curl -s http://127.0.0.1:8080/api/status | python3 -m json.tool
```

Expected: `telemetry_nodes[0].online == true` within ~30 s of first accepted packet.

If services did not start:
```bash
cat ~/.termux/boot/zpdi-boot.log         # boot event log
cat /root/dslv-zpdi/logs/supervisor.log  # supervisor start log
cat /root/dslv-zpdi/logs/daemon.log      # mobile daemon log
```

---

## Next Actions

- GPS lock will enable KCET-ATLAS LOCKED state and PRIMARY stream routing.
- PlutoSDR+ integration on Tier-1 Pi node (see TURNOVER_PENDING_HARDWARE_2026-06-15.md).
- Consider adding `ZPDI_WSS_TOKEN` and `ZPDI_HMAC_SECRET` to `.env` to enable
  the auth/HMAC pipeline (currently both are blank / disabled).
