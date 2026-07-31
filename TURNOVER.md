# Turnover Notes — DSLV-ZPDI Tier-1 Pi 5 Node

**Date:** 2026-07-09  
**Node hostname:** `raspberrypi`  
**Hardware:** Raspberry Pi 5 16 GB + HamGeek PlutoSDR+ (AD9363 REV5) + Leo Bodnar LBE-1421 + Geekworm X-1202 UPS + 10" Lenovo HDMI touchscreen  
**Repository:** `/home/dynogator/dslv-zpdi` (`github.com/DynoGator/dslv-zpdi`, branch `main`, Rev 5.0.0)  

## 1. What Was Done

This Pi 5 was commissioned as a Tier-1 institutional anchor node for the DSLV-ZPDI network. The following systems were installed, configured, and verified:

1. **GPSDO-disciplined timing**
   - LBE-1421 1 PPS output wired to GPIO 18 (header pin 12).
   - `pps-gpio` overlay active; `/dev/pps0` confirmed.
   - `gpsd` owns `/dev/ttyACM0`; `chronyd` is Stratum 1 locked to PPS.

2. **SDR subsystem**
   - PlutoSDR+ reachable at `ip:192.168.2.1`.
   - 10 MHz reference from GPSDO Out2 wired to PlutoSDR+ EXT_REF_CLK.
   - Pipeline opens the Pluto IIO backend on every ingest cycle.

3. **UPS subsystem**
   - X-1202 HAT responding on I2C bus 1, address `0x36`.
   - UPS monitor service enabled; shutdown logic armed but fail-safe (no shutdown if UPS unreadable).

4. **Pipeline + trust**
   - Production HMAC key installed and wired into `HDF5Writer`.
   - SPEC-009 baseline learning is now started automatically.
   - All qualification, routing, and attestation code paths verified with synthetic primary data.

5. **Dashboards**
   - Flask web dashboard on `http://<pi-ip>:8080/`.
   - Rich TUI dashboard autostarts on graphical login in compact mode for the 1024×600 touchscreen.

6. **Git / collaboration**
   - Project home and development environment organized at `/home/dynogator/dslv-zpdi`.
   - Secure credential storage path prepared at `/home/dynogator/dslv-zpdi/.secrets/git-credentials`.
   - Awaiting GitHub PAT to push commits.

## 2. Current Runtime State

All systemd services are enabled and active:

```text
dslv-zpdi-tuning.service    active
dslv-zpdi-preflight.service active
dslv-zpdi.service           active
dslv-zpdi-ups.service       active
dslv-zpdi-webdash.service   active
```

Health endpoint (`/run/dslv-zpdi/health.json`):

- `timing_healthy: true`
- `hal_mode: external`
- `baseline_state: LEARNING`
- `chrony_stratum: 1`
- Secondary packets flowing; primary output gated by baseline lock and multi-node confirmation.

## 3. Important Caveats

- **Baseline learning period:** The node is learning its RF baseline for 72 hours (or 240 samples, whichever comes first). During this time, all packets route to `output/secondary/quarantine.jsonl`. Do not panic — this is expected per SPEC-009. Restarting the pipeline resets the learning clock.
- **Primary output requires 4 confirming nodes:** The router is configured with `min_confirming_nodes: 4`. The registered Tier-2 node `pixel-9-pro-xl` (`10.128.24.165`) must be online and posting telemetry for primary-confirmed events to occur.
- **External clock lock:** The PlutoSDR+ 10 MHz lock cannot be verified in software with stock firmware. The qualification result `external_reference_evidence=UNVERIFIED_PHYSICAL_PROPERTY` is expected. Verify with external test equipment or custom Pluto firmware if needed.
- **UPS AC reading:** Can briefly show `ac_present: false` at boot. The monitor requires continuous AC loss for 300 seconds before scheduling shutdown.

## 4. File Changes to Commit

Run `git status` from `/home/dynogator/dslv-zpdi` to see the full list. Highlights:

- `src/dslv_zpdi/layer1_ingestion/timing/pps_listener.py` — sysfs PPS reader
- `src/dslv_zpdi/layer1_ingestion/timing/nmea_stream.py` — gpsd TCP reader
- `src/dslv_zpdi/layer2_core/wiring.py` — env-driven baseline config
- `src/dslv_zpdi/main_pipeline.py` — key provider + baseline start
- `config/node_profiles/tier1_pluto_lbe1421.yaml` — production HMAC required
- `tools/x1202_ups_monitor.py` — new
- `config/dslv-zpdi-ups.service` — new
- `tools/dashboard/web_server.py` — UPS panel
- `docs/hardware/GEEKWORM_X1202_UPS.md` — new
- `docs/node_ops/WORK_LOG.md` — new
- `CHANGELOG.md` — updated

## 5. How to Supply Git Credentials

When you have a GitHub personal access token:

```bash
# Create the credential file
mkdir -p /home/dynogator/dslv-zpdi/.secrets
cat > /home/dynogator/dslv-zpdi/.secrets/git-credentials <>OF
https://<GITHUB_USERNAME>:<TOKEN>@github.com
EOF
chmod 600 /home/dynogator/dslv-zpdi/.secrets/git-credentials

# Configure git to use it
git config --global credential.helper 'store --file /home/dynogator/dslv-zpdi/.secrets/git-credentials'

# Verify push access
cd /home/dynogator/dslv-zpdi
git remote -v
git status
# git push origin main
```

## 6. Quick Operational Commands

```bash
# Pipeline status and logs
sudo systemctl status dslv-zpdi
sudo journalctl -u dslv-zpdi -f

# Timing
cat /run/dslv-zpdi/health.json
chronyc tracking

# UPS
sudo systemctl status dslv-zpdi-ups
.venv/bin/python -c "from dslv_zpdi.layer1_ingestion.x1202_ups import ups_telemetry; import json; print(json.dumps(ups_telemetry(), indent=2))"

# Dashboard
# Web:  http://<pi-ip>:8080/
# TUI:  tools/dashboard/launch.sh --compact

# Restart everything cleanly
sudo systemctl restart dslv-zpdi-tuning dslv-zpdi-preflight dslv-zpdi dslv-zpdi-ups dslv-zpdi-webdash
```

## 7. Contacts / Next Steps

- **Hardware wiring:** see `docs/hardware/LBE1421_PLUTO_WIRING.md` and `docs/hardware/GEEKWORM_X1202_UPS.md`.
- **Baseline progress:** watch `health.json` for `baseline_state: LOCKED`.
- **Primary output:** will appear in `output/primary/` once baseline is locked and a 4-node confirmation event occurs.
- **Questions:** consult `docs/node_ops/WORK_LOG.md` and `CHANGELOG.md`.
