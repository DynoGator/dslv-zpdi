# DSLV-ZPDI Tier-1 Node Work Log

**Node:** `raspberrypi` (Raspberry Pi 5 16 GB)  
**Project:** `dslv-zpdi` Rev 5.0.0  
**Profile:** `config/node_profiles/tier1_pluto_lbe1421.yaml`  
**Date:** 2026-07-09  
**Operator:** Kimi Code CLI / dynogator  

## 1. Objective

Install and configure `dslv-zpdi` on a Raspberry Pi 5 as a Tier-1 RF-metrology anchor node, integrating:

- Leo Bodnar LBE-1421 GPSDO (1 PPS to GPIO 8, 10 MHz to PlutoSDR+ REF)
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

- `/boot/firmware/config.txt`: `dtoverlay=pps-gpio,gpiopin=8` confirmed active.
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

### 3.7 Boot Orchestrator & Dashboard Autostart

- Created `tools/boot_orchestrator.py`, a retro ASCII-terminal startup wrapper.
  - Verifies the systemd service chain in dependency order.
  - Starts any managed service that is not already active (`TUNING`, `PREFLIGHT`, `SDR`, `UPS`, `WEBDASH`).
  - Treats `chrony` and `gpsd` as externally managed but verifies them.
  - Renders Rich Layout panels with DSLV-ZPDI ASCII logo, sequential stage list, rotating snark messages, and a footer status bar.
  - On success, `exec`s the Rich TUI dashboard (`tools/dashboard/launch.sh --compact`).
- Updated `~/.config/autostart/dslv-zpdi-dashboard.desktop` to launch the orchestrator in a 120×40 `lxterminal` window on Wayland login.
- Added `PYTHONIOENCODING`, `LANG`, and `LC_ALL` exports in the orchestrator before execing the dashboard to keep Rich glyphs clean.

### 3.8 Service Hardening

Hardened the main pipeline systemd unit (`config/os-hardening/dslv-zpdi.service`):

- `ProtectSystem=strict` with explicit `ReadWritePaths` for output, baseline state, runtime health socket, and USB device access.
- `ProtectHome=read-only`, `ProtectClock=true`, `ProtectHostname=true`.
- `RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX`, `SystemCallFilter=@system-service`.
- `CPUAffinity=2 3` pins pipeline work away from the GUI/compositor cores.
- `MemoryMax=2G`, `MemorySwapMax=0`, `LimitNOFILE=65536`.
- `StartLimitIntervalSec=120` / `StartLimitBurst=3` in `[Unit]` to contain restart loops.
- `TimeoutStartSec=60`, `TimeoutStopSec=30`.
- `Nice=-5`, `IOSchedulingClass=realtime`, `IOSchedulingPriority=4` retained.
- The installed `/etc/systemd/system/dslv-zpdi.service` was synced from the repo file and `systemctl daemon-reload` run.

Also corrected stale paths in repo service files:

- `config/dslv-zpdi-webdash.service` now points to `/home/dynogator/dslv-zpdi` and includes `ProtectSystem=strict`, `MemoryMax=512M`, `CPUAffinity=1`, and restart limits.
- `config/dslv-zpdi-preflight.service` path corrected.
- `config/dslv-zpdi-tuning.service` aligned with installed unit.
- `config/dslv-zpdi-ups.service` added `MemoryMax=128M`, `CPUAffinity=1`, restart limits, and journal output.

### 3.9 Toolchain Audit & Dashboard Telemetry Optimization

- Wrote `docs/node_ops/TOOLCHAIN_AUDIT.md` with a full component-by-component evaluation of timing, SDR ingestion, persistence/trust, UPS/power, dashboards, and process supervision, including alternatives and recommendations.
- `main_pipeline.py` now publishes `sdr_health`, `pps`, and `ups` snapshots into `/run/dslv-zpdi/health.json` every 10 payloads.
- `tools/dashboard/web_server.py` and `tools/dashboard/panels/hardware.py` consume the health JSON directly instead of re-probing hardware each cycle.
- `SdrHealth` dataclass gained `external_reference_configured`; `PlutoIioBackend.health()` populates it so the web dashboard reports `clock_src: external`.
- `TimingMonitor` and `tools/check_timing.py` switched from `System time` to `RMS offset` for a stable PPS-jitter figure once chrony has converged.

### 3.10 Git Credentials & Collaborator Access

- Project GitHub credentials stored in `/home/dynogator/dslv-zpdi/.secrets/`:
  - `github-account.txt` — account, password, email, and token reference (mode `0600`).
  - `git-credentials` — git credential-store line for `https://DynoGator:<PAT>@github.com` (mode `0600`).
- `./configure_git_auth.sh` sources `GITHUB_PAT` from `.env` and installs the credential helper scoped to the repo.
- `.secrets/` is ignored by `.gitignore`; credentials are never committed.

### 3.11 Mono-Node Dev Mode & SPEC-009 Baseline Unlock

Motivation: the current field deployment has only the Tier-1 anchor node (no
swarm of 4+ nodes). Requiring a 4-node confirmation gate blocked all PRIMARY
HDF5 output, which defeats hardware/pipeline validation.

