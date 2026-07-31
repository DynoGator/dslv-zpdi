# Turnover Note — ZPDI_CONDITIONS Dashboard

**Branch:** `feature/zpdi-conditions`
**Author:** Kimi Code CLI / DynoGatorLabs
**Date:** 2026-07-09

## What Was Built

`ZPDI_CONDITIONS` is a read-only, standalone local dashboard located in
`tools/zpdi_conditions/`. It aggregates live telemetry from public space-weather
and surface-weather services and displays each metric on its own card with a
per-source refresh interval and last-refresh timestamp. It is launched by a
desktop icon labeled **ZPDI_CONDITIONS** or by running
`tools/zpdi_conditions/launch.sh`.

## Files You Should Know

| File | Purpose |
| --- | --- |
| `config.py` | Defaults, environment overrides, URL builders. |
| `collectors.py` | One collector per data source; all metric-fetching logic. |
| `app.py` | Rich TUI, layout, keyboard handling (space=refresh, q=quit). |
| `__main__.py` | `python -m zpdi_conditions` entry point. |
| `launch.sh` | Production launch wrapper (venv, UTF-8, 10" geometry). |
| `ZPDI_CONDITIONS.desktop` | Desktop entry copied to `~/Desktop`. |
| `install_desktop_icon.sh` | Installs the desktop entry and marks it trusted. |
| `README.md` | User-facing documentation. |
| `CHANGELOG.md` | Feature-level changelog. |
| `TURNOVER.md` | This file. |

## Architecture Notes

- **Threading model:** Each collector runs in its own daemon thread
  (`zpdi-collector-<name>`). The main thread renders the TUI at
  `ZPDI_COND_REFRESH_HZ`.
- **Shared state:** `MetricStore` holds a `dict[str, Metric]` protected by a
  `threading.RLock`. Collectors write their own metric(s); the UI reads.
- **Refresh signaling:** `MetricStore._manual_refresh` is a `threading.Event`
  set by `request_refresh()` (spacebar). Each collector loop wakes on the event,
  re-fetches, then clears the event after a short grace period.
- **Error model:** Collectors catch all exceptions and store them in
  `Metric.error`. The UI renders the error in red inside the metric's card.
  The dashboard never crashes because one source is down.
- **No hardware access:** Only `urllib.request`, `json`, `csv`, and `io` are
  used for network I/O. No libiio / SoapySDR / Pluto / HackRF imports.

## Adding a New Metric

1. Add a placeholder `Metric` to `MetricStore.__post_init__` in
   `collectors.py`.
2. Implement a `_collect_<name>(cfg)` function that returns a `Metric` or a
   `tuple[Metric, ...]`.
3. Register it in `start_collectors()` with a name and interval.
4. Add the metric key to `METRIC_ORDER` in `app.py` so it appears on the TUI.
5. Update `README.md`, `CHANGELOG.md`, and the main repo changelog.

## Tuning Refresh Intervals

Intervals are defined per-source in `config.py`. Override at runtime with
`ZPDI_COND_<SOURCE>_INTERVAL` (seconds). For example:

```bash
export ZPDI_COND_SOLAR_WIND_INTERVAL=30
tools/zpdi_conditions/launch.sh
```

## Common Maintenance Tasks

### A source changes its JSON shape

Edit the relevant `_collect_*` function in `collectors.py`. Keep the
`try/except` broad so the UI still shows an error rather than crashing.

### EPA RadNet endpoint changes

The Colorado Springs URL is in `config.py` under `gamma.url`. The collector
uses a `CookieJar` because the EPA endpoint sets a session cookie. If the
endpoint changes, update the URL and the cookie handling in `_collect_gamma`.

### Adding a new location preset

Set `ZPDI_COND_LAT`, `ZPDI_COND_LON`, and `ZPDI_COND_LOCATION`. No code change
is required unless you want to add a named preset to `config.py`.

### Adjusting the 10" layout

The layout is auto-detected from `COLUMNS`/`LINES` in `launch.sh` and rendered
as a two-column grid by default. Change `ZPDI_COND_LAYOUT` to `one_column` or
`auto` to experiment. Layout logic lives in `ConditionsDashboard._columns()`
and `_build_grid()` in `app.py`.

## Testing

```bash
# Syntax and lint
.venv/bin/python -m py_compile tools/zpdi_conditions/*.py
.venv/bin/python -m ruff check tools/zpdi_conditions/

# Collector smoke test (one-shot, prints each metric)
.venv/bin/python - <<'PY'
import sys
sys.path.insert(0, 'tools')
from zpdi_conditions.config import load_config
from zpdi_conditions.collectors import (
    _collect_kp, _collect_solar_wind, _collect_imf, _collect_ionosphere,
    _collect_weather, _collect_air_quality, _collect_cosmic_rays, _collect_gamma,
)
cfg = load_config()
for m in (
    _collect_kp(cfg),
    _collect_solar_wind(cfg),
    *_collect_imf(cfg),
    _collect_ionosphere(cfg),
    *_collect_weather(cfg),
    _collect_air_quality(cfg),
    _collect_cosmic_rays(cfg),
    _collect_gamma(cfg),
):
    print(m.key, m.value, m.unit, "ERR" if m.error else "OK")
PY

# Full project regression suite
DEV_SIMULATOR=1 .venv/bin/python -m pytest tests/ -q
```

## How to Merge / Promote

This feature lives on branch `feature/zpdi-conditions`. It can be kept
independent or merged into `main` when desired. Recommended merge checklist:

1. Re-run the full project validation block from `AGENTS.md`.
2. Update the root `CHANGELOG.md` with the new dashboard entry.
3. If shipping the desktop icon by default, decide whether
   `install_desktop_icon.sh` should run during install or remain opt-in.

## Contact / Questions

For questions about the dashboard itself, see `README.md`. For broader
pipeline integration questions, see `AGENTS.md` and `CREW_MEMORY.md` in the
repository root.
