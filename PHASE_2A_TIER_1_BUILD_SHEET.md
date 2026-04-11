# DSLV-ZPDI Phase 2A Tier 1 Build Sheet

**Project source:** DynoGator/dslv-zpdi
**Repo revision used:** Rev 4.1-PIVOT / hardware list updated 2026-04-11
**Document purpose:** Printable procurement and assembly reference for a fresh, from-scratch build using RF Metrology timing
**Document Date:** 2026-04-11

> **DISCLAIMER:** The prices, links, and availability listed in this document are based on live web checks performed on **2026-04-11**. Prices are subject to change. Taxes, tariffs, and shipping are not included.

## Short answer
For the Phase 2A Tier 1 anchor build, we have pivoted to **RF Metrology** timing. The primary hardware stack is now the **Raspberry Pi 5 (16GB)**, **HackRF One**, and **Leo Bodnar Mini GPSDO**. This configuration achieves true hardware phase-lock to the GPS constellation, bypassing the USB bus jitter inherent in the previous IT-style networking approach.

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
| Clock Authority | GPS-Disciplined Oscillator | Leo Bodnar Mini GPSDO | 1 | $185.00 | Leo Bodnar Electronics | **MANDATORY:** Provides 10MHz reference and 1 PPS. |
| Storage | OS / endurance media | VIOFO 128GB Industrial Grade microSD | 1 | $55.99 | Amazon | Recommended for long-term HDF5 logging. |
| Cooling | Active Cooling | Raspberry Pi 5 Active Cooler | 1 | $5.00 | PiShop US | Mandatory for sustained 20MHz IQ processing. |
| Power | USB-C Power | Raspberry Pi 27W Power Supply | 1 | $12.95 | PiShop US | Required for Pi 5 board + peripherals. |

### Repo-shared peripherals and cabling

| Category | Recommended buy | Part / variant | Qty | List price | Verified purchase link | Notes |
| :--- | :--- | :--- | : :--- | :--- | :--- | :--- |
| RF Cabling | SMA to SMA (10MHz) | RG174 SMA Male to Male | 1 | $9.99 | Amazon | Connects GPSDO 10MHz Out to HackRF CLKIN. |
| GNSS Antenna | Active GPS Antenna | 3-5V Active Patch Antenna | 1 | $12.00 | Adafruit | Required for GPSDO lock. |
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

**Step 1.** Unpack the Raspberry Pi 5, HackRF One, Leo Bodnar Mini GPSDO, and peripherals.
**Step 2.** Install the Raspberry Pi 5 Active Cooler. High-bandwidth SDR operation will thermally throttle a bare board.
**Step 3.** Flash Raspberry Pi OS 64-bit to the industrial microSD using Raspberry Pi Imager.
**Step 4.** **The Phase-Lock Connection:** Connect a short SMA-to-SMA cable from the Leo Bodnar Mini GPSDO 10 MHz output to the HackRF One `CLKIN` port.
**Step 5.** **The PPS Connection:** Connect the 1 PPS output from the Leo Bodnar GPSDO to **GPIO 18** (Physical Pin 12) on the Raspberry Pi 5. Ensure a common ground between the GPSDO and the Pi.
**Step 6.** Connect the HackRF One to the Raspberry Pi 5 via a high-quality USB 3.0 cable. (Note: USB jitter is now irrelevant to phase-lock).
**Step 7.** Connect the Active GPS antenna to the Leo Bodnar GPSDO and place it with a clear view of the sky.
**Step 8.** Apply power to the Pi 5 and the GPSDO.

---

## 5. Operating system and initial software bring-up

1. **Update OS:** `sudo apt update && sudo apt full-upgrade -y`
2. **Configure PPS:** Add `dtoverlay=pps-gpio,gpiopin=18` to `/boot/firmware/config.txt`.
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
