# DSLV-ZPDI (Distributed Sensor Locational Vectoring)

**Project Phase:** Phase 2A (Hardware Transition — RF Metrology)
**Revision:** Rev 4.7.1 — Dependency and Validation Alignment
**Date:** 2026-05-30
**Status:** Beta — Tier 1 Pi 5 anchor operational, Pixel 9 Pro XL mobile node bridged via PiRepo hotspot, web dashboard active, all 47 tests passing.

---

## Overview

DSLV-ZPDI is a multi-modal Signals Intelligence (SIGINT) network that translates anomalous multi-spectrum phenomena into institutional-grade, GPS-disciplined HDF5 telemetry.

**Phase 2A RF Metrology Pivot:** The architecture transitions from IT Network Timing (PTP/i210-T1) to RF Metrology Timing (GPSDO/HackRF). This achieves hardware-level ADC phase coherence by injecting an atomic-level 10 MHz reference directly into the SDR front-end — making USB jitter irrelevant to sample timing.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 1 — INGESTION                                             │
│  HardwareHAL (HackRF + LBE-1421) or SimulatedHAL               │
│  PPS edge detection · NMEA GPS fix · SDR IQ samples             │
└────────────────────────┬─────────────────────────────────────────┘
                         │ Payload (JSON)
┌────────────────────────▼─────────────────────────────────────────┐
│  LAYER 2 — CORE                                                  │
│  KCET-ATLAS Kuramoto coherence engine (SPEC-006/009)            │
│  Baseline FSM: NOT_STARTED → LEARNING → LOCKED                  │
│  Trust wiring · Swarm integrity                                  │
└────────────────────────┬─────────────────────────────────────────┘
                         │ RoutingDecision
┌────────────────────────▼─────────────────────────────────────────┐
│  LAYER 3 — TELEMETRY                                             │
│  Dual-stream router (PRIMARY institutional / SECONDARY forensic) │
│  HDF5 persistence · SHA-256 cryptographic attestation           │
└──────────────────────────────────────────────────────────────────┘
```

All modules reference a SPEC-ID in their docstring. `tools/orphan_checker.py` enforces compliance.

---

## Hardware Stack (Phase 2A Primary)

| Component           | Model                         | Purpose                                                          |
|---------------------|-------------------------------|------------------------------------------------------------------|
| Tier 1 Compute      | Raspberry Pi 5 (16 GB)        | FFT processing, HDF5 storage, hotspot AP, pipeline anchor        |
| Mobile Node         | Pixel 9 Pro XL (GrapheneOS)   | Remote swarm telemetry over PiRepo Wi-Fi (10.42.0.x)            |
| Display             | 7" DSI (800×480)              | On-device Rich TUI dashboard                                     |
| SDR                 | HackRF One                    | RF ingestion, 20 MHz BW, external CLKIN (amp blown, parts on order) |
| Clock Authority     | Leo Bodnar LBE-1421 GPSDO     | 10 MHz reference + 1 PPS, USB-C, NMEA, 3.3 V CMOS              |
| Antenna             | Great Scott Gadgets ANT500    | 75 MHz – 1 GHz coverage                                         |
| RF Interconnect     | SMA Male-to-Male (50 Ω)       | GPSDO Output → HackRF CLKIN (≤ 1 ft)                           |
| Future: Radon Sensor| EcoSense RadonEye Pro         | Radon ingestion via SPEC-015 (staging endpoint live, promotion pending) |

### Physical Wiring Protocol

1. **RF Phase Lock (ADC slave):** SMA cable · LBE-1421 `Output` → HackRF `CLKIN`
   Hardware ADC is now phase-locked to GPS constellation. USB jitter is irrelevant.
2. **OS Timestamping (heartbeat):** Jumper · LBE-1421 `1 PPS` → Pi 5 GPIO 18 (physical pin 12).
   Bridge ground between GPSDO and Pi. No level-shifter needed — LBE-1421 outputs 3.3 V CMOS natively.
3. **Power & Telemetry:** USB-C · LBE-1421 → Pi 5 (powers GPSDO; exposes virtual serial `/dev/ttyACM0` for NMEA)
4. **SDR Data:** USB · HackRF → Pi 5 USB 3.0 (IQ data transfer — timing separate from USB jitter)

---

## Installation & Deployment

### Prerequisites

**Core hardware (Tier 1 Anchor)**
- Raspberry Pi 5 (16 GB) or compatible (see Hardware Agnosticism section)
- HackRF One with 10 MHz CLKIN connected to GPSDO
- Leo Bodnar LBE-1421 GPSDO (USB-C, NMEA, 3.3 V CMOS)
- Great Scott Gadgets ANT500 antenna
- SMA Male-to-Male 50 Ω coax, ≤ 1 ft
- Female-to-female jumper wire (2.54 mm pitch) for PPS
- GPS antenna with clear sky view
- 7" DSI display (800×480) — optional; dashboard runs headless if absent

**Mobile node (optional but supported)**
- Google Pixel 9 Pro XL running GrapheneOS
- Connect to `PiRepo` Wi-Fi hotspot (see Network Configuration below)
- Telemetry sender POSTs JSON to `http://10.42.0.1:5775/api/v1/ingest`

