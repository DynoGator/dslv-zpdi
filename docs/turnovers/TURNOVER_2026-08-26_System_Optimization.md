# DSLV-ZPDI Pi Alpha Node — Session Turnover Report
## 2026-08-26 | Session: System Optimization & Hardware Calibration

---

> [!IMPORTANT]
> Pi Alpha is now a **fully dedicated, performance-optimized Tier 1 DSLV-ZPDI node**.
> All system resources are prioritized for pipeline stability and SDR data integrity.

---

## Work Performed

### 1. PPS Overlay Fix (GPIO Pin 24)
- **Problem**: Pi Alpha was using the legacy `pps-gpio` overlay (designed for Pi 4 and earlier) instead of the `pps-rp1` overlay required by the Pi 5's RP1 I/O controller.
- **Fix**: Changed `/boot/firmware/config.txt` from `dtoverlay=pps-gpio,gpiopin=24` → `dtoverlay=pps-rp1,pin=24`
- **Result**: PPS0 (`pps@18.-1`) is now properly receiving the LBE-1421 GPSDO 1PPS signal with sub-microsecond jitter. Chrony reports **Stratum 1, PPS-disciplined, system offset <200ns**.

### 2. GPIO Permission Fix (X-1202 UPS Monitor)
- **Problem**: The `dslv-zpdi.service` runs as user `alphapi`, but sysfs GPIO nodes under `/sys/class/gpio/gpio575/` and `/sys/class/gpio/gpio585/` (RP1 pinctrl offsets for BCM GPIO 6 and 16) were being created with `root:root` ownership, causing `[Errno 13] Permission denied` every 20 seconds.
- **Fix**: Created udev rule `/etc/udev/rules.d/99-dslv-gpio.rules` that chowns exported GPIO nodes to `root:gpio` with group write permissions.
- **Result**: GPIO errors completely eliminated. UPS battery monitoring now functional.

### 3. PPS Device Permissions
- **Problem**: `/dev/pps0` was `crw-------` (root only), preventing the non-root PPS listener from reading it.
- **Fix**: Created udev rule `/etc/udev/rules.d/99-dslv-pps.rules` granting `dialout` group read access.
- **Result**: PPS listener can now access `/dev/pps0` without root.

### 4. CPU & Scheduling Optimization
| Setting | Value | Purpose |
|---------|-------|---------|
| CPU Governor | `performance` | Lock all 4 cores at max frequency |
| CPU Affinity | Cores 1-3 for DSLV | Core 0 reserved for OS/GUI |
| Nice Level | `-10` | Pipeline processes get priority over everything |
| I/O Priority | `best-effort:2` | Faster disk I/O for HDF5 writes |
| Memory Lock | `unlimited` | SDR ring buffers stay in RAM |
| RT Priority | `99` | Available for future real-time scheduling |

### 5. Kernel Tuning
| Sysctl | Value | Purpose |
|--------|-------|---------|
| `vm.swappiness` | `10` | Minimize swap, keep pipeline buffers in RAM |
| `vm.dirty_ratio` | `20` | More aggressive write-back for HDF5 |
| `vm.dirty_background_ratio` | `5` | Background flushes start earlier |
| `vm.vfs_cache_pressure` | `50` | Keep directory caches longer |
| `net.core.rmem_max` | `16MB` | Larger UDP buffers for SDR data path |
| `net.core.wmem_max` | `16MB` | Larger send buffers |

### 6. GPU Memory
- Set `gpu_mem=128` — enough for full LXDE desktop, compositing, and touchscreen UI but not wasting RAM on unused GPU compute.

### 7. Disabled Non-Essential Services
- `bluetooth.service` → disabled (no BT peripherals)
- `ModemManager.service` → disabled (no cellular)
- `cups.service` / `cups-browsed.service` → disabled (no printing)
- `triggerhappy.service` → masked (no hotkey daemon needed)
- **Kept active**: SSH, WiFi, LXDE desktop, all input devices, Pi Connect

### 8. Dashboard Crash Fix (Previous Session Carryover)
- Fixed `UnboundLocalError` when pressing `r` (nested `import os` shadowing global)
- Fixed `NameError: name 'sys' is not defined` (regex accidentally stripped global `import sys`)
- Both fixes deployed and verified

### 9. Launch Supervisor Replacement
- Replaced legacy `launch_project.sh` with `dslv_launch_supervisor.sh`
- Added duplicate dashboard prevention via `pgrep` guard
- Removed non-existent `dslv-zpdi-tier1.service` ghost from startup chain

---

## Current System State

```
Git Commit:  f01d096 (main, origin/main)
Version:     5.4.0
Services:    4/4 active (tuning, preflight, pipeline, webdash)
Pipeline:    Nice=-10, CPU cores 1-3, ACTIVE
PPS:         Stratum 1, PPS-disciplined, <200ns offset
SDR:         LibreSDR Rev.5 (AD9361) at ip:libre.local
GPSDO:       LBE-1421 locked, NMEA via gpsd on /dev/ttyACM0
GPIO:        No errors (udev rule active)
Dashboard:   Functional, no crashes
Tests:       230 passed, 7 skipped, 0 failures
```

---

## Files Modified This Session

| File | Change |
|------|--------|
| `config/system/99-dslv-gpio.rules` | **NEW** — GPIO udev rule |
| `config/system/99-dslv-pps.rules` | **NEW** — PPS device permissions |
| `config/system/99-dslv-zpdi-sysctl.conf` | **NEW** — Kernel tuning |
| `config/system/dslv-priority.conf` | **NEW** — Systemd priority drop-in |
| `config/system/99-dslv-limits.conf` | **NEW** — PAM resource limits |
| `install_dslv_zpdi.sh` | Updated to deploy all system configs |
| `tools/dslv_launch_supervisor.sh` | **NEW** — Replaced launch_project.sh |
| `tools/dashboard/app.py` | Fixed import crashes |
| `pyproject.toml` / `__init__.py` / `README.md` / `CHANGELOG.md` | Version bump to 5.4.0 |

---

## Collaborator Notes

- The Pi Alpha is now a **dedicated DSLV node**. All optimizations survive reboots.
- The `config/system/` directory contains every system-level config needed to reproduce this setup on a fresh Pi 5. The installer deploys them automatically.
- If you need to undo any optimization, the configs are clearly separated and can be removed individually.
- The `pps-rp1` overlay is Pi 5 specific. Pi 4 deployments should use `pps-gpio`.
