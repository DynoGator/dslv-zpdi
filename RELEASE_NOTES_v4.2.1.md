# DSLV-ZPDI Release Notes — v4.2.1

**Revision:** Rev 4.2.1 (Dependency Hotfix)
**Date:** 2026-04-15
**Codename:** LBE-1421-HOTFIX

## Summary

Version 4.2.1 is a maintenance release that corrects an invalid dependency requirement in the core software stack. Version 4.2.0 incorrectly specified `pyhackrf>=1.0.0`, which is not currently available on PyPI (latest stable is 0.2.0). This prevented clean installation via `pip` and the automated installer.

## Changes

### Software
- Updated `pyproject.toml` and `requirements.txt` to require `pyhackrf>=0.2.0`.
- Verified 100% test pass rate with the corrected dependency.

### Installation
- Updated `install_dslv_zpdi.sh` to Rev 4.2.1.
- Validated installer in `--simulator` mode.

## Version Alignment
- `pyproject.toml`: 4.2.0 → 4.2.1
- `README.md`: Rev 4.2.0 → Rev 4.2.1
- `install_dslv_zpdi.sh`: Rev 4.2.0 → Rev 4.2.1
- `MASTER_SPEC.md` / `V3_DSLV-ZPDI_LIVING_MASTER.md`: Rev 4.2.0 → Rev 4.2.1

## Validation
- 31/31 tests passing
- SPEC-ID orphan checker: clean
- Version sync: aligned