**Python dependencies (beyond standard requirements.txt)**
```bash
pip install flask psutil   # required for node-receiver and web dashboard
```

### One-Shot Bootstrap (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/DynoGator/dslv-zpdi/main/bootstrap.sh | bash -s -- --all
```

`--all` expands to:

| Flag                 | Effect                                                                                        |
|----------------------|-----------------------------------------------------------------------------------------------|
| `--harden`           | Kernel freeze (`apt-mark hold`), sysctl tuning, DVB blacklist, systemd service chain (Nice=-5 + realtime I/O) |
| `--dashboard`        | Installs rich/textual/pyfiglet, wires TUI into XDG autostart (lxterminal 180×50 at desktop boot) |
| `--bloatware`        | Removes LibreOffice, Firefox, Wolfram, Scratch, Thonny, RealVNC, NodeJS, etc. — keeps desktop/WiFi |
| `--passwordless-sudo`| Writes `/etc/sudoers.d/dslv-zpdi` (validated via `visudo -c`)                                |
| `--simulator`        | Enables simulator mode — pipeline runs without GPSDO hardware                                 |

### Manual Install

```bash
git clone https://github.com/DynoGator/dslv-zpdi.git
cd dslv-zpdi

# Enable PPS GPIO overlay (LBE-1421 is 3.3 V CMOS — no level-shifter needed)
echo "dtoverlay=pps-gpio,gpiopin=18,assert_falling_edge=0" | sudo tee -a /boot/firmware/config.txt
sudo reboot

# Full hardened install
sudo ./install_dslv_zpdi.sh --all

# Simulator-only (no hardware required)
sudo ./install_dslv_zpdi.sh --tier1 --simulator
```

### Hardware Verification

```bash
# PPS kernel module
lsmod | grep pps
ppstest /dev/pps0

# HackRF detected
hackrf_info

# GPSDO NMEA telemetry on USB-C virtual serial
python -c "import serial; s=serial.Serial('/dev/ttyACM0', 9600, timeout=2); print(s.readline())"

# Full hardware lock check
python -c "from dslv_zpdi.layer1_ingestion import verify_hardware_lock; print(verify_hardware_lock())"
```

---

## Configuration

### `config/deployment.yaml` — Pipeline Config

The primary runtime configuration. Edit this to change pipeline behavior.

```yaml
paths:
  primary_output:   /home/dynogator/dslv-zpdi/output/primary   # HDF5 institutional stream
  secondary_output: /home/dynogator/dslv-zpdi/output/secondary  # Forensic stream
  state_dir:        /var/lib/dslv_zpdi                          # Baseline FSM state
  baseline_state:   /var/lib/dslv_zpdi/baseline.json

clock_discipline:
  pps_required:              true          # Require /dev/pps0
  pps_device:                /dev/pps0
  chrony_tracking_required:  true
  max_pps_jitter_ns:         1000.0        # Quarantine threshold
  gps_lock_required:         true

spec009:
  baseline_duration_hours:  72    # Minimum hours for baseline learning
  min_baseline_samples:     240   # Minimum samples before LOCKED state

pipeline:
  center_freq_hz:    100000000    # SDR center frequency (Hz)
  sample_rate_hz:    20000000     # SDR sample rate (Hz)
  ingest_interval_sec: 0.1        # Ingestion loop period
