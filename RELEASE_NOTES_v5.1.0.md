# DSLV-ZPDI v5.1.0 (Consolidation & Housekeeping)
**Date:** 2026-07-18

This is a consolidation release focused on integrating the Pi5 node work (`tools/zpdi_conditions/`) and executing a do-no-harm housekeeping pass on the repository.

- **No behavior change to Pluto/GPSDO stack**. The operational SDR/timing paths remain locked and active.
- **HackRF legacy support reaffirmed**. Backwards compatibility with HackRF paths has been verified and retained.
- Dependabot PRs with failing CI tests have been closed as stale.

All tests remain green (184/184) and the version strings are synchronized.
