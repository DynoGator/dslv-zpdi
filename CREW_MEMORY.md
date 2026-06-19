# DynoGatorLabs Crew - Unified Memory State

**LAST UPDATED:** 2026-06-19T00:00:00-06:00
**SYSTEM STATUS:** OPERATIONAL — MOBILE TIER-2 SYNCED TO v5.0.0

## 1. Current Codebase State
- **Branch:** `main` @ `258d051` (Rev 5.0.0) — synced with `origin/main`
- **Tests:** 185/185 Passing (100% Green) — verified on Pixel 9 Pro XL
- **Merged Features:**
  - `PlutoSDR+ Tier1` hardware abstraction layer (IIO / libiio)
  - `Mobile-Node` architecture (Pixel 9 Pro XL GrapheneOS / PRoot)
  - `Radon-Eye Pro` telemetry fusion
  - CLI: `preflight`, `probe`, `verify` commands
  - Key provider chain (dev / file / env / production)
  - Tier-1 ingestion server with AES-256-GCM + HMAC + SHA256 integrity
  - Frequency translation / calibration subpackage
  - Timing subpackage (PPS, NMEA, Chrony, LBE-1421, attestations)
  - Complete CI matrix (GitHub Actions + Docker + security scan)

## 2. Hardware Configuration
- **Tier 1 Primary Node:**
  - Hardware: HamGeek Pluto+ (Zynq-7020, 1GB RAM)
  - Network: Gigabit Ethernet at `192.168.3.80`
  - SDR Connection: IIO network context (`ip:192.168.3.80`)
  - Firmware: Custom Tezuka-Libre hybrid (required for Zynq-7020 RAM mapping)
  - See: `docs/PLUTO_SDR_FIRMWARE_GUIDE.md`, `docs/PlutoSDR/`
- **GPSDO Metrology Clock:**
  - Hardware: Leo Bodnar LBE-1421
  - Out 1 (1 PPS) → Pi 5 GPIO 18 (UTC anchoring)
  - Out 2 (10 MHz) → PlutoSDR+ CLKIN (Hardware phase lock)
  - See: `docs/hardware/LBE1421_PLUTO_WIRING.md`
- **Mobile Tier-2 Node:**
  - Hardware: Pixel 9 Pro XL / GrapheneOS / PRoot Debian
  - Entry-point: `zpdi_mobile_node.py`
  - Supervisor: `supervisor.sh`
  - Boot: `termux-boot/99-start-zpdi.sh` → `~/.termux/boot/` in Termux

## 3. Next Immediate Steps
1. **Hardware (Joe):** Complete PlutoSDR+ / LBE-1421 physical installation per
   `docs/hardware/LBE1421_PLUTO_WIRING.md`.
2. **Qualification:** Run `python3 -m dslv_zpdi.cli.preflight` once hardware is
   attached to confirm Tier-1 HAL initializes.
3. **Mobile boot:** Copy `termux-boot/99-start-zpdi.sh` to `~/.termux/boot/`
   in Termux (outside proot) to enable auto-start on device boot.
4. **WSS endpoint:** Update `ZPDI_WSS_URI` in `.env` when Tier-1 server is on
   the LAN.

## 4. Operational Directives
- **NO DESTRUCTIVE MERGES:** The `main` branch is stable. All new work must branch from `main` and pass the 185-item test suite (`DEV_SIMULATOR=1 .venv/bin/python -m pytest tests/ -v`) before merging.
- **HARDWARE PRIORITY:** If the SDR cannot be reached, the system must gracefully degrade to SIMULATOR mode, not crash.
- **TEST COMMAND (mobile/PRoot):** `cd /root/dslv-zpdi && .venv/bin/pytest tests/ -v`
