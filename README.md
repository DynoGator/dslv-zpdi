# DSLV-ZPDI (Distributed Sensor Locational Vectoring)

**Project Phase:** Phase 2A (Hardware Transition - RF Metrology)  
**Revision:** Rev 4.1-PIVOT  
**Status:** Hardware Airtight. HackRF + GPSDO Architecture Deployed.

## Overview
DSLV-ZPDI is a multi-modal Signals Intelligence (SIGINT) network that translates anomalous multi-spectrum phenomena into institutional-grade, GPS-disciplined HDF5 telemetry.

**Phase 2A RF Metrology Pivot:** We have transitioned from IT Network Timing (PTP/i210-T1) to RF Metrology Timing (GPSDO/HackRF). This achieves hardware-level ADC phase coherence by injecting an atomic-level reference directly into the SDR front-end.

## Architecture
- **Layer 1 (Ingestion):** Hardware drivers (HackRF + GPSDO) and phase extraction via HardwareHAL.
- **Layer 2 (Core):** KCET-ATLAS Kuramoto coherence engine and statistical outlier detection.
- **Layer 3 (Telemetry):** Dual-stream routing, HDF5 persistence, and cryptographic attestation.

## Hardware Stack (Phase 2A Primary)

| Component | Model | Purpose |
|-----------|-------|---------|
| Compute | Raspberry Pi 5 (16GB) | High-bandwidth FFT processing, HDF5 storage |
| SDR | HackRF One | RF ingestion with 20 MHz bandwidth, CLKIN for GPSDO |
| Clock Authority | Leo Bodnar Mini GPSDO | 10 MHz reference + 1 PPS from GPS constellation |

### Physical Wiring
1. **GPSDO 10 MHz SMA Output** → **HackRF CLKIN** (hardware ADC phase-lock)
2. **GPSDO 1 PPS** → **Pi 5 GPIO 18** (UTC epoch anchoring via pps-gpio)
3. **HackRF USB** → **Pi 5 USB 3.0** (data transfer - USB jitter now irrelevant)

## Installation & Deployment

### Prerequisites
- Raspberry Pi 5 (16GB) or compatible
- HackRF One with GPSDO-connected 10 MHz reference
- Leo Bodnar Mini GPSDO (or equivalent GPS-disciplined oscillator)
- GPS antenna with clear sky view

### Automated Installation
```bash
# Clone the repository
git clone https://github.com/DynoGator/dslv-zpdi.git
cd dslv-zpdi

# Configure PPS on Pi 5
echo "dtoverlay=pps-gpio,gpiopin=18" | sudo tee -a /boot/firmware/config.txt
sudo reboot

# Install system dependencies
sudo apt update
sudo apt install -y pps-tools chrony hackrf libhackrf-dev

# Install Python dependencies (includes pyhackrf)
sudo pip install pyhackrf

# Run the installer
sudo ./install_dslv_zpdi.sh --tier1
```

### Hardware Verification
```bash
# Verify PPS is working
lsmod | grep pps
ppstest /dev/pps0

# Verify HackRF detection
hackrf_info

# Verify GPSDO clock lock
python -c "from dslv_zpdi.layer1_ingestion import verify_hardware_lock; print(verify_hardware_lock())"
```

### Simulator Mode (No Hardware)
```bash
sudo ./install_dslv_zpdi.sh --tier1 --simulator
```

## Pre-Flight Check (Manual)
```bash
# Activate virtual environment
source .venv/bin/activate

# Run core test suite
pytest tests

# Verify SPEC-ID compliance
python tools/orphan_checker.py

# Check timing health
python tools/check_timing.py
```

## Hardware Agnosticism Standard (SPEC-004A.2)

While the Pi 5 + HackRF + GPSDO stack is our Phase 2A reference, alternative hardware is permitted if it meets these criteria:

1. **External 10 MHz reference input** to hardware-lock the SDR's ADC sampling clock
2. **1 PPS hardware interrupt** capability (GPIO, SDP, or dedicated timing input)
3. **Sufficient compute** for Kuramoto coherence math without frame drops

### Permissible Alternatives
- Nvidia Jetson AGX Orin + USRP B200 + GPSDO
- Intel NUC + LimeSDR + M.2 timing card
- Any Linux SBC + CLKIN-capable SDR + GPS-disciplined 10 MHz source

### Tier 2 / Testbed (RTL-SDR)
The RTL-SDR (v3/v4) is relegated to Tier 2 / Testbed role only. It lacks external clock input and cannot achieve hardware-level phase coherence. Acceptable for:
- Local software pipeline validation
- Algorithm development
- Swarm heuristic detection

**RTL-SDR data MUST NOT enter Tier 1 primary stream.**

## Documentation
- `PHASE_2A_HARDWARE_BUILD_LIST.md` - Complete procurement list with verified links
- `PHASE_2A_TIER_1_BUILD_SHEET.md` - Step-by-step assembly and wiring guide
- `V3_DSLV-ZPDI_LIVING_MASTER.md` - Full system specification and theory
- `MASTER_SPEC.md` - Canonical SPEC-ID law layer

## Scientific Justification

### The USB Jitter Problem (Deprecated Architecture)
The previous IT Network approach (Intel i210-T1 + RTL-SDR) had a fatal flaw:
- SDR sampled with free-running crystal
- USB bus introduced variable microsecond delays
- OS timestamped packets *upon arrival*, not when RF wave hit antenna

This mathematically invalidated true phase coherence across distributed nodes.

### The RF Metrology Solution (Current Architecture)
By locking the HackRF's ADC directly to the GPS constellation via 10 MHz CLKIN:
- Phase relationships are preserved at the analog level
- USB jitter affects only data transfer latency, not sample timing
- Every IQ sample carries GPS-disciplined phase information
- Skeptics cannot cite local thermal noise—phase alignment proves external events

## Project Governance
- **Owner:** Joseph R. Fross (Resonant Genesis LLC / DynoGator Labs)
- **Repository:** https://github.com/DynoGator/dslv-zpdi
- **License:** MIT

## Technical Integrity
All code modules include SPEC-ID docstrings. The `tools/orphan_checker.py` script enforces compliance. Commits without valid SPEC-IDs will be rejected.
