# DSLV-ZPDI Release Notes — v4.2.0

**Revision:** Rev 4.2.0 (LBE-1420 Hardware Pivot)
**Date:** 2026-04-11
**Codename:** LBE1420

## Summary

Version 4.2.0 implements the mandatory hardware migration from the Leo Bodnar Mini GPSDO to the **Leo Bodnar LBE-1420 GPSDO** across the entire project. This update eliminates the fragile Mini-USB connection, adds software-observable NMEA telemetry, and leverages the LBE-1420's native 3.3V CMOS output for direct Pi 5 GPIO compatibility without level-shifting.

Additionally, this release introduces the RF & Magnetic Shielding design documentation for the cyberdeck chassis build.

## Breaking Changes

- **GPSDO Model:** Leo Bodnar Mini GPSDO is formally **deprecated**. All Tier 1 deployments must use the LBE-1420.
- **Dependencies:** `pyrtlsdr` removed from core dependencies (Tier 2 only). Replaced with `pyhackrf` as core SDR dependency.
- **BOM Updated:** ANT500 antenna, SMA cabling, and jumper wires added to mandatory Tier 1 BOM.

## Changes

### Hardware
- Migrated Clock Authority from Leo Bodnar Mini GPSDO to **LBE-1420 GPSDO** (USB-C, NMEA, 3.3V CMOS)
- Added Great Scott Gadgets **ANT500** antenna (75 MHz - 1 GHz) to Tier 1 BOM
- Added SMA Male-to-Male coaxial cable (50 Ohm, ≤ 1FT) specification
- Added premium F-to-F jumper wire (2.54mm pitch) specification for PPS interconnect
- Updated physical routing protocol with LBE-1420-specific wiring instructions
- Removed level-shifter requirement for PPS line (LBE-1420 outputs 3.3V natively)

### Software
- Added `verify_nmea_telemetry()` method to `HardwareHAL` for LBE-1420 NMEA stream verification
- Added NMEA check to `provision_tier1.py` validation suite
- Updated `hal_hardware.py` source strings from `gpsdo_leo_bodnar_mini` to `gpsdo_leo_bodnar_lbe1420`
- Removed `pyrtlsdr` from core dependencies (moved to optional/Tier 2)
- Added `pyhackrf>=1.0.0` to core dependencies
- Added Python 3.12/3.13 classifiers to pyproject.toml
- Updated installer script to Rev 4.2.0, removed `rtl-sdr`/`librtlsdr0` from base packages

### Documentation
- Created `docs/HARDWARE_CHANGE_JUSTIFICATION.md` (SPEC-UPDATE-PHASE-2A-LBE1420)
- Created `docs/RF_MAGNETIC_SHIELDING.md` — cyberdeck chassis shielding design
- Updated all hardware references across 20+ files from Mini GPSDO to LBE-1420
- Synchronized version strings to 4.2.0 across pyproject.toml, README, installer, tests, specs, and tools
- Updated RP1 voltage warnings to reflect LBE-1420 native 3.3V compatibility

### Version Alignment
- `pyproject.toml`: 4.0.2.4 → 4.2.0
- `README.md`: Rev 4.1-PIVOT → Rev 4.2.0
- `install_dslv_zpdi.sh`: Rev 4.0.2.4 → Rev 4.2.0
- `CONTRIBUTING.md`: Rev 4.0.2 → Rev 4.2.0
- `MASTER_SPEC.md` / `V3_DSLV-ZPDI_LIVING_MASTER.md`: Rev 4.0.2 → Rev 4.2.0
- All HAL modules: Rev 4.1-FORGE/4.1-PIVOT → Rev 4.2-LBE1420

## Validation

- 31/31 tests passing
- SPEC-ID orphan checker: clean
- Version sync: aligned
