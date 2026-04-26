# DSLV-ZPDI Phase 2A Tier 1 Build Sheet (Consolidated)

> **Canonical source:** `PHASE_2A_TIER_1_BUILD_SHEET.md` in the repo root  
> **Target:** Tier 1 Anchor Node (\"Thoth's Eye\") & Tier 2 Swarm
> **Status:** ACTIVE / RF Metrology Focus
> **Last Updated:** 2026-04-26 (v4.6.0-LBE1421)

---

## 1. Executive Summary: The RF Metrology Pivot

For the Phase 2A Tier 1 anchor build, we have transitioned to **RF Metrology** timing using the **Leo Bodnar LBE-1421 GPSDO**. This unit provides simultaneous 10 MHz reference and 1 PPS physical interrupts, achieving true hardware phase-lock to the GPS constellation.

**LBE-1421 Key Specs:**
- **Out1:** 1 PPS mode (100ms 3.3V CMOS pulse).
- **Out2:** 10,000,000 Hz reference (50 Ohm, 1.65V into 50 Ohm).
- **Stability:** 1 x 10^-12 @ 1000 s.
- **Holdover:** No frequency/phase jumps on GPS loss.
- **Power:** 250 mA +/-10 % @ 5 V USB-C + 30 mA antenna port.

---

## 2. Tier 1 Anchor Node Bill of Materials

| Category | Required Component | Part / Variant | Qty | Role |
| :--- | :--- | :--- | :--- | :--- |
| Compute | Raspberry Pi 5 | PI5-16GB | 1 | Primary Logic & I/O |
| SDR (RF Eye) | HackRF One | Great Scott Gadgets | 1 | RF Ingestion (External CLKIN) |
| Clock Authority | GPSDO | Leo Bodnar LBE-1421 | 1 | 10 MHz + 1 PPS (Out2/Out1) |
| SDR Antenna | Wideband Antenna | ANT500 | 1 | 75 MHz - 1 GHz Coverage |
| GNSS Antenna | Active GPS Antenna | 3-5V Active Patch | 1 | Required for LBE-1421 Lock |
| RF Cabling | SMA to SMA | M-to-M 50 Ohm (<= 1FT) | 1 | LBE-1421 Out2 -> HackRF CLKIN |
| PPS Wiring | Jumper Wires | Premium F-to-F | 2 | LBE-1421 Out1 -> Pi 5 GPIO 18 |
| Storage | Industrial microSD | VIOFO 128GB | 1 | HDF5 Persistence |
| Cooling | Active Cooling | RPi 5 Active Cooler | 1 | Mandatory for 20MHz IQ |
| Power | USB-C Power | RPi 27W Power Supply | 1 | Required for Pi 5 + peripherals |

---

## 3. Tier 2 Swarm Node (E-Waste / Early Warning)

| Component | Specification | Part Number | Quantity | Role |
|-----------|---------------|-------------|----------|------|
| Compute | Rooted Android/iOS E-Waste | Various (SD8xx+) | 1 | Heuristic Detection |
| SDR | RTL-SDR v3/v4 | RTL-SDR-V4 | 1 | Heuristic RF Ingestion |
| Power | Supercapacitor Bank | Eaton HS-108 | 1 | Environmental Endurance |
| Connectivity | Wi-Fi 6 / BT 5.2 | Integrated | 1 | Swarm Sync (SPEC-008) |

---

## 4. Physical Assembly & Wiring Procedure

**Step 1.** Install the Raspberry Pi 5 Active Cooler.
**Step 2.** **RF Phase Lock (ADC Slave):** Connect SMA cable from LBE-1421 `Out2` port (configured to 10,000,000 Hz) to the HackRF One `CLKIN` port. Use a 50 Ohm terminator if cable length exceeds 1 foot.
**Step 3.** **OS Timestamping (Heartbeat):** Connect jumper from LBE-1421 `Out1` (configured to 1 PPS mode) to Pi 5 **GPIO 18** (Physical Pin 12). Bridge ground between LBE-1421 and Pi 5.
**Step 4.** **Power & Telemetry:** Connect LBE-1421 via USB-C to Pi 5. This provides power (250mA draw) and enables NMEA telemetry on `/dev/ttyACM0`.
**Step 5.** Connect HackRF One to Pi 5 via USB 3.0. Connect antennas to respective ports.

---

## 5. OS Configuration & Verification

1. **PPS Support:** Add `dtoverlay=pps-gpio,gpiopin=18,assert_falling_edge=0` to `/boot/firmware/config.txt`.
2. **Tools:** `sudo apt install pps-tools chrony hackrf`
3. **Verify ADC Lock:** `hackrf_debug --clock_source` must report `external`.
4. **Verify PPS:** `ppstest /dev/pps0` should show stable 1s intervals.
5. **Verify NMEA:** `cat /dev/ttyACM0` should show GPGGA/GPRMC sentences.
6. **Hardening:** Run `sudo ./install_dslv_zpdi.sh --tier1`.

---

## 6. Do-Not-Do List

- **Do NOT** connect Out1/Out2 to Pi 5 if voltage exceeds 3.3V. (LBE-1421 is 3.3V native).
- **Do NOT** use a single-output LBE-1420 for Tier 1 builds.
- **Do NOT** skip ground bridging between GPSDO and Pi; it causes floating ground triggers.
- **Do NOT** use software-only timing for primary HDF5 stream.