```

**Important:** `primary_output` and `state_dir` must be writable by the pipeline user. If they don't exist, the pipeline creates them on first run. If the parent directory is read-only, the pipeline will run but not persist data.

### Environment Variable Overrides

All `DSLV_*` variables override the YAML. Invalid values log a warning and fall back to the default (they do not crash).

| Variable                    | Overrides                              | Example                        |
|-----------------------------|----------------------------------------|--------------------------------|
| `DSLV_CONFIG_PATH`          | Path to deployment.yaml                | `/etc/dslv-zpdi/config.yaml`   |
| `DSLV_CENTER_FREQ_HZ`       | `pipeline.center_freq_hz`              | `144000000`                    |
| `DSLV_SAMPLE_RATE_HZ`       | `pipeline.sample_rate_hz`              | `10000000`                     |
| `DSLV_INGEST_INTERVAL_SEC`  | `pipeline.ingest_interval_sec`         | `0.05`                         |
| `DSLV_BASELINE_HOURS`       | `spec009.baseline_duration_hours`      | `24`                           |
| `DSLV_MIN_BASELINE_SAMPLES` | `spec009.min_baseline_samples`         | `100`                          |
| `DSLV_PRIMARY_OUTPUT_DIR`   | `paths.primary_output`                 | `/mnt/ssd/primary`             |
| `DSLV_SECONDARY_OUTPUT_DIR` | `paths.secondary_output`               | `/mnt/ssd/secondary`           |
| `DSLV_BASELINE_STATE_PATH`  | `paths.baseline_state`                 | `/var/lib/dslv_zpdi/bl.json`   |

### `~/.config/dslv-zpdi/dashboard.toml` — Dashboard Config

The dashboard looks for this file at startup. If missing, all defaults apply. Copy from `config/dashboard.toml.example`.

```toml
[dashboard]
refresh      = 0.5        # Screen refresh interval (seconds, min 0.1)
show_banner  = true       # Show startup banner
service_unit = "dslv-zpdi"

[dashboard.panels]        # Set false to hide any panel
system        = true
pipeline      = true
hardware      = true
waterfall     = true
anomaly       = true
weather       = true
storm         = true
logs          = true
notifications = true

[dashboard.waterfall]
mode      = "SWEEP"       # SWEEP (20 MHz) | NARROW (5 MHz) | SCOPE (2 MHz)
center_hz = 100_000_000   # Starting center frequency (Hz, min 1 MHz)
span_hz   = 20_000_000    # Starting span (Hz, 100 kHz – 500 MHz)
history   = 24            # Waterfall row buffer depth (min 10)

[dashboard.notifications]
humor_every_s  = 4.0      # Interval between dark-humor quips (seconds, min 1)
glitch_every_s = 37.0     # Interval between glitch events
max_items      = 8        # Maximum notifications shown (min 1)

[dashboard.logs]
max_lines = 10            # Max lines in wide mode (compact mode always caps to 3)
```

**Env override:** `DSLV_DASHBOARD_CONFIG=/path/to/custom.toml` overrides the default config path.

**Env flags:**
- `DSLV_DASHBOARD_REAL_SDR=1` — start with live HackRF input (same as `--real-sdr` flag)
- `DSLV_DASHBOARD_COMPACT=1` — force compact layout (same as `--compact` flag)

---

## Operations Dashboard

The dashboard is a Rich-based Live TUI that streams pipeline telemetry, system vitals, hardware state, journalctl logs, and a real-time SDR waterfall — all updating in a single terminal window.

### Launching

```bash
# From the repo directory:
python -m dashboard

# Or via the launcher script:
bash tools/dashboard/launch.sh

