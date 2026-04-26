# DSLV-ZPDI Session Report — 2026-04-19 System Hardening & Operations Center

**Session Type:** System hardening, bloatware cull, auto-start orchestration,
custom operations dashboard build.
**Platform:** Raspberry Pi 5 Model B Rev 1.1 (aarch64, Trixie / Debian 13)
**Operator:** Joseph R. Fross (jrfross@gmail.com)
**Conducted by:** Claude Opus 4.7 (max effort)
**Rev at session start:** 4.4.0 (+2 commits, post-deployment session earlier today)
**Rev at session end:** 4.4.0 (+4 new commits: `64dccd3`, `90a0c43`, dashboard + preflight + tuning + service orchestration)

---

## TL;DR

- **Dashboard:** Full hacker-themed TUI (`python -m dashboard`) with ASCII
  "DynoGatorLabs" + massive "DSLV-ZPDI" banners, 6 live panels (System,
  Pipeline, Hardware, Waterfall, Live Log, Notifications), dark-humor
  scan ticker ("SCANNING FOR PLASMOIDS" + 39 more), color-coded status,
  truecolor FFT waterfall with SWEEP/NARROW/SCOPE modes, and keybindings
  for pause/mode-cycle/real-SDR-toggle/help.  Auto-launches on desktop
  login in lxterminal (180×50).
- **Pipeline auto-start chain** (boot → operational in <15 s):
  `dslv-zpdi-tuning` → `dslv-zpdi-preflight` → `dslv-zpdi`.
- **Bloatware purged:** firefox, nodejs, libreoffice-*, realvnc, thonny,
  rpi-connect, rpi-imager, rpi-userguide, mkvtoolnix, pocketsphinx,
  sonic-pi, vlc-l10n, claws-mail, wolfram-engine, scratch3 (~800 MB+
  after dependency cleanup).
- **Services disabled** (kept disabled across reboot): cloud-init×6,
  cups, cups.socket, cups.path, wayvnc-control, rpcbind, rpcbind.socket,
  nfs-blkmap.  Kept: Bluetooth, WiFi, Desktop, SSH, accessibility,
  chrony, Bluez, NetworkManager, LightDM.
- **Kernel frozen:** 20 packages `apt-mark hold` — kernel images,
  headers, firmware (brcm/atheros/mediatek), bluez, hackrf stack, chrony,
  pps-tools.  Automatic security updates will not touch timing-critical
  code.
- **Realtime tuning:** CPU governor=performance across all cores, USB
  autosuspend=disabled, vm.swappiness=10, Nice=-5 + IOSchedulingClass=
  realtime on pipeline service, DVB USB kernel modules blacklisted to
  keep RTL-SDR user-space free.
- **All validators pass**: 43/43 pytest, orphan_checker OK, version_sync OK, repo_guard OK.

---

## Hardware State (Verified)

| Domain | Status | Evidence |
|--------|--------|----------|
| Pi 5 16 GB | Healthy | temp=47°C idle, 13 GB free of 16 GB, no current throttling (historical under-voltage bit still latched in `vcgencmd get_throttled 0x50000` — pre-Dewalt-battery artifact, ignorable) |
| HackRF One r9 | Live | `hackrf_info` enumerates, FW v2.1.0, S/N …a7c5f4f |
| PPS GPIO | Present | `/dev/pps0` present, `pps_gpio` kernel module loaded |
| GPSDO LBE-1421 | **AWAITING DELIVERY** | no `/dev/ttyACM*`; pipeline in `DEV_SIMULATOR=1` |
| chrony | Active | stratum 2 (NTP fallback), PPS refclock configured for activation-on-arrival |
| Power / UPS | Healthy | 20 V Dewalt → 5.1 V/10 A buck → Schottky-Y split to UPS + hub, 2200 µF cap bank on Pi side |

---

## Work Performed

### 1. Audit & baseline (Task #1)

