# DSLV-ZPDI Tier-1 Node — Turnover Notes for Collaborators

**Node hostname:** `raspberrypi`  
**Hardware:** Raspberry Pi 5 16 GB, PWM active cooler  
**Location:** `/home/dynogator/dslv-zpdi`  
**Profile:** `config/node_profiles/tier1_pluto_lbe1421.yaml`  
**Project version:** Rev 5.0.0  
**Turnover date:** 2026-07-09  

## 1. What This Node Does

This is a Tier-1 RF-metrology anchor node for the DSLV-ZPDI project. It:

- Disciplines its clock to a Leo Bodnar LBE-1421 GPSDO (1 PPS on GPIO 8).
- Uses the GPSDO 10 MHz output to externally reference a PlutoSDR+ (AD9363 REV5).
- Captures IQ data, runs a coherence scorer, and routes events to a SHA-256/HMAC-secured HDF5 pipeline.
- Publishes live telemetry to a web dashboard on port 8080 and a Rich TUI dashboard on the touchscreen.
- Monitors an X-1202 UPS HAT and gracefully shuts down on sustained battery loss.

## 2. Access

### Local login

- User: `dynogator`
- Home: `/home/dynogator`
- The Pi auto-logs into the labwc Wayland session and starts the dashboard.

### GitHub credentials (project use only)

Stored in `.secrets/` (mode `0600`, ignored by git):

```text
/home/dynogator/dslv-zpdi/.secrets/github-account.txt
/home/dynogator/dslv-zpdi/.secrets/git-credentials
```

To activate git authentication on a fresh clone, run:

```bash
./configure_git_auth.sh
```

This reads `GITHUB_PAT` from `.env` and configures a repo-scoped credential helper.

## 3. Service Chain

All services are enabled and managed by systemd:

| Service | Purpose | Managed by boot orchestrator |
|---------|---------|------------------------------|
| `dslv-zpdi-tuning.service` | CPU governor `performance`, USB power tuning | yes |
| `dslv-zpdi-preflight.service` | Hardware preflight checks | yes |
| `chrony.service` | PPS clock discipline to Stratum 1 | no (verified) |
| `gpsd.service` | LBE-1421 NMEA feed | no (verified) |
| `dslv-zpdi.service` | Main production pipeline | yes |
| `dslv-zpdi-ups.service` | X-1202 UPS monitor / shutdown | yes |
| `dslv-zpdi-webdash.service` | Flask web dashboard on `:8080` | yes |

Useful commands:

```bash
# Status of the whole chain
systemctl status dslv-zpdi-tuning dslv-zpdi-preflight dslv-zpdi \
               dslv-zpdi-ups dslv-zpdi-webdash chrony gpsd

# Follow the main pipeline log
sudo journalctl -u dslv-zpdi -f

# Restart the pipeline (avoid unless necessary; baseline learning is now persistent)
sudo systemctl restart dslv-zpdi

# Check timing discipline
chronyc tracking
```

## 4. Dashboards

- **Web dashboard:** `http://<pi-ip>:8080/` — system, pipeline, SDR, UPS, and node registry; auto-refreshes every 5 s.
- **TUI dashboard:** launched by `tools/boot_orchestrator.py` on graphical login; manual run with `tools/dashboard/launch.sh --compact`.
- **Boot orchestrator:** `tools/boot_orchestrator.py` (use `--no-start` for verify-only mode, `--no-dashboard` to skip TUI launch).

## 5. Current Node State

- `chrony` reports **Stratum 1**, disciplined to `/dev/pps0`.
- PlutoSDR+ is reachable at `ip:192.168.2.1` and reports `clock_src: external`.
- UPS is healthy, battery ~97%, AC present.
- Baseline is **LOCKED** and PRIMARY HDF5 output is active.
- The node is configured for **mono-node development mode**:
  - `DSLV_MIN_CONFIRMING_NODES=1`
  - `DSLV_BASELINE_FIXED_THRESHOLD=0.30`
  - `DSLV_BASELINE_HOURS=0.02` and `DSLV_MIN_BASELINE_SAMPLES=30`