# CLI flags:
python -m dashboard --help
python -m dashboard --compact          # Force compact (5" DSI) layout
python -m dashboard --wide             # Force wide layout
python -m dashboard --no-banner        # Hide ASCII banner
python -m dashboard --no-boot          # Skip boot animation
python -m dashboard --waterfall-only   # Render only the waterfall (no panels)
python -m dashboard --no-real-sdr      # Start with SDR in SIM mode (default is REAL/HackRF ON)
python -m dashboard --refresh 0.25     # Set refresh rate (seconds)
python -m dashboard --config /path/to/dashboard.toml
python -m dashboard --print-config     # Dump resolved config and exit
python -m dashboard --headless         # Run without TUI (logging only)
```

> **Note (v4.7.0):** HackRF real-SDR mode is **ON by default**. The dashboard sets
> `DSLV_DASHBOARD_REAL_SDR=1` at startup. Use `--no-real-sdr` to start in simulated mode.
> The amp (`a` key) is locked out — HackRF One amp is blown, parts on order.

**Web dashboard** (read-only, auto-refresh, accessible from any device on the PiRepo LAN):
```
http://10.42.0.1:8080/
```

The dashboard **auto-launches** at desktop login if installed with `--dashboard`.

### Layout Overview

**Wide mode** (≥ 110 columns):
```
┌──────────────────────────────── BANNER ─────────────────────────────────┐
│ System │ Pipeline │ Hardware │ RF Anomaly                               │
├─────────────────────────────── WATERFALL ───────────────────────────────┤
│ Space Weather │ Storm Tracker                                            │
├──────────────────────────────────────────────────────────────────────────┤
│ Logs │ Notifications                                                      │
├──────────────────────────────── FOOTER ─────────────────────────────────┤
```

**Compact mode** (< 110 columns, or 5" DSI screen, or `--compact`):
```
┌─ System │ Pipeline │ Hardware ─┐
│─ RF Anomaly │ Weather │ Storm ─│
├────────── WATERFALL ───────────┤
│─ Logs │ Notifications ─────────│
├────────────── FOOTER ──────────┤
```

Toggling compact (`c`) rebuilds the layout live without restarting the dashboard.

### Panel Reference

#### System
CPU %, RAM used/total, SoC temperature, CPU governor, Pi throttle flags, system uptime.
Throttle flags light up if the Pi is voltage-clamping or thermally throttling.

#### Pipeline
`systemctl` service state for `dslv-zpdi`, HAL mode (HARDWARE / SIMULATOR), HDF5 packet counters (primary and secondary stream), ingest packet rate.

#### Hardware
HackRF firmware version and USB status, PPS tick age and jitter (from `/dev/pps0`), GPSDO GPS fix status (from NMEA over `/dev/ttyACM0`), chrony stratum and RMS offset.

#### RF Anomaly
Feeds off the waterfall's last spectrum row. Reports peak dBm, peak frequency, estimated noise floor (median), SNR, and count of bins exceeding floor + 10 dB (candidate anomaly bins). Updates every render tick.

#### Waterfall
See the **Waterfall Explained** section below — the most complex panel.

#### Space Weather
NOAA space weather data: geomagnetic K-index, solar flux index, aurora probability. Polled periodically from the NOAA API.

#### Storm Tracker
Active severe weather / storm events relevant to sensor location. Polled from NOAA NWS.

#### Logs
Live-tailing `journalctl -fu dslv-zpdi`. Shows the most recent N lines from the pipeline service. Threaded reader — does not block the dashboard.

#### Notifications
Rotating event ticker: pipeline state changes, keybinding confirmations, dark-humor quips, and glitch events. Also receives error notifications if a panel fails to render (dashboard does not crash — it pushes the error here instead).

#### Footer
Keybinding quick-reference, live UTC timestamp, and a blinking pulse indicator.

---

## Waterfall Explained

The waterfall is a rolling 2D frequency-power display and the primary real-time sensor view.

### What It Shows

```
         ┌── Spectrum view (bar chart of current row + peak-hold) ──┐
         │ █                                                         │
         │ ██  █   ·      ·                                         │
         │ █████  ██       █                                        │
         │─────────────────────────────────────────────────────────│
         │ (newest row — brightest = highest power)                 │
         │ ░▒▒▓▓███▓▒░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░           │
         │ ░░▒▒▓██▓▒▒░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░           │
         │ ░░░▒▓█▓▒░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░           │
         │ (oldest row — scrolls down as new rows arrive)           │
         └──── 80.00 MHz ────────── 100.000 MHz ──── 120.00 MHz ───┘
