# DSLV-ZPDI Tier-1 Node Work Log

**Node:** `raspberrypi` (Raspberry Pi 5 16 GB)  
**Project:** `dslv-zpdi` Rev 5.0.0  
**Profile:** `config/node_profiles/tier1_pluto_lbe1421.yaml`  
**Date:** 2026-07-09  
**Operator:** Kimi Code CLI / dynogator  

## 1. Objective

Install and configure `dslv-zpdi` on a Raspberry Pi 5 as a Tier-1 RF-metrology anchor node, integrating:

- Leo Bodnar LBE-1421 GPSDO (1 PPS to GPIO 18, 10 MHz to PlutoSDR+ REF)
- HamGeek / LibreSDR PlutoSDR+ (AD9363 REV5) via Ethernet at `192.168.2.1`
- Geekworm X-1202 UPS HAT with 4× Sony VTC6 18650 cells
- 10" Lenovo HDMI touchscreen (1024×600)
- PWM-active cooler and 4-port USB hub
- SHA256/HMAC-secured HDF5 pipeline
- Autostarting web (port 8080) and Rich TUI dashboards

## 2. Environment Audit

See `docs/node_ops/INITIAL_AUDIT.md` for the full system audit captured at session start.

Key facts:

- Raspberry Pi 5 Model B Rev 1.1, 16 GB RAM
- OS: Debian / Raspberry Pi OS (labwc Wayland compositor)
- Python 3.13 venv at `/home/dynogator/dslv-zpdi/.venv`
- `gpsd` owns `/dev/ttyACM0` (LBE-1421 USB-C serial)
- `chronyd` disciplined to PPS, reporting Stratum 1
- User `dynogator` in `i2c`, `gpio`, `dialout`, `plugdev`, `sudo` groups

## 3. Configuration Changes

### 3.1 Timing & GPSDO

- `/boot/firmware/config.txt`: `dtoverlay=pps-gpio,gpiopin=18` confirmed active.
- `/dev/pps0` present and producing edges.
- `chrony` locked to PPS via `refclock PPS /dev/pps0` and `refclock SHM 0` for GPS NMEA.
- `PpsListener` rewritten to read `/sys/class/pps/pps0/assert` instead of the unreliable `PPS_FETCH` ioctl on this Pi 5 kernel. Jitter computed from kernel timestamps (not userspace arrival time).
- `NmeaStream` extended with `gpsd://host:port` TCP reader so `gpsd` can own the serial port while the pipeline reads GGA sentences.
- Node profile `nmea_port` set to `gpsd://localhost:2947`.

### 3.2 SDR

- PlutoSDR+ reachable at `ip:192.168.2.1` with `ad9361-phy` enumerated.
- `DSLV_SDR_URI=ip:192.168.2.1` in `.env`.
- External 10 MHz reference is physically wired from GPSDO Out2 to PlutoSDR+ EXT_REF_CLK; software cannot detect lock on stock Pluto firmware, so qualification marks it `UNVERIFIED_PHYSICAL_PROPERTY` (expected).

### 3.3 UPS

- X-1202 fuel gauge (MAX17048/49) responding on `/dev/i2c-1` address `0x36`.
- Created `tools/x1202_ups_monitor.py` per SPEC-004A.8.
- Created `config/dslv-zpdi-ups.service` and installed/enabled it.
- Created `docs/hardware/GEEKWORM_X1202_UPS.md`.
- UPS telemetry integrated into the Flask web dashboard (`/api/status` and HTML card).

### 3.4 Pipeline & Trust

- `main_pipeline.py` now passes an explicit `KeyProvider` to `HDF5Writer` and sets `allow_development_key=False` when production key is required.
- Node profile `require_production_hmac_key: true`.
- Production HMAC key generated at `/etc/dslv-zpdi/hmac.key` (mode `0600`, owner `dynogator`).
- `layer2_core/wiring.py` now reads `DSLV_BASELINE_HOURS`, `DSLV_MIN_BASELINE_SAMPLES`, and `DSLV_BASELINE_STATE_PATH` from the environment instead of using hard-coded defaults.
- `main_pipeline.py` now calls `coherence_engine.start_baseline()` so baseline learning actually begins (was never started, causing all packets to remain in secondary stream).
- `/var/lib/dslv-zpdi` created and owned by `dynogator` for baseline persistence.

### 3.5 Dashboards

- Web dashboard service `dslv-zpdi-webdash.service` enabled and bound to `0.0.0.0:8080`.
- Web dashboard extended with UPS power card.
- Rich TUI dashboard autostart desktop entry updated to launch `tools/dashboard/launch.sh --compact` with a 120×34 geometry suitable for the 1024×600 touchscreen.
- `dslv-zpdi.service` given `RuntimeDirectory=dslv-zpdi` so `/run/dslv-zpdi/health.json` is written in the expected location.

### 3.6 Systemd Services