This lets a single anchor node produce HDF5 files immediately for hardware and
pipeline validation. It is **not** the production multi-node configuration.

Check live state:

```bash
cat /run/dslv-zpdi/health.json | python3 -m json.tool
curl -s http://127.0.0.1:8080/api/status | python3 -m json.tool
ls -lh /home/dynogator/dslv-zpdi/output/primary/
```

## 6. Known Caveats

- **Mono-node mode is for development.** Before production, revert:
  - remove `DSLV_BASELINE_FIXED_THRESHOLD`
  - set `DSLV_MIN_CONFIRMING_NODES=4`
  - set `DSLV_BASELINE_HOURS=72` and `DSLV_MIN_BASELINE_SAMPLES=240`
- **10 MHz external reference lock** is a physical property. Stock Pluto firmware cannot report lock, so the pipeline reports `UNVERIFIED_PHYSICAL_PROPERTY`. Use external instrumentation or custom Pluto firmware if formal lock verification is required.
- **TUI dashboard not visually confirmed** in this session. After the next reboot, verify that the retro boot screen and Rich TUI render correctly on the 1024×600 touchscreen.
- **UPS `ac_present` may toggle briefly** at boot. The monitor waits for sustained AC loss before shutdown; a momentary flip is normal.
- Baseline state persists across pipeline restarts in `/var/lib/dslv-zpdi/baseline.json`.

## 7. Quick Validation

```bash
cd /home/dynogator/dslv-zpdi
.venv/bin/pytest tests/ -q
.venv/bin/python tools/orphan_checker.py
.venv/bin/python tools/check_version_sync.py
.venv/bin/python tools/repo_guard.py
```

Expected: 184 passed / 1 skipped, all guard tools clean.

## 8. Reboot Preparation

The node has been prepared for a clean reboot:

- All DSLV services (`tuning`, `preflight`, `dslv-zpdi`, `ups`, `webdash`) are
  `enabled` and will start automatically.
- `chrony` and `gpsd` are enabled; `gpsd` was specifically enabled during this
  pass because the NMEA feed is required by the pipeline.
- The only desktop autostart entry is
  `~/.config/autostart/dslv-zpdi-dashboard.desktop`, which launches the retro
  boot orchestrator in `lxterminal`.
- Autologin for `dynogator` is active in LightDM and getty.
- `dynogator` has passwordless sudo so the boot orchestrator can start any
  required service.
- Installed systemd units match the repo files exactly.
- The pipeline baseline state persists in `/var/lib/dslv-zpdi/baseline.json`, so
  the node re-locks quickly after reboot.

Reboot command issued:

```bash
sudo reboot
```

Expected post-reboot sequence:

1. systemd starts `chrony`, `gpsd`, tuning, preflight, pipeline, UPS, and webdash.
2. LightDM autologins `dynogator` into labwc.
3. Autostart launches `tools/boot_orchestrator.py` in a 120×40 terminal.
4. The orchestrator verifies the service chain and execs the Rich TUI dashboard.
5. PRIMARY HDF5 output resumes.

## 9. Next Steps

1. After reboot, confirm the service chain is active and the web dashboard
   returns live data.
2. Confirm HDF5 primary files finalize and rotate correctly (`output/primary/*.h5`).
3. Visually confirm the touchscreen dashboard after the next reboot.
4. When multi-node hardware is available, revert to production baseline/confirmation settings.
5. Review `docs/node_ops/TOOLCHAIN_AUDIT.md` for future upgrades (TPM2 key storage, Grafana, nftables).
6. If the Pixel 9 Pro XL node (`10.128.24.165`) joins the LAN, verify its dashboard and telemetry path.

## 10. References

- `docs/node_ops/WORK_LOG.md` — detailed installation and commissioning log.
- `docs/node_ops/REBOOT_PREP_REPORT.md` — this reboot pass summary.
- `docs/node_ops/TOOLCHAIN_AUDIT.md` — component evaluation and optimization notes.
- `docs/hardware/GEEKWORM_X1202_UPS.md` — UPS operator reference.
- `specs/SPEC-009.md` — baseline learning FSM specification.
- `config/node_profiles/tier1_pluto_lbe1421.yaml` — active node profile.