```

- **X-axis:** Frequency span (lo MHz → center → hi MHz)
- **Y-axis:** Time (newest row at top, scrolling down)
- **Color:** Signal power mapped through the active color palette (floor dBm = dark, ceil dBm = bright)
- **Spectrum view:** Current row rendered as a bar chart; `·` markers show peak-hold (slow decay)

### Data Sources

| Source         | How it works                                                      |
|----------------|-------------------------------------------------------------------|
| `SIM`          | Synthesized spectrum with 3 drifting Gaussian carriers + noise. Runs always when HACKRF is off. |
| `HACKRF`       | Live `hackrf_sweep` subprocess. Streams CSV lines, accumulates a full sweep, publishes via background thread. |
| `HACKRF-WAIT`  | Transitional state — HackRF subprocess started but no sweep received yet. Shows SIM data while waiting. |

Toggle between SIM and HACKRF with `r`. The dashboard auto-detects HackRF at startup via `hackrf_info`; if not present, `r` has no effect.

### Frequency Modes

| Mode     | Default Span | Purpose                                      |
|----------|-------------|----------------------------------------------|
| `SWEEP`  | 20 MHz      | Wideband survey — see the whole neighborhood |
| `NARROW` | 5 MHz       | Mid-range — target a band of interest        |
| `SCOPE`  | 2 MHz       | Narrow — zoom into a single signal           |

Cycle with `m`. Switching mode snaps the span to the mode's default if it's currently outside that mode's range. Center frequency is unchanged.

### Color Palettes

Three palettes cycle with `p`:

| # | Name          | Colors                                  |
|---|---------------|-----------------------------------------|
| 0 | Classic Heat  | Black → deep blue → teal → green → yellow → red → white |
| 1 | Plasma        | Deep purple → violet → orange → yellow  |
| 2 | Viridis       | Purple → teal → green → yellow          |

### Floor and Ceiling (dBm Range)

The floor and ceiling define the dBm window that maps to the color palette's 0–1 range:
- Signals at or below **floor** → darkest color (invisible)
- Signals at or above **ceil** → brightest color (white/yellow peak)
- Signals in between → interpolated color

Adjust with `[`/`]` (floor) and `{`/`}` (ceil) in 5 dBm steps. The floor is clamped to at least 5 dBm below the ceiling and vice versa, so they can never cross.

**Typical starting points:**
- Quiet rural RF environment: floor `-90`, ceil `-30`
- Urban/noisy RF: floor `-80`, ceil `-20`
- Very strong nearby transmitter: floor `-60`, ceil `0`

### Gain Controls (HACKRF mode only)

| Control | Range        | Steps                        | Effect                             |
|---------|-------------|------------------------------|------------------------------------|
| LNA     | 0–40 dB     | 0, 8, 16, 24, 32, 40        | RF front-end amplification         |
| VGA     | 0–62 dB     | 0, 8, 16, 24, 32, 40, 48, 56, 62 | Baseband (IF) gain           |
| AMP     | on/off      | —                            | HackRF internal +14 dB pre-amp (use with care — can saturate) |

Changing any gain value immediately restarts the `hackrf_sweep` subprocess with the new parameters. There is a brief `HACKRF-WAIT` transition (~1–2 rows) while the new sweep starts.

### Peak Hold

The spectrum view maintains a per-bin peak-hold buffer that decays at 2% per frame. Strong transients leave a visible `·` marker in the spectrum even after the signal drops. This is useful for spotting intermittent bursts.

---

## Keybinding Reference

All keys are case-insensitive unless noted.

### Navigation & Control

| Key         | Action                                        |
|-------------|-----------------------------------------------|
| `q`         | Quit dashboard (pipeline continues running)   |
| `Space`     | Pause / resume rendering (pipeline unaffected)|
| `h`         | Toggle ASCII banner (frees vertical space)    |
| `c`         | Toggle compact / wide layout                  |

### Waterfall — Frequency

| Key         | Action                                              |
|-------------|-----------------------------------------------------|
| `<` or `←` | Tune center frequency down (10% of current span)   |
| `>` or `→` | Tune center frequency up (10% of current span)     |
| `,`         | Fine-tune down (1% of current span)                |
| `.`         | Fine-tune up (1% of current span)                  |
| `z` or `↑` | Zoom in (halve span)                               |
| `x` or `↓` | Zoom out (double span)                             |
| `m`         | Cycle mode: SWEEP → NARROW → SCOPE → SWEEP          |

### Waterfall — Display

| Key    | Action                                          |
|--------|-------------------------------------------------|
| `s`    | Toggle spectrum view (bar chart above waterfall)|
| `p`    | Cycle color palette (Heat → Plasma → Viridis)   |
| `[`    | Floor down −5 dBm (show weaker signals)         |
| `]`    | Floor up +5 dBm (suppress noise floor)          |
| `{`    | Ceiling down −5 dBm                             |
| `}`    | Ceiling up +5 dBm                               |

### Waterfall — SDR / Gain (HACKRF mode)

| Key    | Action                                                    |
|--------|-----------------------------------------------------------|
| `r`    | Toggle SIM ↔ HACKRF live SDR mode                        |
| `g`    | Cycle LNA gain (0 → 8 → 16 → 24 → 32 → 40 → 0 dB)       |
| `v`    | Cycle VGA (baseband) gain (0–62 dB steps)                 |
| `+`    | LNA gain up one step                                      |
| `-`    | LNA gain down one step                                    |
| `a`    | Toggle HackRF internal amp (±14 dB, use carefully)        |
| `d`    | Cycle demodulation mode (RAW-SWEEP / AM / NFM / WFM / LSB / USB / CW) |

---

## Network Configuration (PiRepo Hotspot)

The Pi 5 acts as a Wi-Fi access point (`PiRepo`) for swarm node communication.

### Activate the hotspot

```bash
sudo cp config/PiRepo.nmconnection /etc/NetworkManager/system-connections/
sudo chmod 600 /etc/NetworkManager/system-connections/PiRepo.nmconnection
sudo nmcli connection reload
sudo nmcli connection up PiRepo
```

The Pi holds static IP `10.42.0.1/24`. Connected devices receive `10.42.0.x` via DHCP.

### Connect the Pixel 9 Pro XL

1. Open **Settings → Network → Wi-Fi** on the Pixel 9 Pro XL (GrapheneOS).
2. Connect to `PiRepo`.
3. The device will receive a `10.42.0.x` IP automatically.
4. Node telemetry is sent to `http://10.42.0.1:5775/api/v1/ingest`.
5. The web dashboard is viewable at `http://10.42.0.1:8080/`.

