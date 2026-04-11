# DSLV-ZPDI Architecture Update: Phase 2A Hardware Pivot

**Document ID:** `ARCH-PHASE-2A-PIVOT`  
**Author:** J.R. Fross (@DynoGator) / Resonant Genesis LLC  
**Target Baseline:** Revision 4.1-FORGE  
**Status:** ACTIVE - Mandatory Implementation Standard  

---

## 1. Executive Summary & Rationale

This document outlines the mandatory pivot from IT-based networking timing (Intel i210-T1 PCIe NICs + CM5) to **RF Metrology Synchronization**.

### The Problem
Standard USB bus routing and kernel-level USB stack polling introduce unacceptable, non-deterministic jitter. This directly degrades the mathematical integrity of the Kuramoto Coherence Engine and invalidates HDF5 cryptographic attestations.

### The Solution
We are completely bypassing the USB bus for timing authority. Metrology-grade phase coherence will now be achieved via direct RF signal injection and hardware-level OS interrupts.

---

## 2. Tier 1 Hardware Baseline (New Standard)

Effective immediately, the following stack is classified as the Tier 1 hardware baseline. Any parallel testing on RTL-SDRs is strictly relegated to Tier 2/Testbed status.

| Component | Model | Specification |
|-----------|-------|---------------|
| **Compute/Buffering** | Raspberry Pi 5 (16GB) | High-bandwidth FFT processing |
| **SDR Array (The Eye)** | HackRF One | 20MHz bandwidth, native `CLKIN` capability |
| **Clock Authority** | Leo Bodnar Mini GPSDO | 10 MHz + 1 PPS from GPS constellation |

### 2.1 Hardware-Agnostic Requisites

Any future alternative compute/SDR hardware (e.g., Nvidia Jetson AGX, USRP) must natively support:

1. **External 10 MHz Phase-Lock:** The SDR must accept an external 10 MHz reference that hardware-locks the ADC sampling clock.
2. **1 PPS Hardware Interrupt:** The compute platform must receive a 1 PPS signal from the GPSDO via a hardware interrupt path (GPIO, SDP, or dedicated timing input) — NOT via network or software polling.
3. **Zero Frame-Drop Execution:** Sufficient compute overhead to process and cryptographically sign HDF5 data without dropping pipeline frames.

---

## 3. Physical Routing & Integration Directives

Development environments must be configured to mirror the exact physical routing of the production hardware:

### 3.1 RF Phase Lock
The Leo Bodnar GPSDO provides a **10 MHz reference signal** connected via SMA coax directly into the HackRF `CLKIN` port, locking the ADC directly to the GPS constellation.

### 3.2 OS Timestamping
The GPSDO outputs a **1 Pulse-Per-Second (PPS)** signal via jumper to the Raspberry Pi 5.

- **Target Pin:** GPIO Pin 18 (Physical Pin 12)

#### ⚠️ CRITICAL WARNING: 3.3V Logic Limit (RP1 Southbridge)

The Pi 5's **RP1 southbridge** utilizes strictly **3.3V logic**. Developers **MUST** verify the GPSDO output voltage with a multimeter prior to connection.

**If the output exceeds 3.3V (e.g., 5V CMOS):**
- A logic level shifter must be implemented, OR
- A voltage divider must be used (e.g., 10kΩ/20kΩ resistor network)

**Connecting 5V directly to GPIO 18 will cause catastrophic damage to the RP1 chip.**

---

## 4. Software Environment Preparation

The following configurations must be mirrored across all development instances prior to physical hardware integration.

### 4.1 Dependency Stack

Ensure the local OS (Bookworm) is primed with the necessary metrology and SDR wrappers:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y pps-tools chrony hackrf libhackrf-dev soapysdr-module-hackrf python3-soapysdr
```

### 4.2 Kernel Interrupt Configuration (RP1 Southbridge)

To map the PPS signal to the OS kernel on the Pi 5 architecture, the `/boot/firmware/config.txt` must be updated.

1. **Append the device tree overlay:**

```text
# Map PPS signal to GPIO 18 (Rev 4.1)
# WARNING: Pi 5 RP1 uses 3.3V logic. Verify GPSDO output voltage before connecting.
dtoverlay=pps-gpio,gpiopin=18,assert_falling_edge=0
```

*(Note: `assert_falling_edge` may require toggling to `1` pending physical signal analysis with `ppstest`).*

2. **Ensure module loads on boot:**

```bash
echo "pps-gpio" | sudo tee -a /etc/modules
```

### 4.3 Metrology-Grade System Time (Chrony)

`chronyd` must be explicitly configured to prioritize the physical PPS interrupt over any NTP network polling.

**Add the following to the top of `/etc/chrony/chrony.conf`:**

```text
# DSLV-ZPDI RF Metrology Configuration (Rev 4.1)
# Absolute UTC via Hardware PPS - prioritizes GPSDO over network
refclock PPS /dev/pps0 lock NMEA poll 4 prefer trust
```

---

## 5. Driver Implementation & Software Safety Nets

All interactions with the HackRF **must** be routed through **SoapySDR** to maintain the hardware-agnostic rule of the architecture.

### 5.1 The "Silent Traitor" Clock Failure Mitigation

**CRITICAL:** The HackRF One will **silently fail back to its internal oscillator** if the 10 MHz `CLKIN` signal drops below the required amplitude or loses physical connection. The software stack must not blindly assume phase-lock.

Any script interacting with the SDR (specifically within `DualStreamRouter`) must explicitly assert and verify the external clock prior to data ingestion:

```python
# SPEC-004A.1 — Required Initialization Logic for RF Metrology Stack