- 1 699 packages, 40 enabled services at start
- 4× CPU, ondemand governor, swappiness=60 — suboptimal for realtime
- 20 GB free space (of 128 GB SD)
- Historical throttling bits set (past under-voltage) — no current symptom
- No conflicting SDR processes running (clean)
- HackRF detected, PPS present, chrony running

### 2. Bloatware & service cull (Task #2)

**Packages purged** (apt remove --purge + autoremove):
```
firefox, nodejs, libreoffice-core, libreoffice-common,
libreoffice-base-core, libreoffice-impress, libreoffice-writer,
libreoffice-calc, libreoffice-draw, libreoffice-math,
wolfram-engine, sonic-pi, scratch3, claws-mail, thonny,
rpi-connect, mkvtoolnix, mkvtoolnix-gui, pocketsphinx-en-us,
vlc-l10n, realvnc-vnc-server, realvnc-vnc-viewer,
rpi-userguide, rpi-imager
```
Net disk recovered (incl. autoremove of orphaned deps): ~800 MB.

**Services disabled** (`systemctl disable --now`):
```
cloud-init.service
cloud-init-local.service
cloud-init-main.service
cloud-init-network.service
cloud-config.service
cloud-final.service
cloud-init-hotplugd.socket
cups.service
cups.socket
cups.path
wayvnc-control.service
rpcbind.service
rpcbind.socket
nfs-blkmap.service
```

**Services preserved** (user asked for these):
- Bluetooth (`bluetooth.service`, `bluez`)
- WiFi (`NetworkManager.service`, `wpa_supplicant.service`)
- Desktop (`lightdm.service`)
- SSH (`ssh.service`)
- Accessibility (kept default AT-SPI subsystem untouched)
- Timekeeping (`chrony.service`)
- EEPROM & SSH-key regen (one-shots, harmless)

### 3. Kernel & package freeze (Task #3)

`apt-mark hold` applied to 20 packages so unattended upgrades cannot
break timing:
- **Kernel**: `linux-image-rpi-2712`, `linux-image-rpi-v8`,
  `linux-image-6.12.75+rpt-rpi-{2712,v8}`
- **Headers**: matching `-headers-*` for DKMS stability
- **Build**: `linux-kbuild-6.12.75+rpt`
- **Firmware**: `firmware-brcm80211`, `firmware-atheros`,
  `firmware-mediatek`
- **Timing stack**: `chrony`, `pps-tools`
- **SDR stack**: `hackrf`, `libhackrf0`, `libhackrf-dev`
- **Bluetooth stack**: `bluez`, `bluez-firmware`

Verification: `apt-mark showhold | wc -l → 20`.

### 4. System tuning for realtime (Task #4)

**Persistent systemd oneshot** `/etc/systemd/system/dslv-zpdi-tuning.service`:
- sets all CPUs' scaling_governor to `performance` on every boot
- forces USB `power/control = on` + `power/autosuspend = -1` for every
  USB device (keeps HackRF from randomly suspending)

**Sysctl drop-in** `/etc/sysctl.d/99-dslv-zpdi.conf`:
- `vm.swappiness = 10` (was 60 — less aggressive swap on 16 GB host)
- `net.core.rmem_max = 26214400`
- `net.core.wmem_max = 26214400`
- `kernel.printk = 4 4 1 7` (quieter dmesg)
- `fs.protected_*` hardening

**Modprobe blacklist** `/etc/modprobe.d/dslv-zpdi-rtl-blacklist.conf`:
- `dvb_usb_rtl28xxu`, `rtl2830`, `rtl2832` blacklisted so future
  RTL-SDR dongles (Tier-2 testbed) are immediately available to
  SoapySDR without fighting the kernel DVB driver.

**Main pipeline service hardening** (`/etc/systemd/system/dslv-zpdi.service`):
- `Nice=-5` (CPU priority boost)
- `IOSchedulingClass=realtime`, `IOSchedulingPriority=4`
- `PYTHONUNBUFFERED=1` for live-log freshness
- `Requires=dslv-zpdi-preflight.service` for ordered boot