### Node Receiver API (SPEC-014)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ingest` | POST | JSON telemetry from any swarm node |
| `/api/v1/ingest/radoneye` | POST | EcoSense RadonEye Pro staging (SPEC-015 pending) |
| `/api/v1/health` | GET | Service health + HDF5 writer stats |

**RadonEye Pro integration path** (future — SPEC-015 pending):
```json
POST http://10.42.0.1:5775/api/v1/ingest/radoneye
{
  "source": "EcoSense_RadonEye_Pro",
  "radon_bq_m3": 12.5,
  "timestamp_utc": 1748560000.0,
  "unit_id": "RE200-XXXXXX"
}
```
Packets stage to `output/secondary/radoneye_staging.jsonl` until SPEC-015 is ratified.

---

## Pipeline Operation

### Service Chain

Services start in dependency order (managed by systemd):

```
dslv-zpdi-tuning.service         (Nice=-5, I/O realtime scheduling)
    ↓ After=
dslv-zpdi-hackrf-init.service    [NEW] (wakes HackRF via hackrf_info; non-fatal if absent)
    ↓ Before=
dslv-zpdi-preflight.service      (hardware checks: HackRF, PPS, chrony)
    ↓ After=
dslv-zpdi.service                (main_pipeline.py — runs indefinitely)
    ↓ After=
dslv-zpdi-node-receiver.service  [NEW] (Flask receiver on port 5775)
dslv-zpdi-webdash.service        [NEW] (HTML dashboard on port 8080)
```

**Enable new services (run once after install):**
```bash
for svc in dslv-zpdi-hackrf-init dslv-zpdi-node-receiver dslv-zpdi-webdash; do
    sudo cp config/${svc}.service /etc/systemd/system/
done
sudo systemctl daemon-reload
sudo systemctl enable --now dslv-zpdi-hackrf-init dslv-zpdi-node-receiver dslv-zpdi-webdash
```

```bash
# Check full chain status:
systemctl status dslv-zpdi-tuning dslv-zpdi-hackrf-init dslv-zpdi-preflight dslv-zpdi \
                 dslv-zpdi-node-receiver dslv-zpdi-webdash

# Follow live pipeline logs:
journalctl -u dslv-zpdi -f

# Restart pipeline only:
sudo systemctl restart dslv-zpdi

# Restart full chain:
sudo systemctl restart dslv-zpdi-tuning
```

### Simulator Mode

When hardware is absent or during development, run in simulator mode:

```bash
# Toggle simulator on/off:
bash tools/toggle_simulator.sh

# Or set env directly:
DSLV_PIPELINE_SIMULATOR=1 python -m dslv_zpdi
```

In simulator mode:
- `SimulatedHAL` generates deterministic synthetic payloads (Gaussian noise + drifting carriers)
- No PPS edge wait — paced by `time.sleep()`
- Full Layer 2 coherence scoring and Layer 3 HDF5 output still operate
- Dashboard waterfall shows `SIM` source label

If hardware initialization fails (HackRF not detected, PPS device missing), the pipeline **automatically falls back to simulator** and logs a warning. Check `journalctl -u dslv-zpdi` if you suspect an unintended fallback.

### Baseline Learning FSM (SPEC-009)

The coherence engine runs a state machine before committing data to the PRIMARY stream:

```
NOT_STARTED → LEARNING (collecting baseline for baseline_duration_hours)
            → LOCKED   (PRIMARY stream active, coherence-scored)
```

