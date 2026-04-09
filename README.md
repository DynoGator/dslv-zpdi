# DSLV-ZPDI (Distributed Sensor Locational Vectoring)

**Project Phase:** Phase 2A (Hardware Hardening)  
**Revision:** Rev 3.4.2  
**Status:** Software Airtight. Proceeding to Hardware.

## Overview
DSLV-ZPDI is a multi-modal Signals Intelligence (SIGINT) network that translates anomalous multi-spectrum phenomena into institutional-grade, GPS-disciplined HDF5 telemetry.

## Architecture
- **Layer 1 (Ingestion):** Hardware drivers (SDR, GPS/PPS) and phase extraction.
- **Layer 2 (Core):** KCET-ATLAS Kuramoto coherence engine and statistical outlier detection.
- **Layer 3 (Telemetry):** Dual-stream routing, HDF5 persistence, and cryptographic attestation.

## Installation
```bash
pip install -r requirements.txt
pip install -e .
```

## Pre-Flight Check (Validation)
```bash
# Run core test suite (10/10)
python tests/test_pipeline.py

# Verify SPEC-ID compliance
python tools/orphan_checker.py
```

## Hardware Deployment (Phase 2A)
Refer to `PHASE_2A_HARDWARE_BUILD_LIST.md` for precision timing (i210-T1) and supercapacitor power (Tier 2) specifications.