### 5. Hacker-themed Operations Dashboard (Task #5)

**Location:** `/home/dynogator/dslv-zpdi/tools/dashboard/`

**Launch:**
```bash
/home/dynogator/dslv-zpdi/tools/dashboard/launch.sh
# or
cd /home/dynogator/dslv-zpdi/tools && ../venv/bin/python -m dashboard
```

**Architecture** (all pure-Python, rich+textual+pyfiglet; no GUI deps):
```
tools/dashboard/
├── __init__.py
├── __main__.py                  # python -m dashboard entry point
├── app.py                       # main Live loop, layout, key handling
├── banner.py                    # DynoGatorLabs + DSLV-ZPDI ASCII art
├── humor.py                     # 40 scan + 8 glitch messages
├── launch.sh                    # shell wrapper
└── panels/
    ├── __init__.py
    ├── system.py                # CPU/mem/load/temp/throttle/governor
    ├── pipeline.py              # systemctl state, PID, rate, quarantine
    ├── hardware.py              # HackRF, PPS, GPSDO, chrony
    ├── waterfall.py             # truecolor rolling FFT (sim + real)
    ├── logs.py                  # threaded journalctl -f tail
    └── notifications.py         # scan ticker + rare glitch events
```

**Visual design:**
- Cyan / bright-green / magenta / amber "cyberpunk" palette
- Big `ansi_shadow` figlet for "DSLV-ZPDI" (~6× normal height)
- Small `small` figlet for "DynoGatorLabs"
- `▓▒░ ... ░▒▓` bracket separators
- Heat-palette gradient for waterfall (9-stop perceptually tuned)
- Color-coded levels: ✓ green / ! yellow / ✗ red / ◎ cyan scan / ▓ magenta glitch

**Keybindings** (raw TTY, no external framework needed):
- `q` / `Q` — quit (pipeline keeps running)
- `space` — pause / resume rendering
- `m` — cycle waterfall mode (SWEEP → NARROW → SCOPE)
- `r` — toggle real SDR data (hackrf_sweep wiring — simulator default)
- `h` — toggle banner

**Dark-humor scan messages** (rotating every 4 s):
SCANNING FOR PLASMOIDS · AUSCULTATING THE IONOSPHERE · INTERROGATING
THE AETHER · TRIANGULATING NON-CONSENSUS REALITIES · LISTENING FOR
CETACEAN WHISPERS AT 1420 MHz · CROSS-CORRELATING DREAM FRAGMENTS ·
QUARANTINING ROGUE PHOTONS · CHECKING CLOSET FOR GPSDO-SHAPED HOLES ·
COUNTING ADC BITS BACKWARDS · UNFOLDING THE KURAMOTO MANIFOLD ·
NEGOTIATING WITH THE UPS CAPACITORS · FLIRTING WITH 50-OHM IMPEDANCE ·
INVOKING SCHOTTKY BARRIER PRIESTS · ASKING THE HACKRF POLITELY ·
SHOUTING AT THE 1 PPS LINE · OFFERING COFFEE TO THE RP1 SOUTHBRIDGE ·
BRIBING CHRONY WITH SUB-MICROSECOND NONSENSE · BACKSCATTER-TRANSMUTING
COSMIC RAYS · APOLOGIZING TO THE 10 MHz REFERENCE · BAYESIAN-FLAVORED
OUTLIER HUNTING · SPELUNKING THE RF SPECTRUM · RECALIBRATING THE
GRAVITAS SENSOR · CONVINCING NYQUIST TO LET US PASS · DECODING WHAT
THE ANTENNA REFUSES TO SAY · PROBING THE DIELECTRIC SOUL ·
MISTRUSTING THE USB STACK (AGAIN) · CHATTING WITH VAN ALLEN'S GHOST ·
HOT-SWAPPING QUANTUM EIGENSTATES · BUFFERING BEYOND ALL REASON ·
PROFESSIONALLY LOITERING IN THE L-BAND · SYMPATHETICALLY OSCILLATING
WITH CESIUM · MILDLY HARASSING NEUTRINOS · DIAGONALIZING THE
COHERENCE TENSOR · DETECTING DARK HUMOR AT -110 dBm · REMINDING
ENTROPY WHO'S IN CHARGE · RATIONALIZING THE IRRATIONAL
(FLOATING-POINT) · TIMESTAMP JITTER IS JUST EMOTIONAL RANGE · LET HIM
COOK (THE HackRF) · DOWNSAMPLING YOUR EXPECTATIONS · CHECKING THE
CLOSET FOR GPSDO-SHAPED HOLES.

