# [UPDATE] DSLV-ZPDI Architecture Specification: Phase 2A Hardware Pivot

**Document ID:** `SPEC-UPDATE-PHASE-2A-LBE1420`
**Target Baseline:** Revision 4.2.0
**Status:** ACTIVE - Mandatory Integration Standard
**Date:** 2026-04-11

---

## 1. Rationale for Revision

To guarantee mathematical coherence for the Kuramoto Engine and eliminate non-deterministic USB bus jitter, the DSLV-ZPDI project migrated away from IT-networking timing (Intel NICs). Timing authority is now exclusively handled via **Metrology-Grade RF Synchronization**.

The previously specified Leo Bodnar Mini GPSDO has been officially superseded by the **Leo Bodnar LBE-1420**. The LBE-1420 provides critical advantages for day-to-day field operations:

| Feature | LBE-1420 (Current) | Mini GPSDO (Deprecated) |
|---------|---------------------|------------------------|
| Power Delivery | USB-C (ruggedized) | Mini-USB (fragile, prone to shearing) |
| Telemetry | Observable NMEA via virtual serial port | None (hardware LED only) |
| PPS Output | Strictly compliant 3.3V CMOS square wave | Variable (may require level-shifting) |
| Pi 5 Compatibility | Direct GPIO connection (no level-shifter) | Requires voltage verification |

---

## 2. Updated Tier 1 Hardware Baseline (BOM)

All Tier 1 field deployments must utilize the following core stack:

| Component | Model | Role |
|-----------|-------|------|
| Compute / Buffer | Raspberry Pi 5 (16GB) | High-bandwidth FFT processing, HDF5 storage |
| SDR (The Eye) | HackRF One | RF ingestion with 20 MHz bandwidth, CLKIN for GPSDO |
| Clock Authority | Leo Bodnar LBE-1420 GPSDO | 10 MHz + 1 PPS, USB-C, NMEA telemetry |
| SDR Antenna | Great Scott Gadgets ANT500 | 75 MHz - 1 GHz coverage |
| RF Interconnect | SMA Male to SMA Male Coaxial | 50 Ohm, ≤ 1FT |
| Interrupt Interconnect | Premium Female-to-Female Jumper Wires | 2.54mm pitch |

---

## 3. Physical Routing Protocol

Physical connections are strictly standardized to bypass the OS kernel for critical timing loops.

### 3.1 RF Phase Lock (The ADC Slave)
Connect the SMA cable from the LBE-1420 `Output` port directly to the HackRF One `CLKIN` port. This physically locks the HackRF's sampling rate to the GPS constellation.

### 3.2 OS Timestamping (The Heartbeat)
- Run a jumper wire from the LBE-1420 `1 PPS` output to the Pi 5's **GPIO Pin 18** (Physical Pin 12).
- Run a second jumper to bridge the ground paths between the GPSDO and the Pi.
- **Note:** The LBE-1420 outputs 3.3V logic natively, so no level-shifter is required for the Pi 5 RP1 chip.

### 3.3 Power & Telemetry
Connect the LBE-1420 via USB-C to the Pi 5. This provides power and establishes the NMEA virtual serial connection for software observation.

---

## 4. Software Stack Integration Requirements

### 4.1 System Level (Bookworm OS)

**Interrupt Handling:** `/boot/firmware/config.txt` must invoke the `pps-gpio` overlay:
```
dtoverlay=pps-gpio,gpiopin=18,assert_falling_edge=0
```

**Time Daemon:** `chrony` must prioritize `/dev/pps0` as the absolute UTC reference:
```
refclock PPS /dev/pps0 lock NMEA poll 4 prefer trust
```

### 4.2 Application Level (DualStreamRouter)

- **Hardware Agnosticism:** SDR interaction must remain wrapped in `SoapySDR` (SPEC-004A.2).
- **Forced Clock Assertion:** Before initiating the Kuramoto Coherence Engine, software MUST send `setClockSource("external")` to the HackRF.
- **Telemetry Verification:** Software should query the LBE-1420's NMEA stream via virtual serial port to verify an active GPS fix before allowing data ingestion.

---

## 5. Deprecation Notice

| Deprecated Component | Replacement | Status |
|---------------------|-------------|--------|
| Leo Bodnar Mini GPSDO | Leo Bodnar LBE-1420 GPSDO | **SUPERSEDED** |
| Intel i210-T1 NIC | GPSDO 10 MHz reference | **REMOVED** |
| RTL-SDR (v3/v4) | HackRF One with CLKIN | **TIER 2 ONLY** |
| PTP/IEEE 1588 | GPSDO direct clock injection | **REMOVED** |
| Mini-USB connections | USB-C connections | **SUPERSEDED** |

---

**Technical integrity is our only metric of success.**
