# Release Notes v4.6.0

## DSLV-ZPDI v4.6.0 — LBE-1421 Hardened Operations Stack

### Summary
Production-hardened release integrating Leo Bodnar LBE-1421 GPSDO timing
discipline, installer robustness fixes, and Tier-1 baseline validation.

### Changes
- Installer idempotency and bootstrap reliability improvements
- Dynamic path resolution in shell scripts (preflight, launch, dashboard)
- SoapySDR linkage fix for virtual environment provisioning
- Version synchronization across all authority files

### Verification
- pytest: 49 passed
- orphan_checker: clean
- repo_guard: passed
- version_sync: clean