- During LEARNING, all data goes to SECONDARY stream only.
- Baseline state persists to `paths.baseline_state` — a reboot does not reset it.
- Force-reset: `rm /var/lib/dslv_zpdi/baseline.json` then `sudo systemctl restart dslv-zpdi`.

### Health Endpoint

The pipeline writes `/run/dslv-zpdi/health.json` every few seconds. Read it to check status without the dashboard:

```bash
cat /run/dslv-zpdi/health.json | python -m json.tool
```

Fields: `node_id`, `hal_mode`, `baseline_state`, `pps_jitter_ns`, `chrony_offset_us`, `coherence_scores`.

---

## Pre-Flight Check

```bash
source .venv/bin/activate

# Core test suite
pytest tests/

# SPEC-ID compliance (all modules must reference a SPEC-ID)
python tools/orphan_checker.py

# Timing health snapshot
python tools/check_timing.py

# Hardware pre-flight (non-fatal, checks HackRF / PPS / chrony)
bash tools/preflight.sh
```

---

## Troubleshooting

### Dashboard crashes immediately on launch

**Likely cause:** Python environment missing `rich`.

```bash
pip install rich
# Or:
source .venv/bin/activate
python -m dashboard
```

### Dashboard crashes when I press a key

**Fixed in Rev 4.6.0.** Update to latest and relaunch. Specific fixes applied:
- `Space` (pause) no longer crashes if the Notifications panel is disabled.
- `c` (compact toggle) no longer crashes if the Waterfall panel is disabled.
- Layout rebuilds (`c`, `h`) now correctly propagate to the Rich Live context.

### Dashboard renders blank after pressing `c` or `h`

**Fixed in Rev 4.6.0.** The layout rebuild now calls `live.update()` so the new structure is visible immediately.

### Waterfall is stuck on `SIM` even after pressing `r`

- HackRF is not detected. Run `hackrf_info` — if it fails, check USB connection.
- `hackrf_sweep` binary not in PATH. Install: `sudo apt install hackrf`.
- If HackRF is detected but sweep fails, check the error label in the waterfall title bar.

### Pipeline running in SIMULATOR when I expect HARDWARE

Check the pipeline log for the fallback warning:

```bash
journalctl -u dslv-zpdi | grep -i "HardwareHAL\|simulator\|fallback"
```

Common causes:
- HackRF not plugged in when service started
- `/dev/pps0` does not exist (dtoverlay not loaded — add to `/boot/firmware/config.txt` and reboot)
- LBE-1421 not powered or USB-C not seated

### PPS device missing (`/dev/pps0`)

```bash
# Check overlay is loaded:
grep pps /boot/firmware/config.txt
# Expected: dtoverlay=pps-gpio,gpiopin=18,assert_falling_edge=0

# Check kernel module:
lsmod | grep pps
# Expected: pps_gpio, pps_core

# If missing, add overlay and reboot:
echo "dtoverlay=pps-gpio,gpiopin=18,assert_falling_edge=0" | sudo tee -a /boot/firmware/config.txt
sudo reboot
```

### HDF5 files not being written

1. Check output directory permissions:
   ```bash
   ls -ld /home/dynogator/dslv-zpdi/output/
   # Must be writable by the pipeline user
   sudo mkdir -p /home/dynogator/dslv-zpdi/output/{primary,secondary}
   sudo chown -R dynogator:dynogator /home/dynogator/dslv-zpdi/output/
   ```
2. Check if `h5py` is installed: `python -c "import h5py; print(h5py.__version__)"`.
   If not: `pip install h5py`.
3. Check disk space: `df -h`.

### Baseline state not persisting across reboots

```bash
# Check state directory permissions:
ls -ld /var/lib/dslv_zpdi/
sudo mkdir -p /var/lib/dslv_zpdi
sudo chown dynogator:dynogator /var/lib/dslv_zpdi

# Verify baseline file:
cat /var/lib/dslv_zpdi/baseline.json
```

### Timing monitor always shows UNHEALTHY

- Check chrony: `chronyc tracking` — look for "Stratum" and "RMS offset".
- If chrony is not running: `sudo systemctl start chrony`.
- The jitter threshold is `max_pps_jitter_ns` in `config/deployment.yaml` (default 1000 ns). Raise this temporarily if GPSDO is still acquiring lock.

### Config changes have no effect

- The pipeline reads `config/deployment.yaml` at startup. After editing, restart the service:
  ```bash
  sudo systemctl restart dslv-zpdi
  ```
