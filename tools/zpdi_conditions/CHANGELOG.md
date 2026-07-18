# Changelog — ZPDI_CONDITIONS Dashboard

All notable changes to the `tools/zpdi_conditions/` dashboard are documented
here. This changelog follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-09

### Added
- Initial standalone local dashboard (`tools/zpdi_conditions/`).
- Twelve live metric cards covering space weather, surface weather, barometric,
  aerosol density, and ionizing radiation.
- Per-metric refresh intervals and last-refresh timestamps displayed on every
  card.
- Manual refresh triggered by the spacebar.
- Two-column TUI layout optimized for a 10" touchscreen (1280×800 class).
- Clickable desktop icon `ZPDI_CONDITIONS.desktop` plus `install_desktop_icon.sh`.
- `launch.sh` wrapper that forces UTF-8, sets 10" terminal geometry, and uses
  the project venv.
- Self-checking collectors: each metric shows a specific in-card error message
  when its source fails.
- No SDR/hardware dependencies; runs safely alongside `dslv-zpdi`.

### Data Sources (v1.0.0)
- NOAA SWPC Planetary K-index
- NOAA RTSW solar wind (`rtsw_wind_1m.json`)
- NOAA RTSW magnetometer (`rtsw_mag_1m.json`)
- NOAA Space Weather Scales
- Open-Meteo forecast API
- Open-Meteo Air Quality API
- NMDB real-time neutron monitor
- EPA RadNet Colorado Springs CSV

### Known Limitations
- EPA RadNet collector relies on the current `cdx-radnet-rest` CSV endpoint and
  may need adjustment if EPA changes their download URLs.
- NMDB `realtime.txt` reports a single representative station per line; the
  displayed station code depends on NMDB's current feed.
- Wind direction is derived from 10 m forecast wind vectors.
- Pressure is reported as mean sea level (MSL) to match NWS/local reporting.
