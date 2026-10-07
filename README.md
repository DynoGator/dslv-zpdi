# DSLV-ZPDI (Distributed Sensor Locational Vectoring)

**Project Phase:** Phase 2B (Radon Validation Metrology Stack — Tier 2) with Tier-1 hardware pivot
**Revision:** Rev 5.4.0 — Phase 2A/2B: Capability-based Tier-1 RF metrology pivot to PlutoSDR+ class hardware (HamGeek AD9363), LBE-1421 GPSDO timing authority, composed HAL, and tamper-evident HDF5 manifests
**Date:** 2026-08-06
**Status:** Beta — PlutoSDR+ backend implemented, composed HAL and timing authority decoupled, HackRF remains Tier-1 under host_timestamp + GPSDO + adequate compute, simulator validation passing, hardware qualification pending physical verification gates.

---

## Overview

DSLV-ZPDI is a multi-modal Signals Intelligence (SIGINT) network that translates anomalous multi-spectrum phenomena into institutional-grade, GPS-disciplined HDF5 telemetry.

**Phase 2A RF Metrology Pivot:** The architecture transitions from IT Network Timing (PTP/i210-T1) to RF Metrology Timing. For the adc_ext_ref coherence class, this achieves hardware-level ADC phase coherence by injecting a reference directly into the SDR front-end — making USB jitter irrelevant to sample timing. Other Tier-1 nodes use host_timestamp coherence.

---

## ☠️ Toolchain & Export Controls ☢️

~~~
            _.-^^---....,,--_
        _--                    --_
       <      PHASE COHERENCE     >)
       |       FAILURE, 1954      |
        \._      (colorized)    _./
           ```--. . , ; .--'''
                 | |   |
              .-=||  | |=-.
              `-=#$%&%$#=-'
                 | ;  :|
        _____.,-#%&$@%#&#~,._____

   THIS IS WHAT TWO NODES DISAGREEING ABOUT TIME LOOKS LIKE.
   LOCK YOUR CLOCKS. DUCK AND COVER IS NOT A TIMING STRATEGY.
~~~


*This institutional-grade FPGA timing pipeline was synthesized and developed using:*
- **Vivado 2022.2 (Zynq-7000-only image)** 

> **WARNING:** *AMD/Xilinx Vivado is dual-use, export-controlled technology (EAR). You will need an authorized, compliance-cleared AMD account to download the toolchain required to build this bitstream. Unauthorized distribution is a violation of federal export laws.*

---

## Architecture

~~~
                , - ~ ~ ~ - ,
            , '       |       ' ,
          ,       \   |   /       ,
         ,         \  |  /         ,
         ,   ----.   (o)   .----   ,
         ,         /  |  \         ,
          ,       /   |   \       ,
            ,         |         ,
              ' - , _ _ _ ,  '

        KCET-ATLAS COHERENCE ENGINE
     "Splitting hairs, not atoms, since 2026."
~~~


```
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 1 — INGESTION                                             │
│  HardwareHAL (PlutoSDR+ + LBE-1421) or SimulatedHAL            │
│  PPS edge detection · NMEA GPS fix · SDR IQ samples             │
└────────────────────────┬─────────────────────────────────────────┘
                         │ Payload (JSON)
┌────────────────────────▼─────────────────────────────────────────┐
│  LAYER 2 — CORE  ( 🍄 OPHIOCORDYCEPS 🍄 )                        │
│                                                                  │
│            .-._                                                  │
│           {_} _.-_      KCET-ATLAS Kuramoto coherence engine     │
│          .-. { _}       (SPEC-006/009)                           │
│          `-' .-.        Baseline FSM:                            │
│              `-'        NOT_STARTED → LEARNING → LOCKED          │
│                                                                  │
│  Trust wiring · Swarm integrity · Resistance is futile           │
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

The reference stack for Phase 2A is the **topdog** node. 
Other nodes exist with different coherence classes (see `config/nodes.yaml`).

### Node Table

| Node ID | Role | Compute | Front-End | Clock Authority | Coherence |
|---|---|---|---|---|---|
| **topdog** | alpha | Pi 5 16GB, Argon Neo | HamGeek PlutoSDR+ (AD9363) | LBE-1421 GPSDO | adc_ext_ref |
| **ravenpi** | tier1_contributor | Pi 5 8GB | HackRF One (amp blown) | LBE-1421 GPSDO | host_timestamp |
| **cm5-poe** | alpha_capable | Pi CM5 8GB | HackRF One r10 | LBE-1421 GPSDO | host_timestamp |
| **pixel9** | mobile_contributor | Pixel 9 Pro XL | HackRF One r10 | None | none |

### Per-Node Wiring

**topdog (Reference Stack):**
- **RF Phase Lock (ADC slave):** LBE-1421 `Out2` → 15M/EXCLK port on SDR. Hardware ADC is phase-locked. (Frequency is configured per-node).
- **OS Timestamping:** LBE-1421 `Out1` (1 PPS) → Pi GPIO + ground on Adafruit cyberdeck HAT breakout (currently assumed GPIO 8 for dtoverlay).
- **Power & Telemetry:** LBE power/JTAG → Pi USB 2.0.
- **SDR Data & Power:** SDR debug USB → Pi USB 3.0; SDR Ethernet → Pi Ethernet; SDR OTG → UPS 5 V rail. SDR PPS port is empty.
- **RF Input:** 4x Great Scott Gadgets ANT500.

**ravenpi / cm5-poe:**
- **OS Timestamping:** LBE-1421 `Out1` (1 PPS) → Pi GPIO. (host_timestamp coherence).
- **SDR Data:** USB to HackRF. HackRF One stock has no EXT_REF_CLK, thus no LBE Out2 connection.

## Installation & Deployment

### Prerequisites

**Python runtime**
- Supported source/runtime versions: Python 3.10 through 3.14.
- Recommended local development version: Python 3.13.
- Container validation version: Python 3.14.
- `requirements.txt` is generated from `pyproject.toml` using Python 3.13.

**Core hardware (Tier 1 Anchor)**
- topdog, Pi 5 16 GB, HamGeek Pluto+ AD9363-class, 4x ANT500, LBE-1421 Out2 to 15M/EXCLK, frequency unset.
- SMA Male-to-Male 50 Ω coax, ≤ 1 ft
- Female-to-female jumper wire (2.54 mm pitch) for PPS
- GPS antenna with clear sky view
- 10" Lenovo HDMI touchscreen display (800×480) — optional; dashboard runs headless if absent

**Mobile node (optional but supported)**
- Google Pixel 9 Pro XL running GrapheneOS + Termux + proot-distro (Debian)
- Runs the full Tier-2 stack (`supervisor.sh` manages three services):
  - `zpdi_mobile_node.py` — sensor collection via termux-sensor → HDF5 + WSS
  - `tier1_ingestion_server.py` — local WSS ingest receiver (port 8443)
  - `tools/dashboard/web_server.py` — status dashboard (port 8080)
- Install: run `bash install_zpdi_mobile.sh` from Termux (see Mobile Node section below)

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
echo "dtoverlay=pps-gpio,gpiopin=8,assert_falling_edge=0" | sudo tee -a /boot/firmware/config.txt
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

# PlutoSDR+ detected via IIO
python -c "import iio; print(iio.Context('ip:192.168.2.1').name)"

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
  max_pps_jitter_ns:         5000.0        # Quarantine threshold
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
| `DSLV_RECEIVER_HOST`        | Node receiver bind host                | `10.42.0.1`                    |
| `DSLV_WEBDASH_HOST`         | Web dashboard bind host                | `10.42.0.1`                    |
| `ZPDI_SERVER_HOST`          | Tier-1 WSS ingest bind host            | `10.42.0.1`                    |

Network listeners default to `127.0.0.1`. The bundled field systemd units bind
the node receiver and dashboard to `10.42.0.1`; set `ZPDI_SERVER_HOST`
explicitly before exposing the WebSocket ingest server to mobile nodes.

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
mode      = "SWEEP"       # SWEEP (10–20 MHz) | NARROW (5 MHz) | SCOPE (2 MHz)
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
- `DSLV_DASHBOARD_REAL_SDR=1` — start with live PlutoSDRplus input (same as `--real-sdr` flag)
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
python -m dashboard --compact          # Force compact (10" Lenovo HDMI touchscreen) layout
python -m dashboard --wide             # Force wide layout
python -m dashboard --no-banner        # Hide ASCII banner
python -m dashboard --no-boot          # Skip boot animation
python -m dashboard --waterfall-only   # Render only the waterfall (no panels)
python -m dashboard --no-real-sdr      # Start with SDR in SIM mode (default is REAL/PlutoSDRplus ON)
python -m dashboard --refresh 0.25     # Set refresh rate (seconds)
python -m dashboard --config /path/to/dashboard.toml
python -m dashboard --print-config     # Dump resolved config and exit
python -m dashboard --headless         # Run without TUI (logging only)
```