- The dashboard reads `~/.config/dslv-zpdi/dashboard.toml` at launch. Restart the dashboard.
- Environment variables override YAML. Check for stale `DSLV_*` exports in your shell or service override files (`systemctl edit dslv-zpdi`).

### Invalid config values in `dashboard.toml`

The dashboard enforces safe bounds on load. If you set a value out of range, it is silently clamped to the nearest safe value and a warning is printed to stderr. Examples:
- `refresh = 0` → clamped to `0.1`
- `history = 3` → clamped to `10`
- `center_hz = 0` → clamped to `1_000_000`
- `mode = "TURBO"` → reset to `"SWEEP"`

Run `python -m dashboard --print-config` to see the resolved (post-clamp) config.

---

## Hardware Agnosticism Standard (SPEC-004A.2)

The Pi 5 + HackRF + LBE-1421 stack is the Phase 2A reference. Alternative hardware is permitted if it meets:

1. **External 10 MHz reference input** to hardware-lock the SDR's ADC sampling clock
2. **1 PPS hardware interrupt** (GPIO, SDP, or dedicated timing input)
3. **Sufficient compute** for Kuramoto coherence math without frame drops

### Permissible Alternatives

- Nvidia Jetson AGX Orin + USRP B200 + GPSDO
- Intel NUC + LimeSDR + M.2 timing card
- Any Linux SBC + CLKIN-capable SDR + GPS-disciplined 10 MHz source

### Tier 2 / Testbed (RTL-SDR)

The RTL-SDR (v3/v4) is relegated to Tier 2 / Testbed only. It lacks external clock input and cannot achieve hardware-level phase coherence. **RTL-SDR data MUST NOT enter the Tier 1 primary stream.**

---

## LBE-1421 GPSDO Advantages (Rev 4.2)

The Leo Bodnar LBE-1421 supersedes the previously specified Mini GPSDO:

| Feature         | LBE-1421                        | Mini GPSDO (Deprecated)              |
|-----------------|---------------------------------|--------------------------------------|
| Power/Data      | USB-C (ruggedized)              | Mini-USB (fragile)                   |
| Telemetry       | NMEA over virtual serial        | None                                 |
| PPS Output      | 3.3 V CMOS square wave          | Varies (may require level-shifter)   |
| GPS Fix Check   | Software via `/dev/ttyACM0`     | Hardware LED only                    |

The 3.3 V CMOS output is natively matched to the Pi 5 RP1 southbridge — no voltage divider or level-shifter required.

---

## Documentation Index

| File                                   | Contents                                              |
|----------------------------------------|-------------------------------------------------------|
| `MASTER_SPEC.md`                       | Canonical SPEC-ID law layer                           |
| `PHASE_2A_TIER_1_BUILD_SHEET.md`       | Step-by-step assembly and wiring guide                |
| `PHASE_2A_HARDWARE_BUILD_LIST.md`      | Procurement list with verified links                  |
| `docs/LBE-1421_WIRING.md`             | Detailed wiring harness documentation                 |
| `docs/HARDWARE_CHANGE_JUSTIFICATION.md`| Phase 2A hardware pivot rationale (SPEC-UPDATE-PHASE-2A-LBE-1421) |
| `docs/RF_MAGNETIC_SHIELDING.md`        | Cyberdeck chassis shielding design                    |
| `docs/validation-logs/`               | Live evidence artifacts (pytest, hardware, system)    |
| `specs/`                               | Individual SPEC-*.md implementation specs             |

---

## Scientific Justification

### The USB Jitter Problem (Deprecated Architecture)

The previous IT Network approach (Intel i210-T1 + RTL-SDR) had a fatal flaw:
- SDR sampled with a free-running crystal
- USB bus introduced variable microsecond delays
- OS timestamped packets *upon USB arrival*, not when the RF wave reached the antenna

This mathematically invalidated true phase coherence across distributed nodes.

### The RF Metrology Solution (Current Architecture)

By locking the HackRF's ADC directly to the GPS constellation via 10 MHz CLKIN:
- Phase relationships are preserved at the analog level
- USB jitter affects only data-transfer latency, not sample timing
- Every IQ sample carries GPS-disciplined phase information
- Phase alignment across distributed nodes is provable and verifiable

---

## Project Governance

- **Owner:** Joseph R. Fross (Resonant Genesis LLC / DynoGator Labs)
- **Repository:** https://github.com/DynoGator/dslv-zpdi
- **License:** MIT
- **SPEC compliance:** All modules carry SPEC-ID docstrings. `tools/orphan_checker.py` enforces compliance at commit time.
