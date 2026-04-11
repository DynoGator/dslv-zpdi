# DSLV-ZPDI Phase 2A Tier 1 Build Sheet

**Project source:** DynoGator/dslv-zpdi
**Repo revision used:** Rev 4.2-LBE1420 / hardware list updated 2026-04-11
**Document purpose:** Printable procurement and assembly reference for a fresh, from-scratch build using RF Metrology timing
**Document Date:** 2026-04-11

> **DISCLAIMER:** The prices, links, and availability listed in this document are based on live web checks performed on **2026-04-11**. Prices are subject to change. Taxes, tariffs, and shipping are not included.

## Short answer
For the Phase 2A Tier 1 anchor build, we have pivoted to **RF Metrology** timing. The primary hardware stack is now the **Raspberry Pi 5 (16GB)**, **HackRF One**, and **Leo Bodnar LBE-1420 GPSDO**. This configuration achieves true hardware phase-lock to the GPS constellation, bypassing the USB bus jitter inherent in the previous IT-style networking approach.

---

## 1. Supported compute options (Tier 1 Primary only)

| Part number | Board / module | RAM / storage | Use level for this repo | Qty | List price | Verified purchase link |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| PI5-16GB | Raspberry Pi 5 board | 16GB / microSD boot | Phase 2A Primary Anchor - recommended | 1 | $305.00 | CanaKit |
| CM5116000 | Raspberry Pi Compute Module 5 Wireless | 16GB / Lite (0GB eMMC) | Permissible Anchor (via IO Board) | 1 | $300.00 | PiShop US |
| JETSON-AGX-ORIN | NVIDIA Jetson AGX Orin | 32GB/64GB | Permissible (High Performance) | 1 | $1,999.00 | Arrow |

*Selection rule: for the Phase 2A pivot, the **Raspberry Pi 5 (16GB)** is the reference implementation. It provides sufficient compute for coherence math while maintaining GPIO access for PPS.*

---

## 2. Canonical Tier 1 bill of materials (RF Metrology Stack)

This section reflects the 2026-04-11 Hardware Pivot.

| Category | Required component | Part / variant | Qty | List price | Verified purchase link | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Compute | Raspberry Pi 5 | PI5-16GB | 1 | $305.00 | CanaKit | 16GB RAM is preferred for large HDF5 buffers. |
| SDR (RF Eye) | HackRF One | HackRF One (Great Scott Gadgets) | 1 | $349.00 | Great Scott Gadgets | **MANDATORY:** Must have CLKIN port for GPSDO sync. |
| Clock Authority | GPS-Disciplined Oscillator | Leo Bodnar LBE-1420 GPSDO | 1 | $250.00 | Leo Bodnar Electronics | **MANDATORY:** 10MHz + 1PPS, USB-C, NMEA, 3.3V CMOS |
| SDR Antenna | Wideband Antenna | Great Scott Gadgets ANT500 | 1 | $30.00 | Great Scott Gadgets | 75 MHz - 1 GHz coverage |
| RF Cabling | SMA to SMA (10MHz Lock) | SMA M-to-M 50 Ohm (≤1FT) | 1 | $9.99 | Amazon | GPSDO Output → HackRF CLKIN |
| PPS Wiring | Jumper Wires | Premium F-to-F 2.54mm pitch | 2 | $5.99 | Amazon | 1 PPS + Ground bridge |
| Storage | OS / endurance media | VIOFO 128GB Industrial Grade microSD | 1 | $55.99 | Amazon | Recommended for long-term HDF5 logging. |
| Cooling | Active Cooling | Raspberry Pi 5 Active Cooler | 1 | $5.00 | PiShop US | Mandatory for sustained 20MHz IQ processing. |
| Power | USB-C Power | Raspberry Pi 27W Power Supply | 1 | $12.95 | PiShop US | Required for Pi 5 board + peripherals. |

### Repo-shared peripherals and cabling

| Category | Recommended buy | Part / variant | Qty | List price | Verified purchase link | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| GNSS Antenna | Active GPS Antenna | 3-5V Active Patch Antenna | 1 | $12.00 | Adafruit | Required for LBE-1420 GPS lock. |
| RF cabling | By-the-foot coax | LMR-240 | As needed | $1.37/ft | DX Ham Radio Supply | Usually ships in 1-3 business days. |