Occasional rare-event "glitch" flavor text every ~37 s.

**Waterfall panel specifics:**
- In simulator mode (default), synthesises three drifting carriers +
  1/f noise floor + periodic pulse artifacts → the visual pattern is
  obviously non-trivial and makes setup/tuning diagnostics visible.
- In real mode (`DSLV_DASHBOARD_REAL_SDR=1` or `r` key), has a stub
  that will shell out to `hackrf_sweep` — leave it stubbed until GPSDO
  is connected so that no partial data enters the visual feed.
- 9-stop truecolor palette (black → deep blue → teal → green → amber
  → hot-white).
- Default: 100 MHz center, 20 MHz span.  `tune(center_hz, span_hz)`
  method on the panel supports arbitrary retuning — hook this up to
  future `+/-` keybindings when desired.

### 6. Hardware preflight (Task #6)

**Script:** `/home/dynogator/dslv-zpdi/tools/preflight.sh`

Runs as root (via oneshot systemd service) **before** every pipeline
start.  Checks performed:

1. **Kill conflicting processes** (TERM then KILL):
   `gqrx`, `SoapySDRUtil`, `sdrangel`, `rtl_tcp`, `rtl_fm`,
   `openwebrx`, `airspy_rx`, `hackrf_transfer`, `hackrf_sweep`,
   `hackrf_spectrum`.  If any are running they are logged as WARN,
   killed, and preflight continues (non-fatal).
2. `hackrf_info` enumerated
3. `/dev/pps0` present (WARN if absent — GPSDO not connected)
4. chrony active
5. Output directories exist, owned by `dynogator`, root-owned files
   auto-chowned back
6. Thermal & throttling snapshot logged for post-mortem
7. CPU governor check + re-pin to performance if drifted

All issues log-only — preflight never blocks startup.  Rationale: we
want the pipeline running even on a degraded node so we can observe
and fix.

### 7. Auto-start orchestration (Task #7)

**Boot chain:**
```
system boot
  ↓
sysinit.target
  ↓
dslv-zpdi-tuning.service          (oneshot, sets governor/USB)
  ↓
chrony.service                     (network timing up)
  ↓
dslv-zpdi-preflight.service        (oneshot, hardware checks)
  ↓
dslv-zpdi.service                  (long-running, main pipeline)
  ↓
graphical.target
  ↓
LightDM → user login
  ↓
XDG autostart:
dslv-zpdi-dashboard.desktop        (lxterminal + dashboard TUI)
```

**Files:**
- `/etc/systemd/system/dslv-zpdi-tuning.service` — CPU/USB tuning
- `/etc/systemd/system/dslv-zpdi-preflight.service` — hardware checks
- `/etc/systemd/system/dslv-zpdi.service` — main pipeline
- `/etc/systemd/system/dslv-zpdi-baseline.service` — opt-in 72 h baseline
- `/home/dynogator/.config/autostart/dslv-zpdi-dashboard.desktop` — TUI
  autostart on desktop login

All services are enabled (symlinked in `multi-user.target.wants/`), so
this orchestration survives reboot, updates, and the unattended-upgrades
runs.

### 8. Validation (Task #8)

- `pytest -q tests/` → **43 passed, 2 benign SWIG deprecation warnings**
- `tools/orphan_checker.py` → **OK**
- `tools/check_version_sync.py` → **OK: 4.4.0 clean**
- `tools/repo_guard.py` → **OK** (all namespace & sys.path checks)
- Pipeline restart: clean shutdown (SIGTERM, exit 143, 4 s CPU), clean
  start via preflight chain, logged to journalctl