Changes:

- Added `DSLV_MIN_CONFIRMING_NODES` environment variable support in
  `src/dslv_zpdi/layer2_core/wiring.py` and set it to `1` in `.env`.
- Added periodic `coherence_engine.finalize_baseline()` calls in
  `main_pipeline.py` (every 60 s) so the baseline can lock automatically once
  duration/sample gates are met.
- Fixed `CoherenceScorer.start_baseline()` to be idempotent for the `LEARNING`
  state; process restarts no longer wipe accumulated baseline samples.
- Added optional `DSLV_BASELINE_FIXED_THRESHOLD` override in
  `src/dslv_zpdi/layer2_core/coherence.py` for development environments where
  the 3-sigma threshold would otherwise be too high to trigger events.
- Wrote a real `specs/SPEC-009.md` documenting the baseline FSM, states,
  transitions, parameters, and persistence (the file was previously a stub).

Current dev settings in `.env`:

```bash
DSLV_BASELINE_HOURS=0.02
DSLV_MIN_BASELINE_SAMPLES=30
DSLV_MIN_CONFIRMING_NODES=1
DSLV_BASELINE_FIXED_THRESHOLD=0.30
```

These values are intentionally aggressive for development and hardware
validation. For a production multi-node deployment, raise `DSLV_MIN_CONFIRMING_NODES`
to 4, remove `DSLV_BASELINE_FIXED_THRESHOLD`, and restore
`DSLV_BASELINE_HOURS=72` / `DSLV_MIN_BASELINE_SAMPLES=240`.

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
- `baseline_state: LOCKED`
- `chrony_stratum: 1`
- PRIMARY HDF5 output active.

### 4.4 Web Dashboard

`http://<pi-ip>:8080/` serves live status including system, pipeline, swarm nodes, SDR, and UPS.

### 4.5 HDF5 + HMAC

- Primary HDF5 file created at `output/primary/dslv_zpdi_*.h5.partial`.
- Event groups contain SHA-256 content hash and event-chain hash.
- `hmac_sha256` attribute present and verifiable against the production key.
- Detached `.sha256` and `.status.json` files produced on file finalization.

### 4.6 Dashboard Telemetry Optimization

- `/api/status` returns `sdr.clock_src: external`, `sdr.reachable: true`, live UPS telemetry, and baseline state `LOCKED`.
- Health JSON is updated every ~10 payloads; dashboard panels no longer hammer the I2C bus or PlutoSDR context directly.
- Web dashboard auto-refresh every 5 s shows current system, pipeline, SDR, UPS, and node registry data.

### 4.7 Boot Orchestrator

- `tools/boot_orchestrator.py --no-start` reports all managed services active on this node.
- Autostart desktop entry points to the orchestrator and launches it in a terminal window on graphical login.
- The orchestrator exits with code `1` if any required service fails to start, preventing a blind dashboard launch.

### 4.8 Mono-Node PRIMARY Output

After applying the dev baseline settings:

```bash
curl -s http://127.0.0.1:8080/api/status | python3 -m json.tool
# baseline.ready: true
# baseline.baseline_state: LOCKED
# baseline.threshold: 0.3
# pipeline.primary_written: >0
# pipeline.secondary_logged: >0
ls output/primary/
# dslv_zpdi_YYYYMMDD_HHMMSS.h5.partial
```

## 5. Known State / Caveats

- The node is running in **mono-node development mode**. PRIMARY events are
  confirmed with a single node (`DSLV_MIN_CONFIRMING_NODES=1`) and a fixed
  low threshold (`DSLV_BASELINE_FIXED_THRESHOLD=0.30`). This is appropriate for
  hardware/pipeline validation but must be hardened before any production or
  multi-node deployment.
- External 10 MHz reference lock is a physical property; software qualification reports `UNVERIFIED_PHYSICAL_PROPERTY`. Verify lock with external instrumentation or custom Pluto firmware if required.
- The UPS `ac_present` reading can briefly toggle at boot; the monitor waits for continuous AC-loss before shutdown.
- Git credentials are populated and available to collaborators in `.secrets/`; run `./configure_git_auth.sh` after cloning on a new machine to activate the credential helper.
- The Rich TUI dashboard is configured to autostart via the boot orchestrator but has **not been visually verified on the touchscreen** in this session; confirm glyph rendering and geometry after the next reboot.

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
# Boot: tools/boot_orchestrator.py