> **Note (v5.0.0):** PlutoSDRplus real-SDR mode is **ON by default**. The dashboard sets
> `DSLV_DASHBOARD_REAL_SDR=1` at startup. Use `--no-real-sdr` to start in simulated mode.
> The amp (`a` key) is locked out on node `ravenpi` — HackRF amp is blown, parts on order.

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

**Compact mode** (< 110 columns, or 10" Lenovo HDMI touchscreen screen, or `--compact`):
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
PlutoSDRplus firmware version and USB status, PPS tick age and jitter (from `/dev/pps0`), GPSDO GPS fix status (from NMEA over `/dev/ttyACM0`), chrony stratum and RMS offset.

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

#### Advanced Demodulation Suite
A standalone, feature-rich TUI pop-out module (`demod_app.py`) for comprehensive RF demodulation.
- **Base Capabilities:** Live SNR/Lock metrics, spectrum visualization, decoded payload telemetry (e.g., ADS-B), and full manual radio control (Freq, BW, Gain, Squelch) via keyboard shortcuts.
- **Listen Mode:** Payload audio can be routed to the system's default audio device via the `L` key.
- **Restricted Features (PIN Protected):** Sensitive features are locked by default to prevent accidental transmission or unlawful use. Press `*` or `Ctrl+X` to trigger the obfuscated security prompt. Enter PIN `1988` to unlock:
  - **MIMO TX:** Transmit capability unlock.
  - **Fox Hunting (Vector/TDOA):** Estimates target bearing and distance using Time Difference of Arrival and RSSI vectoring.
  - **Frequency Hopping Monitor:** Dynamically flags and tracks fast-hopping signals across the spectrum analyzer.

#### Footer
Keybinding quick-reference, live UTC timestamp, and a blinking pulse indicator.

---

## Waterfall Explained

~~~
        ______________________________________________________
       |  CONELRAD  ::  CIVIL DEFENSE RADIO  ::  EST. 1953    |
       |                                                      |
       |   540    640     800    1000    1240    1400  kHz    |
       |    |     (CD)     |       |      (CD)     |          |
       |    |______|_______|_______|_______|_______|          |
       |                                                      |
       |   IN THE EVENT OF ACTUAL ANOMALY, LEAVE THE RF       |
       |   SPECTRUM EXACTLY AS WEIRD AS YOU FOUND IT.         |
       |______________________________________________________|
~~~


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
| `SIM`          | Synthesized spectrum with 3 drifting Gaussian carriers + noise. Runs always when PlutoSDRplus is off. |
| `PlutoSDRplus` / `PLUTO` | Live SDR subprocess or IIO context. Streams data, accumulates a full sweep, publishes via background thread. |
| `SDR-WAIT`         | Transitional state — SDR initialized but no sweep received yet. Shows SIM data while waiting. |

Toggle between SIM and PlutoSDRplus with `r`. The dashboard auto-detects PlutoSDRplus at startup via `PlutoSDRplus_info`; if not present, `r` has no effect.

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

### Gain Controls (SDR backend)

The active SDR backend (PlutoSDR+ / PlutoSDRplus legacy) applies its own gain model.

| Control | Range        | Steps                        | Effect                             |
|---------|-------------|------------------------------|------------------------------------|
| LNA     | 0–40 dB     | 0, 8, 16, 24, 32, 40        | RF front-end amplification (HackRF model) |
| VGA     | 0–62 dB     | 0, 8, 16, 24, 32, 40, 48, 56, 62 | Baseband (IF) gain (HackRF model) |
| AMP     | on/off      | —                            | HackRF internal +14 dB pre-amp (use with care — can saturate) |

Changing any gain value immediately restarts the underlying sweep subprocess. There is a brief `SDR-WAIT` transition (~1–2 rows) while the new sweep starts.

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

### Waterfall — SDR / Gain

| Key    | Action                                                    |
|--------|-----------------------------------------------------------|
| `r`    | Toggle SIM ↔ SDR live mode                                |
| `g`    | Cycle LNA gain (0 → 8 → 16 → 24 → 32 → 40 → 0 dB)       |
| `v`    | Cycle VGA (baseband) gain (0–62 dB steps)                 |
| `+`    | LNA gain up one step                                      |
| `-`    | LNA gain down one step                                    |
| `a`    | Toggle PlutoSDRplus internal amp (±14 dB, use carefully)        |
| `d`    | Cycle demodulation mode (RAW-SWEEP / AM / NFM / WFM / LSB / USB / CW) |

### Waterfall — Demodulation & MIMO

| Key    | Action                                                    |
|--------|-----------------------------------------------------------|
| `f`    | Enter numerical frequency directly (hit Enter to confirm) |
| `1`-`5`| Select predefined demodulation profiles (ADS-B, FM, AM, EMS, TV) |
| `Enter`| Toggle Demodulation active state                          |
| `T`    | Toggle MIMO TX Mode (CAUTION: Restricted activity)        |

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

### Mobile Node — Pixel 9 Pro XL (GrapheneOS / PRoot)

The mobile device runs a full self-contained Tier-2 stack inside a Debian proot.

**One-shot install (run from Termux, not inside proot):**
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/DynoGator/dslv-zpdi/main/install_zpdi_mobile.sh)
```
Or if already cloned:
```bash
bash /root/dslv-zpdi/install_zpdi_mobile.sh
```

This (Rev 5) installer:
1. Installs Debian proot, `hdf5-tools`, all Python deps via `pip install -e ".[dev]"`
2. Generates a complete `.env` with fresh AES-256-GCM + HMAC-SHA256 keys
3. Creates `data/`, `logs/`, `output/primary`, `output/secondary`
4. Copies `termux-boot/99-start-zpdi.sh` → `~/.termux/boot/` for auto-boot
5. Runs the full test suite as a smoke check

**Services managed by `supervisor.sh`:**

| Service | Port | Purpose |
|---|---|---|
| `tier1_ingestion_server.py` | 8443 (WS) | Receives sensor payloads from mobile daemon |
| `zpdi_mobile_node.py` | — | Polls termux-sensor, writes HDF5 + SQLite, forwards via WSS |
| `tools/dashboard/web_server.py` | 8080 (HTTP) | Status dashboard viewable on LAN |

**Manual start (from inside proot):**
```bash
cd /root/dslv-zpdi
h5clear -s data/zpdi_stream.h5 2>/dev/null || true
set -a && source .env && set +a
source .venv/bin/activate
nohup bash supervisor.sh >> logs/supervisor.log 2>&1 &
```

**Status check:**
```bash
tail -1 /root/dslv-zpdi/logs/health.jsonl | python3 -m json.tool
# Healthy: sensor_alive=true, wss_connected=true, gps_fix present
```

**Web dashboard URL** (on device or LAN):
```
http://<device-ip>:8080/
```

**Auto-boot (Termux:Boot):**
Give Termux and Termux:Boot unrestricted battery usage in Android Settings.
The boot script acquires a wake-lock, clears stale locks, and launches
`supervisor.sh` in an independent proot session.

### Node Receiver API (SPEC-014)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ingest` | POST | JSON telemetry from any swarm node (legacy HTTP) |
| `/api/v1/ingest/radoneye` | POST | EcoSense RadonEye Pro staging (SPEC-015) |
| `/api/v1/health` | GET | Service health + HDF5 writer stats |
| `ws://<host>:8443/ingest` | WS | WebSocket ingest — Tier-2 mobile daemon primary path |