All enabled and active:

- `dslv-zpdi-tuning.service` — CPU governor `performance`, USB power management
- `dslv-zpdi-preflight.service` — hardware preflight checks
- `dslv-zpdi.service` — main production pipeline
- `dslv-zpdi-ups.service` — UPS monitor / graceful shutdown
- `dslv-zpdi-webdash.service` — Flask dashboard on port 8080

## 4. Verification Results

### 4.1 Test Suite

```bash
.venv/bin/pytest tests/ -q
# 184 passed, 1 skipped, 2 warnings

.venv/bin/python tools/orphan_checker.py     # OK
.venv/bin/python tools/check_version_sync.py # Version sync clean: 5.0.0
.venv/bin/python tools/repo_guard.py         # OK
```

### 4.2 Timing

```bash
chronyc tracking
# Stratum 1, Reference ID PPS1, RMS offset ~219 ns

PpsListener sysfs test
# history 16, rms_jitter_ns ~2500–4000 (kernel interrupt timing on Pi 5)
```

### 4.3 Pipeline Health

`/run/dslv-zpdi/health.json` shows:

- `timing_healthy: true`
- `hal_mode: external`
- `baseline_state: LEARNING`
- `chrony_stratum: 1`
- Secondary packets flowing; primary routing gated until baseline locks.

### 4.4 Web Dashboard

`http://<pi-ip>:8080/` serves live status including system, pipeline, swarm nodes, SDR, and UPS.

### 4.5 HDF5 + HMAC

Synthetic primary-write commissioning test confirmed:

- HDF5 primary file created.
- Event group contains SHA-256 content hash and event-chain hash.
- `hmac_sha256` attribute present and verifiable against the production key.
- Detached `.sha256` and `.status.json` files produced on file finalization.

## 5. Known State / Caveats

- The node is in **SPEC-009 baseline learning** for 72 hours (or 240 samples). During this period all packets route to `output/secondary/quarantine.jsonl` with reason `baseline_learning_active`. Primary HDF5 output begins after the baseline locks and a confirmed multi-node event occurs (`min_confirming_nodes: 4`).
- External 10 MHz reference lock is a physical property; software qualification reports `UNVERIFIED_PHYSICAL_PROPERTY`. Verify lock with external instrumentation or custom Pluto firmware if required.
- The UPS `ac_present` reading can briefly toggle at boot; the monitor waits for continuous AC-loss before shutdown.
- Git credentials are not yet populated. When a GitHub PAT is supplied, store it in `/home/dynogator/dslv-zpdi/.secrets/git-credentials` and run `git config --global credential.helper 'store --file <path>'`.

## 6. Useful Commands

```bash
# Service control
sudo systemctl status dslv-zpdi
sudo systemctl restart dslv-zpdi
sudo journalctl -u dslv-zpdi -f

# Timing
chronyc tracking
cat /run/dslv-zpdi/health.json

# UPS one-shot
.venv/bin/python -c "from dslv_zpdi.layer1_ingestion.x1202_ups import ups_telemetry; import json; print(json.dumps(ups_telemetry(), indent=2))"

# Dashboards
# Web: http://<pi-ip>:8080/
# TUI: tools/dashboard/launch.sh --compact

# Git credentials (when PAT available)
# Edit /home/dynogator/dslv-zpdi/.secrets/git-credentials
# Format: https://<username>:<token>@github.com
```

## 7. Files Modified / Created

Modified:

- `config/deployment.yaml`
- `config/node_profiles/tier1_pluto_lbe1421.yaml`
- `src/dslv_zpdi/layer1_ingestion/timing/nmea_stream.py`
- `src/dslv_zpdi/layer1_ingestion/timing/pps_listener.py`
- `src/dslv_zpdi/layer2_core/wiring.py`
- `src/dslv_zpdi/main_pipeline.py`
- `tools/check_timing.py`
- `tools/dashboard/web_server.py`
- `tools/provision_tier1.py`
- `~/.config/autostart/dslv-zpdi-dashboard.desktop`
- `/etc/systemd/system/dslv-zpdi.service`

Created:

- `tools/x1202_ups_monitor.py`
- `config/dslv-zpdi-ups.service`
- `docs/hardware/GEEKWORM_X1202_UPS.md`
- `docs/node_ops/WORK_LOG.md` (this file)

## 8. Next Actions for Collaborators

1. Provide GitHub PAT so changes can be pushed to `github.com/DynoGator/dslv-zpdi`.
2. Allow 72-hour baseline learning to complete; do not restart the pipeline unless necessary.
3. Verify touchscreen calibration and rotate the display if the 1024×600 panel is mounted in portrait.
4. Confirm the registered Tier-2 node `pixel-9-pro-xl` at `10.128.24.165` is on the same LAN and reachable.
5. Monitor `output/primary/` for the first confirmed-event HDF5 after baseline lock.
