# DSLV-ZPDI System Context & Agent Settings

This file serves as the permanent active state vector for Antigravity (AGY) sessions on this node. It provides immediate context upon reboot or session restart.

## 🎯 Current Objective
**Develop and Verify Tier 3 x86 Hardware Profile (HackRF + Simulated GPSDO)**
- Successfully created a parallel fork (`feature/tier3-x86-hackrf-sim`) to lower the entry cost for users with HackRFs and x86 hardware.
- Designed `tools/lbe1421_simulator.py` to mock the LBE-1421 GPSDO timing streams (NMEA + PPS) via PTY and sysfs emulation.
- Verified dashboard operations and pipeline ingestion on Debian 13 (NUC Box G2, Intel N100) using a physical HackRF One with software-simulated GPS timing.
- Next step: Await user confirmation on the new branch, then commit and push to `DynoGator/dslv-zpdi`.

## 🛠️ Project State: DSLV-ZPDI Rev 5.2.0 (x86 HackRF Branch)
- **Hardware:** Intel NUC Box G2 (Debian 13 x86_64) + HackRF One + Simulated LBE-1421 GPSDO.
- **Timing:** `tools/lbe1421_simulator.py` active (provides `/tmp/sim_nmea` and `/tmp/sim_pps0`).
- **SDR Config:** Profile `tier3_x86_hackrf_sim.yaml` active. Default `center_hz` is 100 MHz.
- **Demodulation:** Intelligent automatic presets (AM, NFM, WFM, LSB, USB, CW, APRS, etc.) are integrated in `src/dslv_zpdi/layer1_ingestion/demodulation.py`.
- **MIMO Vectoring:** Integrated with Full Duplex enabled by default for MIMO-ready SDRs.
- **Local Presets (Penrose, CO):** 
  - FM: 104.5 MHz (Star Country)
  - AM: 1400 kHz (KRLN)
  - Fire/EMS: 154.310 MHz
  - Profiles correctly sync `center_hz` and `span_hz` to the waterfall dashboard.

## 🤖 Agent Settings & Behavioral Rules
As an agent working on this repository, you must adhere to the following rules to work most effectively:

1. **State Tracking:** Always update this `GEMINI.md` file whenever the current objective changes, a turnover occurs, or major architectural decisions are made. This ensures seamless resumption across reboots.
2. **Master Architecture:** The canonical source of truth for deep architectural rules is `docs/V3_DSLV-ZPDI_LIVING_MASTER.md`. Consult it if you need deep context on Tier 1/Tier 2 roles or hardware specifications.
3. **Turnovers:** When ending a session that requires hardware resets, create a turnover report in `docs/turnovers/` summarizing changes.
4. **Code Standards:** 
   - Ensure high performance and low-latency in all user interfaces (avoid blocking `time.sleep` in TUI loops).
   - Document any new hardware abstractions in `docs/hardware_notes/`.

*Note to User: When starting a new session, you don't need to manually point me here! Because this file is named `GEMINI.md`, Antigravity will automatically read it and know exactly where we left off.*