---

## Pipeline Operation

### Service Chain

Services start in dependency order (managed by systemd):

```
dslv-zpdi-tuning.service         (Nice=-5, I/O realtime scheduling)
    ↓ After=
dslv-zpdi-preflight.service      (hardware checks: PlutoSDR+, PPS, chrony)
    ↓ After=
dslv-zpdi.service                (main_pipeline.py — runs indefinitely)
    ↓ After=
dslv-zpdi-node-receiver.service  [NEW] (Flask receiver on port 5775)
dslv-zpdi-webdash.service        [NEW] (HTML dashboard on port 8080)
```

**Enable new services (run once after install):**
```bash
for svc in dslv-zpdi-node-receiver dslv-zpdi-webdash; do
    sudo cp config/${svc}.service /etc/systemd/system/
done
sudo systemctl daemon-reload
sudo systemctl enable --now dslv-zpdi-node-receiver dslv-zpdi-webdash
```

```bash
# Check full chain status:
systemctl status dslv-zpdi-tuning dslv-zpdi-preflight dslv-zpdi \
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

If hardware initialization fails (PlutoSDRplus not detected, PPS device missing), the pipeline **automatically falls back to simulator** and logs a warning. Check `journalctl -u dslv-zpdi` if you suspect an unintended fallback.

### Baseline Learning FSM (SPEC-009)

*72 hours of learning before it trusts you. The FSM has been hurt before.*

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

# Hardware pre-flight (non-fatal, checks PlutoSDR+ / PPS / chrony)
bash tools/preflight.sh
```

---

## Troubleshooting

~~~
     .-----------------------------------------.
     |  *************************************  |
     |  *              FALLOUT              *  |
     |  *              SHELTER              *  |
     |  *           _____________           *  |
     |  *           \   |   |   /           *  |
     |  *             \  |   |  /           *  |
     |  *              \ |   | /            *  |
     |  *          ----+--+--+----          *  |
     |  *              / |   | \            *  |
     |  *             /  |   |  \           *  |
     |  *           /___|___|___\           *  |
     |  *                                   *  |
     |  *    CAPACITY: 1 GPSDO, 4 NERVES    *  |
     |  *************************************  |
     '-----------------------------------------'
~~~


### Dashboard crashes immediately on launch

**Likely cause:** Python environment missing `rich`.

```bash
pip install rich
# Or:
source .venv/bin/activate
python -m dashboard
```

### Dashboard crashes when I press a key

**Fixed in Rev 5.0.0.** Update to latest and relaunch. Specific fixes applied:
- `Space` (pause) no longer crashes if the Notifications panel is disabled.
- `c` (compact toggle) no longer crashes if the Waterfall panel is disabled.
- Layout rebuilds (`c`, `h`) now correctly propagate to the Rich Live context.

### Dashboard renders blank after pressing `c` or `h`

**Fixed in Rev 5.0.0.** The layout rebuild now calls `live.update()` so the new structure is visible immediately.

### Waterfall is stuck on `SIM` even after pressing `r`

- PlutoSDR+ is not reachable at `ip:192.168.2.1`. Verify the network link and run `iio_info -u ip:192.168.2.1`.
- Legacy HackRF only: run `hackrf_info` — if it fails, check USB connection.
- If the SDR is detected but sweep fails, check the error label in the waterfall title bar.

### Pipeline running in SIMULATOR when I expect HARDWARE

Check the pipeline log for the fallback warning:

```bash
journalctl -u dslv-zpdi | grep -i "HardwareHAL\|simulator\|fallback"
```

Common causes:
- PlutoSDR+ not reachable at `ip:192.168.2.1` when service started
- `/dev/pps0` does not exist (dtoverlay not loaded — add to `/boot/firmware/config.txt` and reboot)
- LBE-1421 not powered or USB-C not seated

### PPS device missing (`/dev/pps0`)

