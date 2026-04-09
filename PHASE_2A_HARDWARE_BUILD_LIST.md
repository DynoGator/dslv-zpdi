# DSLV-ZPDI Phase 2A Hardware Build List

**Target:** Tier 1 Anchor Node ("Thoth's Eye") & Tier 2 Swarm
**Status:** Canonical for Phase 2A
**Last Updated:** 2026-04-09

---

## 1. TIER 1 ANCHOR NODE (The Truth Engine)

| Component | Specification | Part Number | Quantity | Role |
|-----------|---------------|-------------|----------|------|
| Compute | Raspberry Pi Compute Module 4 (CM4) / CM5 | CM4108032 (or CM5 equiv) | 1 | Primary Logic & I/O |
| Carrier Board | Waveshare CM4-IO-BASE-B (or equivalent) | CM4-IO-BASE-B | 1 | PCIe & SDP Exposure |
| Precision Timing | Intel i210-T1 PCIe Gigabit Ethernet NIC | I210T1 | 1 | PTP / Nanosecond Timing |
| GPS/GNSS | u-blox ZED-F9P (L1/L5) | ZED-F9P | 1 | PPS Source & Geolocation |
| Storage | Industrial microSD / NVMe | Endurance-128GB | 1 | HDF5 Persistence |

### Tier 1 Assembly Instructions:
1. **PTP Hardening:** Seat the Intel i210-T1 into the CM4 carrier board's PCIe x1 slot.
2. **Timing Surgery:** Physically wire the u-blox ZED-F9P PPS output pin directly to the Software Definable Pin (SDP) header on the Intel i210-T1. This bypasses the native CM4 hardware clock.
3. **OS Configuration:** Install 64-bit OS. Install `linuxptp`, `ethtool`, and `chrony`.
4. **Verification:** Confirm `<30ns` jitter via `chronyc tracking` and verify `ts2phc` is disciplining the i210 PHC from the PPS signal.

---

## 2. TIER 2 SWARM NODE (Early Warning)

| Component | Specification | Part Number | Quantity | Role |
|-----------|---------------|-------------|----------|------|
| Compute | Rooted/Jailbroken Android/iOS E-Waste | Various (SD8xx+) | 1 | Heuristic Detection |
| Power | Eaton HS-108 Supercapacitor Bank | HS-108 | 1 | Environmental Endurance |
| Connectivity | Wi-Fi 6 / Bluetooth 5.2 | Integrated | 1 | Swarm Sync (SPEC-008) |

### Tier 2 Assembly Instructions:
1. **Power Overhaul:** Remove the internal Lithium-Ion battery. Integrate the Eaton HS-108 supercapacitor bank to handle environmental temperature extremes and provide rapid recharge/discharge cycles.
2. **Firmware:** Flash custom hardened kernel to enable raw spectrum access.
3. **Deployment:** Ensure SPEC-008 stylistic consistency analysis is active to prevent swarm poisoning.

---

## 3. SHARED PERIPHERALS & CABLING

- **SDR:** RTL-SDR Blog V4 or Airspy R2 (Modality-dependent).
- **Antennas:** Multi-spectrum dipole/patch array for 400MHz - 2.4GHz.
- **Cabling:** LMR-240 or better for RF paths; shielded Cat6 for PTP network.
