# TURNOVER: Tier 1 "Zero-Touch" Hardening (2026-08-25)

## Overview
This session focused heavily on the Tier-1 Raspberry Pi Alpha node stability, particularly addressing startup configuration nightmares and dependency holes when booting a fresh Debian Trixie image. We established a fully seamless, zero-touch install procedure that guarantees out-of-the-box operation and data ingestion from the HamGeek PlutoSDR hardware without manual intervention.

## Work Completed

### 1. Hardware Communication & Security
*   **PlutoSDR udev Integration:** `install_dslv_zpdi.sh` was updated to deploy `52-PlutoSDRplus.rules` (USB `0456:b673`), granting the `plugdev` group raw USB access to the SDR hardware. This resolves startup complaints about missing rules.
*   **Production HMAC Key:** Added an automatic payload signing key generation loop in the installer. By default, it will fetch 32 bytes of entropy from `/dev/urandom` to populate `/etc/dslv-zpdi/hmac.key` allowing the `require_production_hmac_key: true` Spec-004A directive to pass.
*   **Static Network Route for PlutoSDR:** Updated the installer to automatically configure the `end0` interface via NetworkManager (`nmcli`) for static IP `192.168.2.10/24`. The Pi now properly bridges to the Pluto network segment automatically.

### 2. Live Node Runtime Repairs (Pi Alpha)
*   **GPIO Permissions Fixed:** The runtime `[Errno 13] Permission denied` errors when the `dslv-zpdi.service` attempted to export `gpio575` and `gpio585` were permanently fixed. The installer now deploys `99-gpio.rules` which maps sysfs GPIO ownership to the `gpio` group.
*   **Dashboard Reliability:** Stripped a hidden `U+0001` byte injected during a previous patching loop that was crashing the TUI with a Python `SyntaxError`. Corrected a hardcoded hallucinated backend instantiation (`PlutoSweepStream` -> `PlutoSDRplusSweepStream`) in `waterfall.py`, allowing the "Real SDR" dashboard mode to safely fallback or operate without fatal stack traces.

### 3. Tier-2 Mobile Node Link (Pixel 9 Pro XL)
*   **Status API Target surfaced:** The Tier-2 mobile node integration (`mobile_bridge.py`) was looking for an old status IP (`10.29.134.63:8080`). We surfaced the override parameter `DSLV_PIXEL_STATUS_URL` in `.env.example`. This makes the target configurable and visible for integrators without digging into the Python source.

## Version & Repository Status
*   **Version:** Bumped repository to **5.3.3** across `pyproject.toml`, `README.md`, and `__init__.py`. 
*   **Tests:** 230 passing tests (7 skipped).
*   **Sync State:** All changes merged cleanly into the `main` branch. 
*   **Outstanding Branches:** The `feature/tier3-x86-hackrf-sim` branch carrying these fixes was merged cleanly into `main`. The git tree is tightly packed and synced to origin.

## Next Session Startup Guide
1.  **Mobile Node Reconnection:** The Pi Alpha is successfully demodulating `WFM_AUDIO` in real-time. However, the Pixel 9 Pro XL was not accessible at the legacy IP address. Check the mobile node's current network IP and populate `DSLV_PIXEL_STATUS_URL` in the Alpha Node's `.env` configuration file so they can sync up.
2.  **Verify New Install:** If performing a fresh flash of Debian Trixie on Pi Alpha, simply run `bash install_dslv_zpdi.sh`. The system should immediately bring up the SDR and the background ingestion pipeline cleanly without manual udev tweaks.
