# ZPDI_CONDITIONS Local Dashboard

A standalone, read-only local dashboard that aggregates live space-weather,
surface-weather, barometric, aerosol, and ionizing-radiation metrics for the
Penrose, CO tracking footprint. It is designed to run alongside the main
`dslv-zpdi` pipeline without touching SDR hardware.

## Quick Start

From the repository root:

```bash
tools/zpdi_conditions/launch.sh
```

Or install the desktop icon and double-click **ZPDI_CONDITIONS**:

```bash
tools/zpdi_conditions/install_desktop_icon.sh
```

Keyboard controls while the dashboard is running:

- `space` — force an immediate refresh of every metric
- `q` or `Ctrl+C` — quit

## Metrics & Sources

| Category | Metric | Source | Default Refresh |
| --- | --- | --- | --- |
| Space Weather | Planetary K-index (Kp) | NOAA SWPC planetary K-index JSON | 5 min |
| Space Weather | Solar Wind Speed (Vsw) | NOAA RTSW `rtsw_wind_1m.json` | 1 min |
| Space Weather | IMF Total Field (Bt) | NOAA RTSW `rtsw_mag_1m.json` | 1 min |
| Space Weather | IMF Vertical Alignment (Bz) | NOAA RTSW `rtsw_mag_1m.json` | 1 min |
| Space Weather | Ionospheric Density Anomalies | NOAA Space Weather Scales (S-scale) | 10 min |
| Surface Weather | Ambient Temperature | Open-Meteo forecast API | 15 min |
| Surface Weather | Wind Speed & Direction | Open-Meteo forecast API | 15 min |
| Surface Weather | Relative Humidity (RH) | Open-Meteo forecast API | 15 min |
| Barometric | Station Pressure | Open-Meteo forecast API (MSL) | 15 min |
| Aerosol Density | PM2.5 / Wildfire Smoke | Open-Meteo Air Quality API | 30 min |
| Ionizing Radiation | Ambient Gamma Rate | EPA RadNet Colorado Springs CSV | 30 min |
| Ionizing Radiation | Secondary Cosmic Ray Flux | NMDB real-time neutron monitor text | 15 min |

All sources are public HTTP endpoints. The dashboard does not use libiio,
SoapySDR, HackRF, PlutoSDR, or any local RF hardware.

## Configuration

Set environment variables before launching:

| Variable | Default | Description |
| --- | --- | --- |
| `ZPDI_COND_LOCATION` | `Penrose, CO` | Display location name |
| `ZPDI_COND_LAT` | `38.425` | Latitude |
| `ZPDI_COND_LON` | `-105.023` | Longitude |
| `ZPDI_COND_REFRESH_HZ` | `2.0` | TUI render rate |
| `ZPDI_COND_LAYOUT` | `two_column` | `two_column`, `one_column`, or `auto` |
| `ZPDI_COND_<SOURCE>_INTERVAL` | per source | Override refresh interval in seconds |

Example:

```bash
export ZPDI_COND_LAT=39.7392
export ZPDI_COND_LON=-104.9903
export ZPDI_COND_LOCATION="Denver, CO"
tools/zpdi_conditions/launch.sh
```

## Error Handling

If a collector fails, the dashboard displays a specific error message in the
metric's own card instead of crashing or showing stale data. Common causes:

- Network outage or DNS failure
- Remote API shape change
- EPA RadNet cookie/session expiry (auto-retried)
- Rate limiting from Open-Meteo

## Coexistence with DSLV-ZPDI

`ZPDI_CONDITIONS` is intentionally isolated from the main pipeline:

- No shared hardware
- No shared Python modules with the SDR code path
- Runs as an ordinary user process
- Can be started, stopped, and restarted independently

The main `dslv-zpdi` stack always takes priority. This dashboard will never
hold an SDR, GPSDO, or serial port open.

## Development

```bash
.venv/bin/python -m py_compile tools/zpdi_conditions/*.py
.venv/bin/python -m ruff check tools/zpdi_conditions/
```

To run all project tests:

```bash
DEV_SIMULATOR=1 .venv/bin/python -m pytest tests/ -q
```

## License

Same as the parent `dslv-zpdi` project.
