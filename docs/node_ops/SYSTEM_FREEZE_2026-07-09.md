# System Freeze Report — Tier-1 Anchor

**Date:** 2026-07-09
**Host:** raspberrypi
**Kernel:** 6.18.34+rpt-rpi-2712
**OS:** Debian GNU/Linux 13 (trixie)

## Purpose

This report records the system-level freeze applied to the Tier-1 anchor after
validating that the `dslv-zpdi` stack, the operations dashboard, and the new
`ZPDI_CONDITIONS` local dashboard are all running harmoniously. The freeze is
intended to prevent unintended package upgrades from breaking hardware timing,
SDR, or Python runtime behavior.

## Persistence Verified

| Item | State | Notes |
| --- | --- | --- |
| `dslv-zpdi.service` | enabled / active | Production pipeline |
| `dslv-zpdi-ups.service` | enabled / active | X-1202 UPS monitor |
| `dslv-zpdi-webdash.service` | enabled / active | Web dashboard on :8080 |
| `dslv-zpdi-preflight.service` | enabled | Boot preflight |
| `dslv-zpdi-tuning.service` | enabled | Boot tuning |
| `gpsd.service` | enabled / active | LBE-1421 NMEA feed |
| `chrony.service` | enabled / active | PPS-disciplined NTP |
| `~/.config/autostart/dslv-zpdi-dashboard.desktop` | present | Operations dashboard autostart |
| `~/Desktop/ZPDI_CONDITIONS.desktop` | present | New conditions dashboard icon |
| `unattended-upgrades.service` | inactive | No automatic upgrades running |

## Apt Holds Applied

The following packages are on `apt-mark hold`:

### Kernel / bootloader
- `linux-image-6.18.34+rpt-rpi-2712`
- `linux-image-6.18.34+rpt-rpi-v8`
- `linux-image-rpi-2712`
- `linux-image-rpi-v8`
- `linux-headers-6.18.34+rpt-common-rpi`
- `linux-headers-6.18.34+rpt-rpi-2712`
- `linux-headers-6.18.34+rpt-rpi-v8`
- `linux-headers-rpi-2712`
- `linux-headers-rpi-v8`
- `linux-kbuild-6.18.34+rpt`

### SDR / RF infrastructure
- `libiio0`, `libiio-dev`, `libiio-utils`, `python3-libiio`
- `libsoapysdr0.8`, `libsoapysdr-dev`, `python3-soapysdr`, `soapysdr-tools`
- `libhackrf0`
- `libad9361-dev`

### Timing / GPS
- `gpsd`, `gpsd-clients`, `gpsd-tools`
- `chrony`
- `pps-tools`

### Wireless firmware
- `bluez`, `bluez-firmware`
- `firmware-atheros`, `firmware-brcm80211`, `firmware-mediatek`

### Python runtime
- `python3`, `python3-minimal`, `python3-venv`
- `python3-pip`, `python3-pip-whl`
- `python3-setuptools`, `python3-setuptools-whl`
- `python3-wheel`

## Stack Health Snapshot

Captured from `http://localhost:8080/api/status`:

- Pipeline: active, baseline `LOCKED`
- Timing: `chrony_stratum: 1`, `timing_healthy: true`
- SDR: mode `REAL`, `clock_src: external`, `reachable: true`
- UPS: battery ~97%, voltage 4.16 V

## Restoring Updates Later

To unhold a specific package:

```bash
sudo apt-mark unhold <package-name>
```

To unhold everything:

```bash
sudo apt-mark unhold $(apt-mark showhold)
```

Unfreezing should be done deliberately and followed by a full validation pass
(documented in `AGENTS.md`).

## Reboot / Shutdown Note

All validated state is stored in:
- Systemd unit files (repo + `/etc/systemd/system`)
- Autostart desktop entry (`~/.config/autostart/`)
- Desktop icon (`~/Desktop/`)
- Apt holds (`/var/lib/dpkg/status`)
- Git repository branch `feature/zpdi-conditions` pushed to origin

A clean shutdown or reboot should restore this exact operational state.