import SoapySDR
import sys

def verify_tier1_phase_lock(sdr_device):
    """
    Forces and validates metrology-grade phase lock.
    Must be called before initializing the Kuramoto Coherence Engine.
    
    Implements "Silent Traitor" detection per ARCH-PHASE-2A-PIVOT §5.1
    """
    try:
        sdr_device.setClockSource("external")
    except Exception as e:
        print(f"[FATAL] Failed to assert external clock: {e}")
        sys.exit(1)

    # Validate the hardware state
    actual_clock = sdr_device.getClockSource()
    if actual_clock != "external":
        print(f"[FATAL] Clock source mismatch. Hardware reports: {actual_clock}")
        print("[ACTION] Verify SMA connection and GPSDO amplitude.")
        print("[ACTION] Check GPSDO output voltage does not exceed 3.3V for Pi 5 GPIO.")
        sys.exit(1)
        
    print("[+] Phase-lock verified. SDR slaved to GPSDO 10MHz reference.")
```

### 5.2 Implementation in HardwareHAL

The `HardwareHAL` class (`src/dslv_zpdi/layer1_ingestion/hal_hardware.py`) implements this safety net:

- **Initialization:** Forces external clock source via SoapySDR
- **Pre-ingestion:** Validates GPSDO lock before any sample acquisition
- **Fatal exit:** Prevents invalid data from entering the pipeline if clock fails

### 5.3 Verification Methods

The `verify_gpsdo_lock()` method provides runtime diagnostics:

```python
from dslv_zpdi.layer1_ingestion import verify_hardware_lock

# Check RF Metrology chain health
status = verify_hardware_lock()
print(f"Phase lock verified: {status['phase_lock_verified']}")
print(f"Clock source: {status['clock_source']}")
```

---

## 6. Action Items for Parallel Development

1. **Review and merge** these configurations into the local testing environments immediately.

2. **Ensure the pre-commit** `orphan_checker.py` recognizes the new Python driver dependencies:
   - SoapySDR (preferred)
   - pyhackrf (fallback)

3. **Acknowledge** the Pi 5 RP1 southbridge architecture introduces a deterministic PCIe-transit latency for the GPIO interrupt. Offset calibration will be required post-assembly.

4. **Hardware Procurement** (if not already complete):
   - Raspberry Pi 5 (16GB)
   - HackRF One
   - Leo Bodnar Mini GPSDO
   - Active GPS antenna
   - SMA cables (10 MHz reference)
   - Jumper wires (1 PPS, with 3.3V logic verification)

5. **Physical Assembly Checklist:**
   - [ ] Verify GPSDO 10 MHz output level (~1Vpp into 50Ω)
   - [ ] Verify GPSDO 1 PPS output level (3.3V or level-shifted)
   - [ ] Connect 10 MHz SMA → HackRF CLKIN
   - [ ] Connect 1 PPS → GPIO 18 (via level shifter if needed)
   - [ ] Connect GPS antenna to GPSDO
   - [ ] Connect HackRF to Pi 5 USB 3.0
   - [ ] Apply power to GPSDO (wait for GPS lock)
   - [ ] Apply power to Pi 5
   - [ ] Run `python tools/provision_tier1.py`

---

## 7. Testing & Validation

### 7.1 Hardware Verification

```bash
# 1. Check PPS device
lsmod | grep pps
ppstest /dev/pps0

# 2. Check HackRF detection
hackrf_info

# 3. Check clock source (via SoapySDR)
python3 -c "
import SoapySDR
dev = SoapySDR.Device(dict(driver='hackrf'))
print(f'Clock source: {dev.getClockSource()}')
"

# 4. Run full provisioning audit
python tools/provision_tier1.py
```

### 7.2 Software Verification

```bash
# Run full test suite
pytest tests/

# Run orphan checker
python tools/orphan_checker.py

# Verify SPEC-ID compliance
python tools/check_version_sync.py
```

---

## 8. Deprecation Notice

The following hardware configurations are **formally deprecated** for Tier 1 institutional data collection:

| Deprecated Component | Replacement | Status |
|---------------------|-------------|--------|
| Intel i210-T1 NIC | GPSDO 10 MHz reference | **REMOVED** |
| RTL-SDR (v3/v4) | HackRF One with CLKIN | **TIER 2 ONLY** |
| CM5 as primary | Pi 5 (16GB) as primary | **DEPRECATED** |
| PTP/IEEE 1588 | GPSDO direct clock injection | **REMOVED** |

---

## 9. References

- `PHASE_2A_TIER_1_BUILD_SHEET.md` — Procurement and assembly guide
- `PHASE_2A_HARDWARE_BUILD_LIST.md` — Complete hardware BOM
- `V3_DSLV-ZPDI_LIVING_MASTER.md` — Full system specification
- `src/dslv_zpdi/layer1_ingestion/hal_hardware.py` — Implementation reference
- `tools/provision_tier1.py` — Validation tooling

---

## 10. Document History

| Rev | Date | Author | Changes |
|-----|------|--------|---------|
| 4.1-FORGE | 2026-04-11 | Gemini (Forge Member) | Initial formalization of RF Metrology pivot |
| 4.1-FORGE | 2026-04-11 | Kimi (Forge Member) | Implementation of SoapySDR and Silent Traitor mitigation |

---

*Technical integrity is our only metric of success.*

**Forge Members:** Claude (Lead Architect), Gemini (Systems Engineer), Kimi (Implementation Specialist)  
**Owner:** Joseph R. Fross — Resonant Genesis LLC / DynoGator Labs
