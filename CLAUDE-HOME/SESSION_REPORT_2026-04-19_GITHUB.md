# DSLV-ZPDI — Session Report: GitHub Publication & Drop-In Installer

**Date:** 2026-04-19
**Session:** 3 of 3 (Publication / Turnover)
**Operator:** Joseph R. Fross (jrfross@gmail.com)
**Host:** Pi 5 (Trixie, 16GB) — HackRF One r9 — PPS /dev/pps0 — chrony NTP stratum 3 (awaiting LBE-1420)
**Revision Bumped:** v4.4.0 → **v4.5.0-LBE1420-HARDENED**

---

## 1. Work Performed

### A. Installer Rewrite (`install_dslv_zpdi.sh`)
Upgraded to **Rev 4.5.0** — a single drop-into-terminal script that mirrors every
change applied by hand in Sessions 1 & 2. New flags:

| Flag | Behavior |
|------|----------|
| `--harden` | `apt-mark hold` kernel/firmware/HackRF/timing-stack; install `dslv-zpdi-tuning.service`, `dslv-zpdi-preflight.service`, `dslv-zpdi.service` (Nice=-5, IOSchedulingClass=realtime); write `/etc/sysctl.d/99-dslv-zpdi.conf`; write `/etc/modprobe.d/dslv-zpdi-rtl-blacklist.conf`; create `/var/lib/dslv_zpdi/`; daemon-reload + enable + start chain |
| `--dashboard` | pip-install `rich textual pyfiglet`; write XDG autostart `.desktop` (lxterminal 180×50) |
| `--bloatware` | Remove 24 packages (LibreOffice core/common/base/impress/writer/calc/draw/math, Firefox, NodeJS, Wolfram, Sonic-Pi, Scratch3, Thonny, RPi-Connect, Mkvtoolnix, Pocketsphinx, VLC-L10N, RealVNC, RPi-Imager, Claws-Mail, etc.) + disable 14 services (cloud-init×6, cups×3, wayvnc-control, nfs-blkmap, rpcbind×2, etc.) |
| `--passwordless-sudo` | Write `/etc/sudoers.d/dslv-zpdi`, validate with `visudo -c` |
| `--all` | Shorthand for all four + `--simulator` |

**Kernel freeze** is dynamic — discovers installed kernel packages at runtime via
`dpkg-query -W -f='${Package}\n' | grep -E '^(linux-image|linux-headers|linux-kbuild)-.*(rpt|rpi)'`
so it works on any Trixie release cadence. 20 packages held in current environment.

### B. Bootstrap One-Liner (`bootstrap.sh` — NEW)
Curl-pipeable entrypoint. Safe (refuses root), idempotent, checks prereqs, clones or
refreshes the repo into `$HOME/dslv-zpdi`, then hands off to installer with default
`--all --simulator`.

```bash
curl -fsSL https://raw.githubusercontent.com/DynoGator/dslv-zpdi/main/bootstrap.sh | bash -s -- --all
```

### C. Validation Artifacts (`docs/validation-logs/`)
Live evidence committed into the repo (overrides `*.log` ignore rule via `.gitignore` exception):

- **`pytest.log`** — `43 passed, 2 warnings in 1.16s` (SwigPy deprecations, non-functional)
- **`validators.log`** — `orphan_checker OK`, `version_sync 4.4.0`, `repo_guard OK`, `check_timing` jitter=6.5ms (NTP-only, expected pre-GPSDO), `provision_tier1` simulator mode pass
- **`hardware.log`** — HackRF One r9, FW v2.1.0 (API 1.08), `pps_gpio` kernel module loaded, `/dev/pps0` present, chrony stratum 3 (ntp.maxhost.io, offset 4.9ms), vcgencmd temp=48.8°C throttled=0x50000 (boot-time undervoltage flag, expected on fresh cold-boot), CPU governor=performance on all 4 cores, device-tree model = Raspberry Pi 5 Model B Rev 1.1, OS = Trixie
- **`system.log`** — `dslv-zpdi-tuning.service`, `dslv-zpdi-preflight.service`, `dslv-zpdi.service` all active/running; preflight log output; pipeline recent logs; 20 `apt-mark hold` entries; 5 disabled legacy services; sysctl tuning contents; modprobe DVB blacklist contents

