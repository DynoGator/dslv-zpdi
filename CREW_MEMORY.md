# DynoGatorLabs Crew - Unified Memory State

**LAST UPDATED:** 2026-06-16T01:55:00-06:00
**SYSTEM STATUS:** PRE-REBOOT PREPARATION

## 1. Current Codebase State
- **Branch:** `main` (Fully unified and consolidated)
- **Tests:** 185/185 Passing (100% Green)
- **Merged Features:**
  - `PlutoSDR+ Tier1` hardware abstraction layer
  - `Mobile-Node` architecture (Pixel 9 Pro XL Graphene)
  - `Radon-Eye Pro` telemetry fusion

## 2. Hardware Configuration
- **Tier 1 Primary Node:**
  - Hardware: HamGeek Pluto+ (Zynq-7020, 1GB RAM)
  - Network: Gigabit Ethernet at `192.168.3.80`
  - SDR Connection: IIO network context (`ip:192.168.3.80`)
  - Firmware: Custom Tezuka-Libre hybrid (required for Zynq-7020 RAM mapping)
- **GPSDO Metrology Clock:**
  - Hardware: Leo Bodnar LBE-1421
  - Out 1 (1 PPS) → Pi 5 GPIO 18 (UTC anchoring)
  - Out 2 (10 MHz) → PlutoSDR+ CLKIN (Hardware phase lock)

## 3. Next Immediate Steps (Post-Reboot)
1. **User Action:** Physically install the LBE-1421 onto the PlutoSDR+.
2. **System Action:** Boot sequence triggers Supervisor daemon.
3. **Crew Action:** Run the live hardware verification tests to confirm the PlutoSDR+ is successfully slaved to the GPSDO 10MHz external clock.

## 4. Operational Directives
- **NO DESTRUCTIVE MERGES:** The `main` branch is stable. All new work must branch from `main` and pass the 185-item test suite (`DEV_SIMULATOR=1 .venv/bin/python -m pytest tests/ -v`) before merging.
- **HARDWARE PRIORITY:** If the SDR cannot be reached, the system must gracefully degrade to SIMULATOR mode, not crash.
