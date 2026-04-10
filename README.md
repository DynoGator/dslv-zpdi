# DSLV-ZPDI (Distributed Sensor Locational Vectoring)

**Project Phase:** Phase 2A (Hardware Hardening)  
**Revision:** Rev 4.0.2  
**Status:** Software Airtight. Automated Installer Deployed.

## Overview
DSLV-ZPDI is a multi-modal Signals Intelligence (SIGINT) network that translates anomalous multi-spectrum phenomena into institutional-grade, GPS-disciplined HDF5 telemetry.

## Architecture
- **Layer 1 (Ingestion):** Hardware drivers (SDR, GPS/PPS) and phase extraction via HardwareHAL.
- **Layer 2 (Core):** KCET-ATLAS Kuramoto coherence engine and statistical outlier detection.
- **Layer 3 (Telemetry):** Dual-stream routing, HDF5 persistence, and cryptographic attestation.

## Installation & Deployment
The canonical way to install DSLV-ZPDI is via the automated installer:

```bash
# Clone the repository
git clone https://github.com/DynoGator/dslv-zpdi.git
cd dslv-zpdi

# Run the installer (requires sudo for hardware audit packages)
sudo ./install_dslv_zpdi.sh --tier1
```

For virtualized environments (skip hardware checks):
```bash
sudo ./install_dslv_zpdi.sh --tier1 --simulator
```

## Pre-Flight Check (Manual)
If not using the installer, you can run manual checks:
```bash
# Run core test suite
pytest tests

# Verify SPEC-ID compliance
python tools/orphan_checker.py
```

## Hardware Deployment (Phase 2A)
Refer to `PHASE_2A_HARDWARE_BUILD_LIST.md` for precision timing (i210-T1) and supercapacitor power (Tier 2) specifications.