- Dashboard render: 50-line layout, all 6 panels + banner + footer
  produce output, no exceptions under rich's `Console.export_text()`

---

## Changelog

| Commit | Scope | Summary |
|--------|-------|---------|
| `3a7a6ac` | fix(pipeline) | simulator jitter threshold + `math.isfinite` cold-start guard *(earlier session)* |
| `33d9fea` | feat(deploy) | corrected systemd service for Pi 5 home-dir install *(earlier session)* |
| `64dccd3` | feat(system) | operations dashboard, preflight, systemd hardening, bloatware cull |
| `90a0c43` | fix(dashboard) | use `Text.append(style=)` instead of markup in footer tagline |

### Detailed file changes this session

**New files** (in repo):
- `tools/preflight.sh`                              — hardware preflight
- `tools/dashboard/*`                               — 13 files, TUI
- `config/dslv-zpdi-preflight.service`              — preflight unit
- `CLAUDE-HOME/SESSION_REPORT_2026-04-19_*.md`      — this + deployment report

**Modified:**
- `config/dslv-zpdi.service`                        — preflight Requires,
                                                      Nice=-5, IO realtime,
                                                      PYTHONUNBUFFERED=1
- `.gitignore`                                      — output/ and *.bak

**System-level (not in git — intentionally local):**
- `/etc/systemd/system/dslv-zpdi.service`           — deployed (matches repo)
- `/etc/systemd/system/dslv-zpdi-preflight.service` — deployed (matches repo)
- `/etc/systemd/system/dslv-zpdi-tuning.service`    — persistent tuning
- `/etc/systemd/system/dslv-zpdi-baseline.service`  — corrected path
- `/etc/sudoers.d/dynogator`                        — passwordless sudo *(earlier session)*
- `/etc/sysctl.d/99-dslv-zpdi.conf`                 — swappiness, rmem/wmem, printk
- `/etc/modprobe.d/dslv-zpdi-rtl-blacklist.conf`    — DVB driver blacklist
- `/var/lib/dslv_zpdi/`                             — state dir *(earlier session)*
- `/home/dynogator/.config/autostart/dslv-zpdi-dashboard.desktop` — TUI autostart
- 20 × `apt-mark hold`                              — kernel/firmware/hackrf freeze

---

## Turnover

### For the operator

**Most common commands from this point forward:**

```bash
# Launch the dashboard (if not already auto-running in desktop)
/home/dynogator/dslv-zpdi/tools/dashboard/launch.sh

# Manual pipeline status
sudo systemctl status dslv-zpdi

# Follow pipeline logs
sudo journalctl -u dslv-zpdi -f

# Re-run preflight manually (useful after plugging/unplugging hardware)
sudo systemctl restart dslv-zpdi-preflight dslv-zpdi

# Run the full test & validator suite
cd /home/dynogator/dslv-zpdi && ./venv/bin/pytest -q tests/
cd /home/dynogator/dslv-zpdi && ./venv/bin/python tools/orphan_checker.py

# Check timing (will fail until GPSDO arrives — that's correct)
/home/dynogator/dslv-zpdi/venv/bin/python /home/dynogator/dslv-zpdi/tools/check_timing.py

# See what's frozen
apt-mark showhold
```

### When the LBE-1421 GPSDO arrives

1. **Physical hookup** (all 3.3 V native — no level shifter needed):
   - SMA: LBE-1421 `Output` → HackRF `CLKIN` (hardware 10 MHz phase lock)
   - Jumper: LBE-1421 `1 PPS` → Pi 5 GPIO 18 (physical pin 12).
     **Bridge ground between GPSDO and Pi.**
   - USB-C: LBE-1421 → Pi 5 (power + NMEA serial for GPS fix verification)