---

## 3. Hardware Agnosticism Standard (SPEC-004A.2)

If the primary components above are unavailable, any hardware meeting these criteria is permissible for Tier 1:
1. **External 10 MHz Phase-Locking:** The SDR MUST have a `CLKIN` or equivalent port that hardware-locks the sampling clock.
2. **1 PPS Hardware Interrupt:** The compute board MUST receive a 1 PPS signal via a direct hardware interrupt (GPIO).
3. **Compute Performance:** Must handle Kuramoto Coherence math at the operational sample rate without frame drops.

*Permissible fallbacks: USRP B200, USRP N210, LimeSDR (with clock mod), Intel NUC with M.2 timing card.*

---

## 4. Physical assembly and wiring procedure (RF Metrology Focus)

**Step 1.** Unpack the Raspberry Pi 5, HackRF One, Leo Bodnar LBE-1420 GPSDO, ANT500, and peripherals.
**Step 2.** Install the Raspberry Pi 5 Active Cooler. High-bandwidth SDR operation will thermally throttle a bare board.
**Step 3.** Flash Raspberry Pi OS 64-bit to the industrial microSD using Raspberry Pi Imager.
**Step 4.** **RF Phase Lock (ADC Slave):** Connect SMA Male-to-Male cable (50 Ohm, ≤ 1FT) from the LBE-1420 `Output` port to the HackRF One `CLKIN` port.
**Step 5.** **OS Timestamping (Heartbeat):** Run jumper wire from the LBE-1420 `1 PPS` output to Pi 5 **GPIO Pin 18** (Physical Pin 12). Run a second jumper to bridge the ground paths between the GPSDO and the Pi. *Note: LBE-1420 outputs 3.3V CMOS natively — no level-shifter required for Pi 5 RP1 chip.*
**Step 6.** **Power & Telemetry:** Connect the LBE-1420 via USB-C to the Pi 5. This provides power and establishes the NMEA virtual serial connection for software-observable GPS fix verification.
**Step 7.** Connect the HackRF One to the Raspberry Pi 5 via a high-quality USB 3.0 cable. (Note: USB jitter is now irrelevant to phase-lock).
**Step 8.** Connect the ANT500 antenna to the HackRF One for RF capture. Connect the Active GPS antenna to the LBE-1420 GPSDO and place it with a clear view of the sky.
**Step 9.** Apply power to the Pi 5 (GPSDO powers via USB-C from Pi).

---

## 5. Operating system and initial software bring-up

1. **Update OS:** `sudo apt update && sudo apt full-upgrade -y`
2. **Configure PPS:** Add `dtoverlay=pps-gpio,gpiopin=18,assert_falling_edge=0` to `/boot/firmware/config.txt`.
3. **Install Tools:** `sudo apt install pps-tools chrony hackrf`
4. **Verify PPS:** `lsmod | grep pps` and `ppstest /dev/pps0`.
5. **Verify HackRF:** `hackrf_info` (ensure it's detected).
6. **Clone & Install Repo:**
```bash
git clone https://github.com/DynoGator/dslv-zpdi.git
cd dslv-zpdi
sudo ./install_dslv_zpdi.sh --tier1
```

---

## 6. Verification checklist (Post-Pivot)

- **Check 1.** Run `hackrf_debug --clock_source`. It MUST report the clock source as external (clkin).
- **Check 2.** Run `chronyc sources -v`. The PPS source should have a `*` or `+` indicating active discipline.
- **Check 3.** Run `python tools/check_timing.py` (the updated PPS/GPSDO audit utility).
- **Check 4.** Run the full test suite: `pytest tests/`.

---

## 7. Do-not-do list for the RF Metrology build

- **Do not** use a free-running SDR oscillator for Tier 1 institutional data collection.
- **Do not** use software-only PTP/NTP for primary stream timing.
- **Do not** use a low-quality USB power supply; the HackRF + Pi 5 draw significant current during 20MHz ingestion.
- **Do not** skip the 10MHz SMA connection; without it, the SDR is not phase-locked.

*End of build sheet.*
