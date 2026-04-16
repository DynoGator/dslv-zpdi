# Release Notes v4.4.0

**Date:** 2026-04-15

## Summary
Production pipeline loop, live HardwareHAL wiring, canonical HAL factory, field baseline capture script, installer hardening, and modality expansion hooks.

## Added
- `src/dslv_zpdi/main_pipeline.py` — SPEC-011 production pipeline loop with `--field` baseline mode.
- `tools/capture_baseline.py` — 72 h passive baseline capture script (SPEC-009.1).
- `src/dslv_zpdi/layer1_ingestion/hal_factory.py` — canonical SPEC-005A.4 factory with typed `get_hal()`.
- Hilbert phase extraction in `HardwareHAL` and `SimulatedHAL` (Layer 1 per SPEC-005).
- Thermal/acoustic ingest hooks in `HardwareHAL` (Layer 1 modality expansion).
- udev rules deployment (`99-pps.rules`, `52-hackrf.rules`) and `systemctl enable chrony` in installer.
- CI matrix expansion for Python 3.10–3.13 and Pi 5 self-hosted hardware runners.
- RP1 3.3V hard enforcement guard in `provision_tier1.py` and build sheet.

## Changed
- `hal_hardware.py` — integrated NMEA telemetry into `ingest_gps_pps()`, 64-item IQ preview, Hilbert phase extraction.
- `payload.py`, `tier1_policy.py`, `hdf5_writer.py` — schema bumped to 3.2.
- Version alignment to Rev 4.4.0 across all canonical sources.
