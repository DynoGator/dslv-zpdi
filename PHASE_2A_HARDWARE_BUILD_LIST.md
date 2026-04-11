# DSLV-ZPDI Phase 2A Hardware Build List

**Target:** Tier 1 Anchor Node ("Thoth's Eye") & Tier 2 Swarm
**Status:** Canonical for Phase 2A
**Last Updated:** 2026-04-11

---

## 1. TIER 1 ANCHOR NODE (The Truth Engine)

| Component | Specification | Part Number | Quantity | Role |
|-----------|---------------|-------------|----------|------|
| Compute | Raspberry Pi 5 (16GB) | PI5-16GB | 1 | Primary Logic & I/O |
| SDR (The Eye) | HackRF One | HackRF-One | 1 | RF Ingestion (External CLKIN) |
| Clock Authority | Leo Bodnar LBE-1420 GPSDO | LBE-1420 | 1 | 10 MHz & 1 PPS, USB-C, NMEA, 3.3V CMOS |
| SDR Antenna | Great Scott Gadgets ANT500 | ANT500 | 1 | 75 MHz - 1 GHz Coverage |
| RF Interconnect | SMA Male-to-Male Coaxial | 50 Ohm, ≤ 1FT | 1 | GPSDO Output → HackRF CLKIN |
| Interrupt Interconnect | Premium F-to-F Jumper Wires | 2.54mm pitch | 2 | PPS + Ground Bridge |
| Multi-Modal Sensors | Thermal/Acoustic array | Generic | 1 | Secondary Modality Data |
| Storage | Industrial microSD | Endurance-128GB | 1 | HDF5 Persistence |

### Tier 1 Assembly Instructions:
1. **RF Phase Lock (ADC Slave):** Connect SMA cable from LBE-1420 `Output` port directly to HackRF One `CLKIN` port. This phase-locks the SDR's ADC to the GPS constellation.
2. **OS Timestamping (Heartbeat):** Run jumper wire from LBE-1420 `1 PPS` output to Pi 5 GPIO Pin 18 (Physical Pin 12). Bridge ground between GPSDO and Pi. *Note: LBE-1420 outputs 3.3V CMOS natively — no level-shifter required.*
3. **Power & Telemetry:** Connect LBE-1420 via USB-C to Pi 5. Provides power and NMEA virtual serial connection for GPS fix verification.
4. **OS Configuration:** Install Raspberry Pi OS (64-bit). Install `chrony` and `hackrf` tools. Add `dtoverlay=pps-gpio,gpiopin=18,assert_falling_edge=0` to `/boot/firmware/config.txt`.
5. **Verification:** Confirm ADC lock via `hackrf_debug --clock_source` (should show external), verify PPS discipline with `chronyc sources -v`, and verify NMEA stream on `/dev/ttyACM0`.

---

## 2. TIER 2 SWARM NODE (Early Warning)

| Component | Specification | Part Number | Quantity | Role |
|-----------|---------------|-------------|----------|------|
| Compute | Rooted/Jailbroken Android/iOS E-Waste | Various (SD8xx+) | 1 | Heuristic Detection |
| SDR | RTL-SDR v3/v4 | RTL-SDR-V4 | 1 | Heuristic RF Ingestion |
| Power | Eaton HS-108 Supercapacitor Bank | HS-108 | 1 | Environmental Endurance |
| Connectivity | Wi-Fi 6 / Bluetooth 5.2 | Integrated | 1 | Swarm Sync (SPEC-008) |

### Tier 2 Assembly Instructions:
1. **Power Overhaul:** Remove the internal Lithium-Ion battery. Integrate the Eaton HS-108 supercapacitor bank to handle environmental temperature extremes and provide rapid recharge/discharge cycles.
2. **Firmware:** Flash custom hardened kernel to enable raw spectrum access.
3. **SDR Integration:** Connect RTL-SDR v3/v4 via USB. Note: Tier 2 nodes do not require hardware phase-lock but must maintain <10ms sync for heuristic triggers.

---

## 3. SHARED PERIPHERALS & CABLING

- **Primary SDR:** HackRF One (Mandatory for Tier 1).
- **Secondary SDR:** RTL-SDR v3/v4 (Permissible for Tier 2/Testbed).
- **Antennas:** Multi-spectrum dipole/patch array for 400MHz - 2.4GHz.
- **Cabling:** LMR-240 or better for RF paths; shielded Cat6 for any network-backhauled data.
