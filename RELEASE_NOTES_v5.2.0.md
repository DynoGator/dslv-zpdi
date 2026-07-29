# DSLV-ZPDI Release Notes — Rev 5.2.0

**Release Date:** 2026-07-28
**Milestone:** Demodulation engine, Full Duplex MIMO vectoring, and mobile-node dashboard refinements
**Status:** Beta — builds on the Rev 5.0.0 PlutoSDR+ / LBE-1421 Tier-1 architecture

## Summary

Rev 5.2.0 extends the Rev 5.x Tier-1 stack with an intelligent demodulation
engine and a Full Duplex MIMO vectoring framework, and folds in the Rev 5.1.0
mobile-node and TUI refinements (including the standalone `ZPDI_CONDITIONS`
conditions dashboard). Dashboard defaults are tuned for live SDR monitoring
out of the box.

## New in 5.2.0

- **Demodulation engine** (`layer1_ingestion`) — supports audio, data, video,
  and telemetry formats with auto-presets.
- **Full Duplex MIMO Vectoring framework** — spatial multiplexing and signal
  vectoring.

### Changed

- Dashboard default configs: Live SDR enabled, gain 0.0, raw modulation,
  sweep mode, center freq 3 GHz, span 40 MHz, plasma palette, LNA 30, VGA 30,
  noise floor -75.0 dBm, ceiling -70.0 dBm.
- Dashboard banner disabled by default.

## Carried forward from 5.1.0 (Mobile Node and TUI Refinements)

- New standalone dashboard package `tools/zpdi_conditions/` aggregating live
  space weather, surface weather, barometric, aerosol, and ionizing-radiation
  metrics for the Penrose, CO tracking footprint (NOAA SWPC, Open-Meteo,
  NMDB neutron monitor, EPA RadNet Colorado Springs).
- Rich two-column TUI optimized for a 10" touchscreen with per-metric refresh
  intervals, self-checking collectors, launch script, and desktop icon.
- No SDR, GPSDO, or radio hardware access; runs in parallel with the main
  `dslv-zpdi` stack without conflicts.
- Mobile node WSS transport: exponential-backoff circuit breaker and corrected
  default ingest URI (`ws://127.0.0.1:8443/`).

## Validation

- `pytest` suite green on simulator (`DEV_SIMULATOR=1`); ruff, mypy,
  orphan-checker, repo-guard, and version-sync all clean.
- Hardware-dependent claims remain gated on physical verification per
  `AGENTS.md` doctrine.