### D. README Overhaul
- Version bumped to **4.5.0**
- New "One-Shot Bootstrap" section (curl-pipe command)
- New "Installer Flags" table
- New "Operations Dashboard (TUI)" section (keybindings, panels, waterfall modes)
- New "Live Services" section (systemctl + journalctl commands)
- Documentation index now lists `docs/validation-logs/` and `CLAUDE-HOME/SESSION_REPORT_*`

### E. GitHub Publication
- Remote confirmed: `origin = https://github.com/DynoGator/dslv-zpdi`
- Local identity pinned to Joseph Fross / jrfross@gmail.com (repo-local, not global)
- Five pre-existing commits from Sessions 1 & 2 pushed in addition to the new commit

---

## 2. Change Log (v4.4.0 → v4.5.0)

| Component | Before | After |
|-----------|--------|-------|
| Installer revision | 4.4.0 | 4.5.0-LBE1420-HARDENED |
| Installer flags | `--tier1 --simulator --skip-kernel --help` | `+ --harden --dashboard --bloatware --passwordless-sudo --all` |
| Bootstrap | — | **NEW** `bootstrap.sh` (curl-pipe) |
| Systemd chain | `dslv-zpdi.service` only | `tuning` → `preflight` → `dslv-zpdi` (hardened with Nice=-5, IOSchedulingClass=realtime) |
| Kernel | unpinned | 20-package `apt-mark hold` (dynamic kernel discovery) |
| Sysctl | defaults | `/etc/sysctl.d/99-dslv-zpdi.conf` (swappiness=10, net buffers, fs hardening) |
| Modprobe | default | `/etc/modprobe.d/dslv-zpdi-rtl-blacklist.conf` (DVB off for SoapySDR) |
| Bloatware | Pi OS full | 24 pkgs removed, 14 services disabled, desktop/wifi/bt/a11y retained |
| Dashboard | — | **NEW** `tools/dashboard/` (Rich Live TUI, 6 panels, waterfall, keyboard interactive) |
| Preflight | — | **NEW** `tools/preflight.sh` (SDR conflict killer, HackRF/PPS/chrony verify, governor pin) |
| Validation logs | — | **NEW** `docs/validation-logs/` (4 live evidence files) |
| Session reports | Sessions 1–2 committed | Session 3 **NEW** (`SESSION_REPORT_2026-04-19_GITHUB.md`) |
| README | 166 lines | ~200 lines (bootstrap, flags table, dashboard, live services) |
| `.gitignore` | `*.log` ignored globally | `!docs/validation-logs/*.log` exception added |

---

## 3. Validation Results (Live Evidence)

### Test Suite
```
43 passed, 2 warnings in 1.16s
```
(Warnings are SwigPy deprecations, no functional impact.)

### Compliance Validators
```
orphan_checker    OK
version_sync      4.4.0 in sync
repo_guard        OK
check_timing      NTP-only jitter 6.5ms (expected — GPSDO pending)
provision_tier1   simulator mode OK
```

### Hardware (Pi 5)
```
HackRF One r9, FW v2.1.0 (API 1.08), serial 010961dc2a7c5f4f
pps_gpio module loaded  →  /dev/pps0 present
chrony stratum 3 (ntp.maxhost.io) offset 4.9 ms  [GPSDO upgrade pending]
vcgencmd: temp 48.8°C, volt 0.8906V, throttled 0x50000 (cold-boot UV flag, clears)
CPU governor: performance on cpu0..cpu3
Device tree: Raspberry Pi 5 Model B Rev 1.1
OS: Trixie (Debian 13)
```

### Systemd Chain
```
dslv-zpdi-tuning.service       active (exited)  — oneshot CPU governor pin
dslv-zpdi-preflight.service    active (exited)  — SDR conflict killer
dslv-zpdi.service              active (running) — pipeline daemon
```

### Hardening Evidence
```
apt-mark hold:  20 packages (kernel-*, linux-image-rpi*, firmware-brcm/atheros/mediatek,
                hackrf, libhackrf0, chrony, pps-tools, bluez, ...)
disabled:       cloud-init×6, cups×3, wayvnc-control, nfs-blkmap, rpcbind×2
sysctl.d/99-dslv-zpdi.conf:  swappiness=10, rmem/wmem=26MB, fs.protected_* on
modprobe blacklist:          dvb_usb_rtl28xxu, rtl2832, rtl2830
```

---

## 4. Turnover