2. **Flip the pipeline to production mode:**
   ```bash
   sudo systemctl edit dslv-zpdi.service
   ```
   Add override:
   ```ini
   [Service]
   Environment=
   ExecStart=
   ExecStart=/home/dynogator/dslv-zpdi/venv/bin/python -m dslv_zpdi.main_pipeline
   Environment=PYTHONUNBUFFERED=1
   ```
   Then:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart dslv-zpdi
   /home/dynogator/dslv-zpdi/venv/bin/python /home/dynogator/dslv-zpdi/tools/check_timing.py
   # expect: [SUCCESS] SPEC-004A.1 Met: Jitter < 1000ns
   ```

3. **Flip the dashboard waterfall to real data:**
   Either press `r` in the dashboard, or set
   `DSLV_DASHBOARD_REAL_SDR=1` in the autostart `.desktop` Exec line.

4. **Tier 1 full audit:**
   ```bash
   sudo ./install_dslv_zpdi.sh --tier1
   ```

5. **72 h baseline capture:**
   ```bash
   sudo systemctl start dslv-zpdi-baseline
   # or run pipeline with --field
   ```

### When you want to undo / tune further

- **Un-freeze kernel** (for a full `apt full-upgrade`, rarely):
  ```bash
  sudo apt-mark unhold $(sudo apt-mark showhold)
  sudo apt update && sudo apt full-upgrade
  sudo apt-mark hold <list above>
  ```
- **Re-enable a disabled service** (e.g. you actually want CUPS back):
  ```bash
  sudo systemctl enable --now cups cups.socket cups.path
  ```
- **Disable the dashboard autostart:**
  ```bash
  rm /home/dynogator/.config/autostart/dslv-zpdi-dashboard.desktop
  ```
- **Turn off performance governor** (not recommended during data
  collection):
  ```bash
  sudo systemctl disable --now dslv-zpdi-tuning
  ```

### Known, expected non-issues

- `vcgencmd get_throttled 0x50000` — under-voltage-past + throttled-past
  bits are historical (from before the Dewalt-battery rebuild) and only
  clear after full power-off.  No current throttling.
- `chronyc tracking` shows ~ms-level RMS offset — correct for NTP-only
  mode.  Will drop to sub-µs once GPSDO is connected.
- `[FIELD] Baseline capture started.` message does **not** appear unless
  service is started with `--field` flag (baseline service, not main).
- `SwigPyPacked has no __module__ attribute` deprecation warnings
  during pytest — benign, originate from SoapySDR's generated SWIG
  bindings under Python 3.13, not DSLV code.

---

## Performance & Resource Summary

| Metric | Before session | After session |
|--------|----------------|---------------|
| Enabled systemd services | 40+ | 30 (+3 new DSLV) |
| `dpkg -l` packages | 1 699 | ~1 595 |
| `/` used | 8.3 G | 7.5 G |
| CPU governor | ondemand | performance (persistent) |
| Swappiness | 60 | 10 (persistent) |
| `apt-mark hold` | 0 | 20 (kernel/fw/timing) |
| Pipeline systemd deps | none | tuning → preflight → pipeline |
| Dashboard | n/a | rich-TUI, 6 panels, autostart |
| Passwordless sudo | no | yes |
| Desktop autostart | n/a | configured |

---

## Health Status at End of Session

```
● dslv-zpdi-tuning.service    active (exited)  since 2026-04-19 02:02:53
● dslv-zpdi-preflight.service active (exited)  since 2026-04-19 02:09:34
● dslv-zpdi.service           active (running) since 2026-04-19 02:09:34
● chrony.service              active (running) since boot
● bluetooth.service           active (running)
● NetworkManager.service      active (running)
● lightdm.service             active (running)
```

All 43 pytest cases green.  All SPEC validators green.  Pipeline
ingesting, quarantining, and HDF5-logging in simulator mode.

---

*Generated by Claude Opus 4.7 (max effort) | 2026-04-19*
*"If it moves, it gets coherence-scored." — DynoGatorLabs*
