# DSLV-ZPDI Release Notes — Rev 5.0.0

**Release Date:** 2026-06-15  
**Milestone:** Tier-1 RF metrology hardware pivot to PlutoSDR+ class devices  
**Status:** Beta — software architecture complete, hardware qualification pending physical verification gates

## Summary

Rev 5.0.0 replaces the HackRF One as the canonical Tier-1 RF metrology target
with a capability-based qualification model centered on the HamGeek AD9363
PlutoSDR+ class device and the Leo Bodnar LBE-1421 GPSDO. The HackRF One
remains supported as an optional legacy backend and historical performance
floor.

This is a major architectural refactor:

- Timing authority, SDR backend, frequency translation, and qualification
  policy are now decoupled and composable.
- Timing evidence is represented explicitly and granularly; no more misleading
  `phase_lock_verified` Boolean.
- HDF5 finalization is atomic and includes an event hash chain.
- Production HMAC key handling is hardened and fails closed.

## New Components

| Component | Path | SPEC |
|-----------|------|------|
| Composed HAL | `src/dslv_zpdi/layer1_ingestion/hardware_hal.py` | SPEC-005A.HAL |
| Timing subpackage | `src/dslv_zpdi/layer1_ingestion/timing/` | SPEC-005A.TIMING |
| SDR backend subpackage | `src/dslv_zpdi/layer1_ingestion/sdr/` | SPEC-004A |
| Pluto IIO backend | `src/dslv_zpdi/layer1_ingestion/sdr/pluto_iio.py` | SPEC-004A.PLUTO |
| Qualification engine | `src/dslv_zpdi/layer1_ingestion/sdr/qualification.py` | SPEC-004A.QUAL |
| Frequency translation | `src/dslv_zpdi/layer1_ingestion/frequency_translation/` | SPEC-004A.FREQ |
| Key provider | `src/dslv_zpdi/core/key_provider.py` | SPEC-018 |
| Config models | `src/dslv_zpdi/config_models.py` | SPEC-004A.CONFIG |
| CLI package | `src/dslv_zpdi/cli/` | SPEC-011.CLI |
| Node profiles | `config/node_profiles/` | SPEC-004A |

## Validation

- 143 tests pass in simulator mode.
- Orphan checker, version sync, and repo guard pass.
- ruff lint passes.

## Known Limitations / Remaining Physical Gates

- Exact HamGeek PCB revision: UNVERIFIED_PHYSICAL_PROPERTY
- Timing connector family (U.FL/MMCX/etc.): UNVERIFIED_PHYSICAL_PROPERTY
- 10 MHz/PPS direction and electrical levels: UNVERIFIED_PHYSICAL_PROPERTY
- SDR PPS input reaching FPGA fabric: UNVERIFIED_PHYSICAL_PROPERTY
- External reference software detection on the device: UNVERIFIED_PHYSICAL_PROPERTY

Primary institutional output remains fail-closed until these gates pass.