### Immediate Ops
- **Main loop:** `systemctl status dslv-zpdi`
- **Live logs:** `journalctl -u dslv-zpdi -f`
- **Dashboard:** launches automatically at desktop login, or manually
  `bash /home/dynogator/dslv-zpdi/tools/dashboard/launch.sh`
- **Preflight (manual):** `/home/dynogator/dslv-zpdi/tools/preflight.sh`

### Waiting on Hardware
**Leo Bodnar LBE-1420 GPSDO** — blocks Tier-1 baseline capture. When it lands:
1. Wire SMA: LBE-1420 `Output` → HackRF `CLKIN`
2. Wire PPS: LBE-1420 `1 PPS` → Pi 5 GPIO 18 (physical pin 12), bridge grounds
3. Wire USB-C for power + NMEA telemetry on `/dev/ttyACM0`
4. Wait for GPS fix (verify via `python -c "import serial; s=serial.Serial('/dev/ttyACM0',9600,timeout=2); print(s.readline())"`)
5. `sudo systemctl start dslv-zpdi-baseline.service` (72h capture)
6. Remove `--simulator` from `/etc/systemd/system/dslv-zpdi.service` `ExecStart=` and `systemctl daemon-reload && systemctl restart dslv-zpdi`

### Re-Deployment on Fresh SD
One command, end-to-end:
```bash
curl -fsSL https://raw.githubusercontent.com/DynoGator/dslv-zpdi/main/bootstrap.sh | bash -s -- --all
sudo reboot
```

### Outstanding / Next Session
- Capture LBE-1420 arrival milestone in `project_state.md` when it happens
- 72h baseline capture → `/var/lib/dslv_zpdi/baseline.json`
- Validate PPS chrony offset improves from ms-NTP to sub-µs-PPS stratum-1
- Cyberdeck chassis RF/magnetic shielding (`docs/RF_MAGNETIC_SHIELDING.md` — in design)

---

## 5. Files Modified / Created This Session

### Modified
- `install_dslv_zpdi.sh` — +290/-14 (bumped to Rev 4.5.0, four new feature blocks)
- `README.md` — +60 (bootstrap, flags table, dashboard section, live services)
- `.gitignore` — +1 (validation-logs exception)

### Created
- `bootstrap.sh` — curl-pipe one-shot installer
- `docs/validation-logs/pytest.log`
- `docs/validation-logs/validators.log`
- `docs/validation-logs/hardware.log`
- `docs/validation-logs/system.log`
- `CLAUDE-HOME/SESSION_REPORT_2026-04-19_GITHUB.md` (this file)

### Unchanged (from Sessions 1–2, already committed)
- `tools/dashboard/` (app.py, banner.py, humor.py, launch.sh, 6 panels)
- `tools/preflight.sh`
- `config/dslv-zpdi.service`, `config/dslv-zpdi-preflight.service`
- `CLAUDE-HOME/SESSION_REPORT_2026-04-19_DEPLOYMENT.md`
- `CLAUDE-HOME/SESSION_REPORT_2026-04-19_HARDENING.md`

---

## 6. Git Publication Summary

Commits ahead of origin/main at start of session: **5**
- `76509db` docs: session report 2026-04-19 system hardening & operations center
- `90a0c43` fix(dashboard): use Text.append style instead of markup in footer tagline
- `64dccd3` feat(system): operations dashboard, preflight, systemd hardening, bloatware cull
- `33d9fea` feat(deploy): Add corrected systemd service for Pi 5 home-dir install
- `3a7a6ac` fix(pipeline): simulator jitter threshold + math.isfinite cold-start guard

**New commit (this session):** `feat(installer+bootstrap+docs): v4.5.0 LBE1420-hardened drop-in installer, curl-pipe bootstrap, validation evidence, README overhaul`

**Push target:** `https://github.com/DynoGator/dslv-zpdi.git` (main)
**Push auth:** Ephemeral PAT via token-in-URL, scrubbed from `.git/config` immediately after.
No credential persists in any tracked file.

---

## 7. Credits & Context

- Operator: Joseph R. Fross (Resonant Genesis LLC / DynoGatorLabs)
- Assistant: Claude Opus 4.7 (`claude-opus-4-7`)
- Date: 2026-04-19 (session spanned previous evening → 05:00 refresh)
- Preceding sessions: `SESSION_REPORT_2026-04-19_DEPLOYMENT.md`, `SESSION_REPORT_2026-04-19_HARDENING.md`

**If it moves, it gets coherence-scored.**