```bash
# Check overlay is loaded:
grep pps /boot/firmware/config.txt
# Expected: dtoverlay=pps-gpio,gpiopin=8,assert_falling_edge=0

# Check kernel module:
lsmod | grep pps
# Expected: pps_gpio, pps_core

# If missing, add overlay and reboot:
echo "dtoverlay=pps-gpio,gpiopin=8,assert_falling_edge=0" | sudo tee -a /boot/firmware/config.txt
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
- The jitter threshold is `max_pps_jitter_ns` in `config/deployment.yaml` (default 5000 ns). Raise this temporarily if GPSDO is still acquiring lock.

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

The Pi 5 + PlutoSDR+ + LBE-1421 stack is the Phase 2A/2B reference. Alternative hardware is permitted if it meets:

1. **External 10 MHz reference input** to hardware-lock the SDR's ADC sampling clock
2. **1 PPS hardware interrupt** (GPIO, SDP, or dedicated timing input)
3. **Sufficient compute** for Kuramoto coherence math without frame drops

### Permissible Alternatives

- Nvidia Jetson AGX Orin + USRP B200 + GPSDO
- Intel NUC + LimeSDR + M.2 timing card
- Any Linux SBC + CLKIN-capable SDR (like PlutoSDR+) + GPS-disciplined 10 MHz source

### Tier 2 / Mobile Nodes (Pixel 9 Pro XL)

The **Pixel 9 Pro XL (GrapheneOS)** is fully integrated as a Tier 2 mobile swarm node. It runs the Termux/PRoot telemetry daemon (`zpdi_mobile_node`) and contributes secondary stream telemetry (magnetometer, GPS, camera orientation hashes) directly into the Tier 1 ingestion pipeline over the `10.42.0.1:8080` local dashboard network.

*Note: The RTL-SDR (v3/v4) is also relegated to Tier 2 / Testbed only as it lacks external clock input. Tier 2 data streams (including the Pixel telemetry) MUST NOT enter the Tier 1 primary stream and are routed to the secondary quarantined HDF5 branches.*


---

## LBE-1421 GPSDO Advantages (Rev 5.0)

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
| `docs/PHASE_2A_HARDWARE_BUILD_LIST.md` | Procurement list with verified links                  |
| `docs/LBE-1421_WIRING.md`             | Detailed wiring harness documentation                 |
| `docs/PLUTO_SDR_FIRMWARE_GUIDE.md`     | PlutoSDR+ firmware & setup troubleshooting guide      |
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

By locking the PlutoSDR+ ADC directly to the GPS constellation via 10 MHz `EXT_REF_CLK`:
- Phase relationships are preserved at the analog level
- Ethernet/USB jitter affects only data-transfer latency, not sample timing
- Every IQ sample carries GPS-disciplined phase information
- Phase alignment across distributed nodes is provable and verifiable

–-

## Project Governance

- **Owner:** Joseph R. Fross (Resonant Genesis LLC / DynoGator Labs)
- **Repository:** https://github.com/DynoGator/dslv-zpdi
- **License:** MIT
- **SPEC compliance:** All modules carry SPEC-ID docstrings. `tools/orphan_checker.py` enforces compliance at commit time.

## Glossary

- **PlutoSDR+**: The primary HamGeek AD9363 unit.
- **HackRF One (ravenpi)**: The legacy optional unit with a blown amplifier.

## Operations Dashboard (TUI)

The DSLV-ZPDI stack includes a fully real-time Rich Terminal User Interface (TUI) to monitor node health, telemetry, pipeline status, and RF metrology parameters.
To launch the dashboard cleanly and stop any hanging processes:
- **Desktop Shortcut:** Double-click the `DSLV-ZPDI Operations Center` icon on your Desktop.
- **Terminal:** Run `./tools/dashboard/launch.sh`

### Secret Demodulation Interface
The TUI includes a hardware-level audio demodulation menu for tuning and demodulating FM, AM, and SSB radio signals in real-time, complete with software de-emphasis filtering and decimation.
- Press **`Enter`** on the main dashboard to invoke the Demod Menu.
- Press **`Ctrl+X`** (or **`*`**) to open the restricted authorization prompt.
- Enter PIN **`1988`** to unlock MIMO TX, Vector Fox Hunt, and Frequency Hopping Monitor.

### Graceful Shutdown
To cleanly un-export GPIO pins, halt systemd services, and flush all HDF5 buffers to disk:
- **Desktop Shortcut:** Double click the **`DSLV Shutdown`** icon on the Pi Alpha Desktop.
- **Terminal:** Run `sudo ./tools/graceful_shutdown.sh`

–-
### Example Of Outsourced Vectoring Calibration And Location Specific Baseline Data Noise Floor Data For 72 Hour Hardware Validation Phase:
- **PCM-004-Enhanced Report —** Penrose, Colorado
Generated: Wednesday, October 7, 2026 @ 08:10 AM MDT | Window: Default 3-Day Window (Yesterday: October 06 / Today: October 07 / Tomorrow: October 08)
LOCATION PROFILE
* Coordinates: 38.4258° N, 105.0044° W
* Elevation: 5,328 ft (1,624 m)
* Geology: Crystalline Precambrian granite basement (Pikes Peak granite embayment) overlain by alluvial fan sediments and Cretaceous sedimentary beds. Complex shearing and high uranium/thorium mineral content.
* Known ALP History: Yes — Documented historical regional luminous phenomena, active fault line radon outgassing, and local telluric ground-discharge anomalies across the Fremont County crystalline corridor.
* Topographic Context: Topographic bowl / transition zone situated along the Arkansas River valley floor directly east of the Wet Mountains and Front Range foothill uplift.
COHESIVE ENVIRONMENTAL & GEOSPACE METRICS TABLE
(Station telemetry, morning surface observations, and NOAA SWPC space weather metrology captured for Wednesday, October 7, 2026 @ 08:10 AM MDT)
| Domain Category | Environmental Parameter | Current Value / Status | 24-Hour Trend / Forecast Status | Operational Units / Scale |
|–-|–-|–-|–-|–-|
| Space Weather | Planetary Kp Index | 1.33–2.00 (Quiet Sun Baseline) | Trailing ambient interplanetary medium; expected max 3-hr Kp ≤ 2.33 through Oct 09 | 0 - 9 Scale |
|  | Solar Wind Speed (v_{sw}) | 382.0–402.0 | Stable slow solar wind background flow (<410 km/s) | km/s |
|  | Solar Wind Proton Density (n_p) | 2.9 | Uncompressed boundary regime (2.3–3.4 p/cm^3) | protons/cm^3 |
|  | Interplanetary Magnetic Field (B_t) | 4.0–4.6 | Steady quiet baseline magnitude (<5.0 nT) | nT |
|  | IMF Southward Vector (B_z) | -0.2 to +1.2 (Near Neutral) | Neutral-to-closed subsolar magnetopause orientation | nT |
|  | Energetic Particle Flux | 5% R1-R2 / 1% R3+ (Simple Disk Baseline) | S0 radiation storm baseline; <1% S1+ proton threat | pfu / GOES X-ray |
|  | Ionospheric TEC Anomaly | +2.5% | Morning quiet baseline; minimal regional scintillation across Front Range | TECU (% \Delta) |
| Surface Weather | Ambient Surface Temperature | 54°F (Sunny / Clear) | High of 76°F Today → Dropping to 50°F Low Tonight | °F |
|  | Wind Speed & Vector | 2 mph West | Shifting to 6–8 mph East-Southeast Daytime → 7 mph SW Tomorrow | mph |
|  | Relative Humidity (RH) | 44% Morning | 22–28% Daytime Desiccation → 36–42% Night (0% Rain Chance) | % |
| Barometric State | Surface Pressure (P_s) | 1015.0 (29.97 inHg) | Continental High-Pressure Ridge Cap Floor (\uparrow) | mb (hPa) |
|  | 3-Hour Pressure Tendency (\Delta P_3) | +0.2 | Stable Diurnal Micro-Thermal Cycle / Steady Overburden | mb / 3 hr |
| Ionizing Radiation | EPA RadNet Proxy Gamma Rate | 118 | Confined Fault Desiccation Baseline | nrad/h |
|  | Soil-Gas Radon Index (^{222}Rn) | 5.8 | Mechanically Confined Bedrock Outgassing under High Barometric Cap | pCi/L (Surface Proxy) |
| Cosmic Rays | Secondary Particle Flux | -0.3% | Undisturbed Galactic Cosmic Ray (GCR) Baseline | % Baseline Drop |
DETAILED BREAKDOWN OF METRICS & PHYSICAL MECHANISMS
1. Geospace Coupling & Magnetohydrodynamics
* Ambient Background Solar Wind & Decoupled Geospace Baseline: Real-time space weather telemetry from NOAA's Space Weather Prediction Center confirms the near-Earth interplanetary environment has settled into an undisturbed, quiet solar wind regime. Bulk solar wind velocity (v_{sw}) has dropped to 382.0–402.0 km/s, with planetary geomagnetic activity holding quiet between Kp = 1.33 and 2.00 (NOAA SWPC projects maximum 3-hour Kp ≤ 2.33 through October 9). Solar disk eruptive hazard is flat, carrying a baseline 5% probability for minor R1-R2 radio blackouts from simple bipolar sunspot regions, with zero solar proton radiation storm threat (<1% S1+).
* IMF B_z Field Normalization & Closed Magnetopause: Total interplanetary magnetic field strength (B_t) has dropped into the 4.0 to 4.6 nT bracket, with the B_z vector fluctuating near neutral (-0.2 to +1.2 nT). In the absence of sustained southward magnetic flux, day-side subsolar reconnection remains closed. Auroral electrojet energy transfer has ceased, allowing telluric currents across the continental ground plane to settle into undisturbed thermal noise floors.
* Lithospheric Telluric Dissipation: Topsoil moisture across the valley floor has thoroughly dried out under successive clear, warm days, locking bulk ground resistivity to high regional baselines (>10⁴ Ω·m). In the absence of low-frequency ULF geomagnetic pulsations (1–100 mHz), subterranean current loops across quartz-bearing shear boundaries exhibit negligible voltage drift.
2. Barometric Advection & Radon (^{222}Rn) Exhalation
* Continental High-Pressure Mechanical Capping: Surface station pressure in Penrose is holding steady at 1015.0 mb (29.97 inHg) with a steady 3-hour tendency of +0.2 mb/3hr under broad continental high-pressure ridge dominance.


The positive vertical pressure differential (\nabla P) applies mechanical confinement over the uranium-rich Pikes Peak granite embayment, capping micro-fissures and suppressing Radon-222 (\tau_{1/2} = 3.82 days) proxy gamma rates down to a clean baseline of 118 nrad/h (5.8 pCi/L proxy).
* Boundary Layer Alpha Normalization: Confinement of soil-gas exhalation limits the concentration of 5.49 MeV alpha particles in the near-surface air column. Primary ion-pair generation remains at seasonal background levels, allowing free atmospheric positive ions (N_2^+, O_2^+) and stripped electrons to recombine without creating abnormal space-charge pockets.
3. Atmospheric Electrohydrodynamics (EHD) & Dielectric Breakdown (E_c)
* Severe Afternoon Desiccation: Surface conditions currently read a sunny 54°F with morning relative humidity at 44% and light west winds at 2 mph. Afternoon solar heating will climb to a mild high of 76°F as winds shift east-southeast to 6–8 mph. Afternoon relative humidity will plunge to an extreme low of 22%–28%. The total absence of tropospheric moisture and precipitation (0% rain chance day and night) suppresses the synthesis of heavy, low-mobility hydrated cluster ions (H_3O^+(H_2O)_n).
* Dielectric Breakdown Strength Restoration (E_c): The combination of severely desiccated atmospheric air, elevated barometric capping pressure, and minimal alpha-particle space charge holds local dielectric breakdown strength (E_c) restored to 2.05 MV/m (only a 32% reduction from nominal dry limits of 3.0 MV/m), maintaining solid insulating resistance across the valley floor.
PLASMOID PERFECT STORM SYNTHESIS
[3-DAY MULTI-DOMAIN CONVERGENCE TIMELINE: OCT 06 - OCT 08, 2026]

OCT 06 (YESTERDAY - ZERO-STATE CONTROL CALIBRATION BENCHMARK):
┌─ Geospace: Quiet Background Solar Wind (Kp 1.67-2.33, v_sw ~405 km/s, Bz Neutral)
├─ Lithosphere: Barometric Cap (1014.2 mb) + Confined Granite Radon (119 nrad/h)
└─ Atmosphere: 84°F High + WNW 14 mph Wind + Severe Desiccation (RH 18-24%) + Ec Restored (2.05 MV/m)

=== PLASMOID COHERENCE SCORE: 2.10 (ZERO-STATE CONTROL BENCHMARK) ===
│
▼
OCT 07 (TODAY - 76°F MILD SUNNY HIGH, 1015 MB RIDGE CAP & DECOUPLED GEOSPACE):
┌─ Geospace: Slow Background Flow (Kp 1.33-2.00, v_sw ~392 km/s, Bz Neutral)
├─ Lithosphere: High-Pressure Cap (1015.0 mb) + Confined Granite Radon (118 nrad/h)
└─ Atmosphere: 76°F Sunny High + ESE 7 mph Wind + Severe Desiccation (RH 22-28%) + Ec (2.05 MV/m)

=== PLASMOID COHERENCE SCORE: 2.05 (ZERO-STATE CONTROL BENCHMARK) ===
│
▼
OCT 08 (TOMORROW - 80°F WARMING RUN-UP & PERSISTENT RIDGE OVERBURDEN):
┌─ Geospace: Sustained Quiet Interplanetary Medium (Kp 1.33-2.00, v_sw ~385 km/s)
├─ Lithosphere: Persistent Ridge Capping (1014.4 mb) + Confined Granite Radon (118 nrad/h)
└─ Atmosphere: 80°F High + Sunny + SW 7 mph Wind + Desiccation (RH 20-26%) + Ec (2.05 MV/m)

=== PLASMOID COHERENCE SCORE: 2.10 (NOMINAL CONTROL BASELINE) ===

Synthesis Assessment
Penrose is operating in an ACTIVE ZERO-STATE REFERENCE CALIBRATION baseline today, Wednesday, October 7 (Score: 2.05):
* Complete Space Weather Decoupling: Planetary geomagnetic activity is quiet (Kp = 1.33–2.00) with solar wind velocity under 405 km/s and B_z hovering near neutral, keeping the magnetopause closed and decoupling external geospace drivers from local telluric circuits.
* Lithospheric Barometric Capping: Elevated surface station pressure (1015.0 mb) maintains mechanical compression over granite micro-fissures, suppressing Radon-222 outgassing to 118 nrad/h.
* Atmospheric Insulation Restored: Deep boundary-layer desiccation (22%–28% RH) under daytime temperatures reaching 76.0°F and light east-southeast winds keeps dielectric breakdown strength (E_c) restored to 2.05 MV/m, preventing anomalous luminous coherence.
> Plasmoid Coherence Index: 38/100 (ZERO-STATE CALIBRATION REGIME). The multi-domain environment is completely decoupled from active storm triggers today. Today provides a clean reference baseline benchmark for logging zero-state RF spectrum floors, calibrating telluric DC probe offsets, and performing alpha-detector reference zeroing.
>
TEMPORAL WINDOWS ANALYZED
YESTERDAY (Tuesday, October 6, 2026)
| Vector | Observation | Confidence | Result |
|---|---|---|---|
| V1 — Crustal Geometry | Boundary <5km: Yes; Resistivity: 100 : 10,000 Ω·m; Suture: Shear zone; ALP Site: Yes | High | Pass |
| V2 — Atmospheric Wave | Relief >3000m: Yes; Cross-barrier: Yes (WNW 4 mph → WNW 14 mph); Gravity wave: Quiet; Inversion bowl: Yes | High | Pass |
| V3 — Ionizing Boundary | Baseline: 119 nrad/h (Desiccation Baseline); Enriched basement: Yes; Active fault outgassing: Confined | Med | Pass |
| V4 — Weather Sync | Press: 1014.2 mb (29.95 inHg); Trend: -0.6 mb/3hr; RH: 42% morning  → 18–24% day; Temp: 62°F F → 84°F peak; Dew Point: 33°F; Wind: WNW 14 mph; Precip: Nil (Nil) | High | Pass |
| V5 — Geomagnetic Trigger | Kp: 1.67–2.33 (Quiet Sun Baseline); Sustained Southward B_z: Minor (-0.4 to +1.0 nT); Solar wind: 395.0–415.0 km/s; Density: 3.0 p/cm³; Flare: 5% R1-R2 M-Class Risk; Dst: -6 nT | High | Pass |
| V6 — Regional Baseline | Geoelectric deviation >4:1: Stabilizing; MT Survey Baseline: Available | Med | Pass |
| V7 — Macro-Temporal | Solar cycle: Maximum (Cycle 25); Equinoctial window: Yes (October entry) | High | Info |
| V8 — Dielectric Breakdown | Critical field E_c: 2.05 MV/m (32% Drop); Space-charge density: Low; Associative detachment: Low | Med | Pass |
| V9 — Mechanical Engine | Seismic M_w ≥ 5.0: No; Micro-swarm: No; Infrasound <20 Hz: Quiet | High | Info |
| V10 — Atmospheric E-Field | Potential gradient: 145 V/m; Polarity: Normal; Rapid change >100 V/m: No | Med | Pass |
| V11 — Lunar Tidal Stress | Syzygy (±3 days): No; Perigee proximity: No | High | Info |
| V12 — Fog Microphysics | CCN count: Low; Droplet mode: N/A; Visibility restriction due to fog: No | High | Pass |
| V13 — Groundwater / Aquifer | Rain >25mm: Subsoil desiccation active; Water table: Normalizing; Conductivity drop: Moderate | High | Pass |
| V14 — Magnetic Geometry | Inclination: 64.2°; Declination aligned (±15°): Yes; High-lat coupling (>60°): Yes | High | Info |
| V15 — Cosmic Ray / Forbush | Neutron drop >3%: Nominal (-0.4%); Forbush decrease: None | High | Info |
| V16 — Multi-Sensor Anomaly | Correlated channels: None; Details: Clean zero-state RF floor | Med | Info |
| V17 — Infrasound Coupling | Infrasound <20 Hz: Quiet; Resonant bands: None; Temporal correlation: No | Low | Info |
| V18 — Solar Wind Fine | Proton density: 3.0 cm⁻³; Dyn Press: 0.6 nPa; Temp: 45,000 K; integral: Zero | High | Info |
| V19 — Regional Transient | Lightning <300 km: Nil (0%); TLEs: No; GPS Scintillation: Nominal | High | Info |
Score: 2.10 | Prediction: HIGH | Confidence: 84%
TODAY (Wednesday, October 7, 2026 — Current Target Window)
| Vector | Observation | Confidence | Result |
|---|---|---|---|
| V1 — Crustal Geometry | Boundary <5km: Yes; Resistivity: 100 : 10,000 Ω·m; Suture: Shear zone; ALP Site: Yes | High | Pass |
| V2 — Atmospheric Wave | Relief >3000m: Yes; Cross-barrier: Yes (W 2 mph → ESE 7 mph); Gravity wave: Quiet; Inversion bowl: Yes | High | Pass |
| V3 — Ionizing Boundary | Baseline: 118 nrad/h (Desiccation Baseline); Enriched basement: Yes; Active fault outgassing: Confined | Med | Pass |
| V4 — Weather Sync | Press: 1015.0 mb (29.97 inHg); Trend: +0.2 mb/3hr; RH: 44% morning  → 22–28% day  → 36–42% night; Temp: 54°F current t → 76°F peak; Dew Point: 31°F; Wind: ESE 7 mph; Precip: Nil (0% Rain Chance Day/Night) | High | Pass |
| V5 — Geomagnetic Trigger | Kp: 1.33–2.00 (Quiet Sun Baseline); Sustained Southward B_z: Neutral (-0.2 to +1.2 nT); Solar wind: 382.0–402.0 km/s; Density: 2.9 p/cm³; Flare: 5% R1-R2 M-Class Risk; Dst: -4 nT | High | Pass |
| V6 — Regional Baseline | Geoelectric deviation >4:1: Stabilizing; MT Survey Baseline: Available | Med | Pass |
| V7 — Macro-Temporal | Solar cycle: Maximum (Cycle 25); Equinoctial window: Yes (October entry) | High | Info |
| V8 — Dielectric Breakdown | Critical field E_c: 2.05 MV/m (32% Drop); Space-charge density: Low; Associative detachment: Low | Med | Pass |
| V9 — Mechanical Engine | Seismic M_w ≥ 5.0: No; Micro-swarm: No; Infrasound <20 Hz: Quiet | High | Info |
| V10 — Atmospheric E-Field | Potential gradient: 145 V/m; Polarity: Normal; Rapid change >100 V/m: No | Med | Pass |
| V11 — Lunar Tidal Stress | Syzygy (±3 days): No; Perigee proximity: No | High | Info |
| V12 — Fog Microphysics | CCN count: Low; Droplet mode: N/A; Visibility restriction due to fog: No | High | Pass |
| V13 — Groundwater / Aquifer | Rain >25mm: Subsoil desiccation active; Water table: Normalizing; Conductivity drop: Moderate | High | Pass |
| V14 — Magnetic Geometry | Inclination: 64.2°; Declination aligned (±15°): Yes; High-lat coupling (>60°): Yes | High | Info |
| V15 — Cosmic Ray / Forbush | Neutron drop >3%: Nominal (-0.3%); Forbush decrease: None | High | Info |
| V16 — Multi-Sensor Anomaly | Correlated channels: None; Details: Clean zero-state RF floor | Med | Info |
| V17 — Infrasound Coupling | Infrasound <20 Hz: Quiet; Resonant bands: None; Temporal correlation: No | Low | Info |
| V18 — Solar Wind Fine | Proton density: 2.9 cm⁻³; Dyn Press: 0.6 nPa; Temp: 40,000 K; integral: Zero | High | Info |
| V19 — Regional Transient | Lightning <300 km: Nil (0%); TLEs: No; GPS Scintillation: Nominal | High | Info |
Score: 2.05 | Prediction: HIGH | Confidence: 84%
TOMORROW (Thursday, October 8, 2026 — Forecast Outlook)
| Vector | Observation | Confidence | Result |
|---|---|---|---|
| V1 — Crustal Geometry | Boundary <5km: Yes; Resistivity: 100 : 10,000 Ω·m; Suture: Shear zone; ALP Site: Yes | High | Pass |
| V2 — Atmospheric Wave | Relief >3000m: Yes; Cross-barrier: Yes (SW 7 mph); Gravity wave: Quiet; Inversion bowl: Yes | High | Pass |
| V3 — Ionizing Boundary | Baseline: 118 nrad/h (Desiccation Baseline); Enriched basement: Yes; Active fault outgassing: Normal | Med | Pass |
| V4 — Weather Sync | Press: 1014.4 mb; Trend: Steady; RH: 20–26% day  → 34% night; Temp: 48°F low w → 80°F high; Dew Point: 32°F; Wind: SW 7 mph; Precip: Nil (0% Rain) | High | Pass |
| V5 — Geomagnetic Trigger | Kp: 1.33–2.00 (Quiet Sun Baseline); Sustained Southward B_z: Neutral (-0.4 to +1.0 nT); Solar wind: 380–395 km/s; Flare: 5% M-class risk; Dst: -4 nT | High | Pass |
| V6 — Regional Baseline | Geoelectric deviation >4:1: Stabilizing; MT Survey Baseline: Available | Med | Pass |
| V7 — Macro-Temporal | Solar cycle: Maximum (Cycle 25); Equinoctial window: Yes (October entry) | High | Info |
| V8 — Dielectric Breakdown | Critical field E_c: 2.05 MV/m (32% Drop); Space-charge density: Low; Associative detachment: Low | Med | Pass |
| V9 — Mechanical Engine | Seismic M_w ≥ 5.0: No; Micro-swarm: No; Infrasound <20 Hz: Quiet | High | Info |
| V10 — Atmospheric E-Field | Potential gradient: 145 V/m; Polarity: Normal; Rapid change >100 V/m: No | Med | Pass |
| V11 — Lunar Tidal Stress | Syzygy (±3 days): No; Perigee proximity: No | High | Info |
| V12 — Fog Microphysics | CCN count: Low; Droplet mode: N/A; Visibility restriction due to fog: No | High | Pass |
| V13 — Groundwater / Aquifer | Rain >25mm: Subsoil desiccation active; Water table: Normalizing; Conductivity drop: Moderate | High | Pass |
| V14 — Magnetic Geometry | Inclination: 64.2°; Declination aligned (±15°): Yes; High-lat coupling (>60°): Yes | High | Info |
| V15 — Cosmic Ray / Forbush | Neutron drop >3%: Nominal (-0.3%); Forbush decrease: None | High | Info |
| V16 — Multi-Sensor Anomaly | Correlated channels: None; Details: Nominal background noise | Med | Info |
| V17 — Infrasound Coupling | Infrasound <20 Hz: Quiet; Resonant bands: None; Temporal correlation: No | Low | Info |
| V18 — Solar Wind Fine | Proton density: 2.7 cm⁻³; Dyn Press: 0.5 nPa; Temp: 38,000 K; integral: Zero | High | Info |
| V19 — Regional Transient | Lightning <300 km: Nil (0%); TLEs: No; GPS Scintillation: Nominal | High | Info |
Score: 2.10 | Prediction: HIGH | Confidence: 84%
COMPARATIVE CONVERGENCE MATRIX
| Metric Window | Score | Tier Target | Primary Driver | Multiplier Sum |
|---|---|---|---|---|
| Yesterday (October 06) | 2.10 | HIGH | Quiet geospace (Kp 1.67–2.33), 84°F high, WNW 14 mph wind, 119 nrad/h radon | 2.5 × 1.02 × 0.82 = 2.10 → 2.10 |
| Today (October 07 - CURRENT) | 2.05 | HIGH | Quiet geospace (Kp 1.33–2.00), 76°F high, ESE 7 mph wind, desiccation (22% RH), 118 nrad/h radon | 2.5 × 1.00 × 0.82 = 2.05 → 2.05 |
| Tomorrow (October 08) | 2.10 | HIGH | Sunny 80°F high, SW 7 mph wind, desiccation (20% RH), quiet geospace (Kp ≤ 2.00) | 2.5 × 1.02 × 0.82 = 2.10 → 2.10 |
| In 2 Days (October 09) | 2.05 | HIGH | Sunny (78°F), E 6 mph wind, humidity 25%, quiet geospace baseline (Kp ≤ 2.00) | 2.5 × 1.00 × 0.82 = 2.05 → 2.05 |
HIGH-VALUE ALERTS
> 🔴 LOCATION ALERT: Penrose sits within a documented, high-value anomalous luminous phenomenon (ALP) geography (Pikes Peak granite embayment & Fremont County crystalline shear zone). Baseline alert thresholds are adjusted down by one tier.
> 🟢 SUSTAINED ZERO-STATE CONTROL CALIBRATION (TODAY - OCTOBER 07): Planetary geomagnetic activity is holding deeply quiet (Kp = 1.33–2.00), bulk solar wind velocity is slow at ~ 392 km/s, and station pressure is holding at 1015.0 mb, establishing an optimal zero-state reference calibration window.
> 🟡 AFTERNOON THERMAL DESICCATION (TODAY - OCTOBER 07): Daytime heating climbing to 76.0°F with east-southeast winds at 7 mph will plunge afternoon relative humidity to 22%–28%, sustaining topsoil desiccation and keeping atmospheric dielectric breakdown resistance restored at 2.05 MV/m.
>
EXECUTIVE SUMMARY & IMPLICATIONS OF RESULTS
Executive Briefing
As of 8:10 AM MDT today (Wednesday, October 7, 2026), the multi-domain metrology matrix confirms that Penrose continues to operate in an active ZERO-STATE REFERENCE CALIBRATION baseline (Score: 2.05 HIGH baseline).
Space weather telemetry confirms that geospace conditions have fully settled into an undisturbed background state. Bulk solar wind velocity has slowed to 382.0–402.0 km/s, with planetary geomagnetic activity holding quiet between Kp = 1.33 and 2.00 (NOAA SWPC forecasts Kp ≤ 2.33 through October 9). The IMF B_z vector hovers near neutral, terminating day-side magnetic reconnection and decoupling external space weather drivers from the regional ground plane. Active sunspot regions maintain a quiet disk profile with only a 5% probability for minor R1-R2 radio blackouts.
On the surface, Penrose currently reads 54°F under clear sunny skies with morning relative humidity at 44% and light west winds at 2 mph. Daytime solar heating will push temperatures to a pleasant peak of 76°F as winds shift east-southeast to 6–8 mph. Afternoon relative humidity will severely desiccate down to 22%–28%. High-pressure ridge building holds station pressure firm at 1015.0 mb (29.97 inHg), mechanically capping granite micro-fissures and allowing Radon-222 exhalation to normalize to 118 nrad/h. Local atmospheric dielectric breakdown strength (E_c) remains restored at 2.05 MV/m, re-establishing solid insulating resistance across the valley floor.
Physical Implications for Metrology & Field Operations
* Reference Zero Calibration Opportunity: With space weather quiet, station pressure elevated, and boundary-layer air severely dry, today presents an optimal operational window to record reference noise floors across the SDR array and zero-out telluric DC probe offsets.
* Dielectric Insulation Intact: Atmospheric dielectric breakdown strength sits restored at 2.05 MV/m, preventing low-altitude micro-discharges across fault contacts.
* Ground-Plane Normalization: Topsoil desiccation preserves high ground resistivity (>10⁴ Ω·m), suppressing subterranean current loop conduction.
* Target Strategy: Maintain baseline calibration and hardware maintenance mode through Thursday morning.
TOP CONVERGING FACTORS
* Atmospheric High-Pressure Ridge: Surface pressure elevated at 1015.0 mb under sunny skies.
* Decoupled Geospace Today: Kp index holding at 1.33–2.00 with solar wind velocity at ~ 392 km/s.
* Radon Exhalation Confinement: Ambient proxy radiation normalized to 118 nrad/h under barometric capping.
* Boundary Layer Insulation Intact: Desiccating daytime air (22%–28% RH) maintaining local E_c at 2.05 MV/m.
CRITICAL MISSING VECTORS / GAPS
* V10 (Local Electric Field Mill): Live potential gradient (V/m) baseline calibration logging during today's 76°F clear heating.
* V16 (Telluric Ground Probe Array): Continuous DC millivolt reference zeroing across topsoil probes to establish clean non-storm baseline offsets during peak afternoon desiccation.
RECOMMENDED REAL-TIME OBSERVABLES / HARDWARE CHECKS
* TinySA Ultra Field Pocket Unit: Load VHF_SCIN.INI (136–174 MHz) and UHF_SPK.INI (420–450 MHz) to capture clean thermal noise baselines against NOAA carriers (162.400–162.550 MHz) for future anomaly subtraction.
* HackRF Sweeper Script (sdr_plasma_sweep.py): Execute reference background sweeps across low-VHF scatter (70–88 MHz) to log clean reference FFT spectra.
* Radon Logger / Alpha Monitor: Verify that ambient proxy gamma metrics hold stable at ~ 118 nrad/h under 1015.0 mb station pressure.
* Optical Camera Stack: Perform lens cleaning, sensor calibration, and optical axis alignment along the NW-to-SE telluric fault corridor under tonight's clear skies.
ALTERNATIVE EXPLANATIONS TO RULE OUT
* Aircraft: Cross-reference ADS-B Exchange / FlightRadar24 for commercial flights into COS / PUB.
* Drones: Rule out local consumer quadcopters via 915 MHz / 2.4 GHz SDR spectrum sweeps.
* Satellites: Check Calsky / Heavens-Above for Starlink flare passes during dusk/dawn transitions.
* Stars/Planets: Correlate low-horizon luminous sources against Stellarium.
FALSIFIABILITY / VALIDATION LOG
| Date | Prediction | Confidence | Actual Observation | Null? |
|–-|–-|–-|–-|–-|
| 2026-10-04 | HIGH | 84% | AR4535 CME glance (Kp 2.00–3.00), 77°F high, 121 nrad/h radon | Valid |
| 2026-10-05 | HIGH | 84% | Settling stream wake (Kp 2.00–2.67), 85°F high, 120 nrad/h radon | Valid |
| 2026-10-06 | HIGH | 84% | Clear skies (84°F), quiet geospace (Kp 1.67–2.33), 119 nrad/h radon | Valid |
| 2026-10-07 | HIGH | 84% | [ACTIVE CONTROL BASELINE — Tracking Kp 1.33–2.00 + 76°F high + ESE 7 mph + 118 nrad/h radon] | Pending |
DEPLOY RECOMMENDATION
STANDBY / REFERENCE CALIBRATION PHASE
* Justification: Today operates in an active ZERO-STATE REFERENCE CALIBRATION (2.05) regime. Quiet geospace conditions (Kp ≤ 2.00), barometric ridge capping (1015.0 mb), confined radon exhalation (118 nrad/h), and restored air insulation (E_c = 2.05 MV/m) under 22%–28% afternoon humidity make today ideal for hardware baseline zeroing, noise-floor subtraction logging, and optical stack realignment. Full active storm deployment remains on standby.