# Git credentials (already configured)
# /home/dynogator/dslv-zpdi/.secrets/git-credentials
# Format: https://<username>:<token>@github.com
```

## 7. Files Modified / Created

Modified:

- `config/deployment.yaml`
- `config/node_profiles/tier1_pluto_lbe1421.yaml`
- `config/dslv-zpdi-ups.service`
- `config/dslv-zpdi-webdash.service`
- `config/dslv-zpdi-preflight.service`
- `config/dslv-zpdi-tuning.service`
- `config/os-hardening/dslv-zpdi.service`
- `src/dslv_zpdi/layer1_ingestion/timing/nmea_stream.py`
- `src/dslv_zpdi/layer1_ingestion/timing/pps_listener.py`
- `src/dslv_zpdi/layer1_ingestion/sdr/capture_result.py`
- `src/dslv_zpdi/layer1_ingestion/sdr/pluto_iio.py`
- `src/dslv_zpdi/layer2_core/wiring.py`
- `src/dslv_zpdi/layer2_core/coherence.py`
- `src/dslv_zpdi/main_pipeline.py`
- `src/dslv_zpdi/watchdog/timing_monitor.py`
- `tools/check_timing.py`
- `tools/dashboard/web_server.py`
- `tools/dashboard/panels/hardware.py`
- `tools/provision_tier1.py`
- `~/.config/autostart/dslv-zpdi-dashboard.desktop`
- `/etc/systemd/system/dslv-zpdi.service`

Created:

- `tools/x1202_ups_monitor.py`
- `tools/boot_orchestrator.py`
- `config/dslv-zpdi-ups.service`
- `docs/hardware/GEEKWORM_X1202_UPS.md`
- `docs/node_ops/TOOLCHAIN_AUDIT.md`
- `docs/node_ops/TURNOVER_NOTES.md`
- `docs/node_ops/WORK_LOG.md` (this file)
- `specs/SPEC-009.md` (rewritten from stub)

## 8. Next Actions for Collaborators

1. Verify touchscreen calibration and rotate the display if the 1024×600 panel is mounted in portrait.
2. Confirm the registered Tier-2 node `pixel-9-pro-xl` at `10.128.24.165` is on the same LAN and reachable if/when multi-node mode is re-enabled.
3. Monitor `output/primary/` for finalized `.h5` files after the first rotation (default rotation is size- or time-based).
4. Review `docs/node_ops/TOOLCHAIN_AUDIT.md` for future tool-chain improvements (TPM2, Grafana, nftables).
5. After the next reboot, visually confirm the Rich TUI dashboard renders correctly through the boot orchestrator.
6. Before production deployment, revert to multi-node confirmation:
   - remove or comment out `DSLV_BASELINE_FIXED_THRESHOLD`
   - set `DSLV_MIN_CONFIRMING_NODES=4`
   - set `DSLV_BASELINE_HOURS=72` and `DSLV_MIN_BASELINE_SAMPLES=240`.

## 9. Reboot Preparation (Final Pass)

Goal: ensure the node comes back up cleanly with real hardware data and all startup paths persistent.

### 9.1 Real-Data Verification

Confirmed live telemetry sources:

- **PPS / timing**: `chronyc tracking` reports Stratum 1, Reference ID `PPS1`, RMS offset ~786 ns.
- **SDR**: `sdr.mode: REAL`, `clock_src: external`, PlutoSDR+ reachable at `ip:192.168.2.1`.
- **UPS**: MAX17048 on I2C-1/0x36, 97.8% battery, AC present.
- **Web dashboard**: `http://127.0.0.1:8080/api/status` returns the above live state.
- **Rich TUI**: system/pipeline/hardware/UPS panels read `/run/dslv-zpdi/health.json`.

### 9.2 Boot Persistence

- Enabled `gpsd.service` (was disabled).
- Verified all DSLV services are `enabled` and will start on boot.
- Verified only one autostart entry exists: `~/.config/autostart/dslv-zpdi-dashboard.desktop`.
- Verified autologin for `dynogator` in `/etc/lightdm/lightdm.conf` and getty.
- Verified `dynogator` has passwordless sudo so the boot orchestrator can start services.
- Confirmed installed systemd units match repo files (`diff` clean).
- Confirmed no conflicting NTP daemon (`systemd-timesyncd` inactive/not enabled).

### 9.3 Startup Blockers Removed

| Issue | Resolution |
|-------|------------|
| `gpsd` disabled | `sudo systemctl enable gpsd` |
| Service file path drift | Synced all installed units from `config/` |
| Possible duplicate autostart | Only `dslv-zpdi-dashboard.desktop` present |
| Silent simulation risk | Profile `allow_simulator_fallback: false`; service runs without `--simulator` |

### 9.4 Reboot Command

```bash
sudo reboot
```

### 9.5 Expected Post-Reboot Sequence

1. systemd starts `chrony`, `gpsd`, tuning, preflight, pipeline, UPS, and webdash.
2. LightDM autologins `dynogator` into labwc.
3. Autostart launches the boot orchestrator in `lxterminal`.
4. Boot orchestrator verifies services, renders retro ASCII status, and execs the Rich TUI dashboard.
5. Pipeline reloads persisted baseline state and resumes PRIMARY HDF5 output.

### 9.6 Caveats

- The Rich TUI **waterfall panel** requires `hackrf_sweep`; no HackRF (legacy/optional) is connected, so it remains in SIM mode. All other dashboard data is real.
- Touchscreen glyph/layout has been configured but not visually verified.
- Mono-node dev mode remains active until deliberately reverted for production.

## 10. Files Modified / Created (This Pass)

Created:

- `docs/node_ops/REBOOT_PREP_REPORT.md`

Modified:

- `docs/node_ops/WORK_LOG.md` (this section)
