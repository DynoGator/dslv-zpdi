# DSLV-ZPDI Release Notes — v4.3.0

**Revision:** Rev 4.3.0 (Multi-OS Compliance & Installer Hardening)
**Date:** 2026-04-15
**Codename:** MULTI-OS-PIVOT

## Summary

Version 4.3.0 introduces a hardened, multi-OS compatible deployment architecture. It formally validates and supports **Raspberry Pi OS Trixie (Debian 13)** alongside **Bookworm (Debian 12)**. This release also addresses the "SoapySDR Venv Isolation" problem by introducing an automated linkage layer for hardware-agnostic SDR drivers.

## Changes

### Installation & Deployment
- **OS Detection:** `install_dslv_zpdi.sh` now detects Debian version and codename to ensure path compliance (e.g., firmware config location).
- **SoapySDR Linkage:** Automatically symlinks system `python3-soapysdr` into the project's virtual environment. This enables the high-performance C++ bindings to be used within the isolated Python environment without requiring complex source builds.
- **Improved venv creation:** Hardened venv setup for Python 3.12/3.13 compatibility.

### Compatibility
- **Trixie (Debian 13) Support:** Validated on Python 3.13.5. All core algorithms (Kuramoto coherence, HDF5 persistence) are verified stable.
- **Bookworm (Debian 12) Support:** Retained 100% compatibility for existing Phase 2A deployments.

## Version Alignment
- `pyproject.toml`: 4.2.1 → 4.3.0
- `README.md`: Rev 4.2.1 → Rev 4.3.0
- `install_dslv_zpdi.sh`: Rev 4.2.1 → Rev 4.3.0
- `MASTER_SPEC.md` / `V3_DSLV-ZPDI_LIVING_MASTER.md`: Rev 4.2.1 → Rev 4.3.0

## Validation
- 31/31 tests passing on Trixie (Python 3.13)
- SPEC-ID orphan checker: clean
- Version sync: aligned
- SoapySDR venv linkage: VERIFIED
