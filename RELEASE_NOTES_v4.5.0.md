# Release Notes v4.5.0

**Date:** 2026-04-24

## Summary
LBE-1421 hardened operations stack with fully instrumented dashboard, automated email telemetry pipeline, interactive geospatial mapping, hardened project launcher, and field baseline coherence integration.

## Added
- **Dashboard v2** (`tools/dashboard/`)
  - 5" DSI-optimized layout with compact/full banner modes and startup animation.
  - NOAA Space Weather integration (`noaa.py`) for real-time Kp, solar wind, and aurora alerts.
  - New panels: RF Anomaly, Storm Watch, Weather Overlay, Waterfall spectrogram, enhanced Hardware/Logs/Notifications/Pipeline/System views.
  - `config.py` with TOML-based runtime configuration (`config/dashboard.toml.example`).
- **Auto-Email Pipeline** (`tools/mailer/`)
  - Modular backends (`backends.py`) supporting SMTP, SendGrid, and AWS SES.
  - `send_data.py` — daily/alert-triggered telemetry dispatch with HDF5 attachment support.
  - `configure.py` — interactive TUI for credential and recipient management.
  - `send_now.sh` — one-shot manual send wrapper.
  - Example config: `config/email.example.yaml`.
- **Interactive Mapping** (`tools/mapping/`)
  - `render_map.py` — Folium-based HTML map generation with anomaly clustering and GPS track overlay.
  - `aggregate.py` — HDF5 telemetry aggregator for multi-node map layers.
  - `open_map.sh` / `open_hdf5_browser.sh` — quick-launch helpers.
- **Project Launcher** (`tools/launch_project.sh`)
  - Clean-boot sequence with preflight checks, dual-window terminal spawn (dashboard + logs), and autostart integration.
  - `tools/toggle_simulator.sh` — runtime simulator/hardware mode switch with systemd service restart.
- **Test Infrastructure**
  - `tests/conftest.py` — shared pytest fixtures and monkey-patched HAL helpers.
- **Configuration Examples**
  - `config/dashboard.toml.example`
  - `config/email.example.yaml`
  - `config/sensor_location.example.yaml`

## Changed
- `main_pipeline.py` — integrated simulator resolution via `_resolve_simulator()` with env/CLI priority; graceful signal handling (`SIGINT`/`SIGTERM`); `DSLV_SIM_DEMO` mode for 4-node rotation gate testing.
- `wiring.py` — baseline state path resolution with env override (`DSLV_BASELINE_STATE_PATH`).
- `hal_simulated.py` — simulator fidelity improvements aligned to SPEC-005A.HAL-SIM.
- `.gitignore` — expanded to cover agent workspaces (`GEMINI-HOME/`, `CLAUDE-HOME/`), local runtime configs, and artefact directories.
- `README.md` — bumped to Rev 4.5.0 with LBE-1421 hardened operations stack documentation.

## Fixed
- Launcher race conditions on clean-boot dual-window startup (lxterminal UTF-8 codec guard, service dependency ordering).
- Pipeline baseline state not loaded into coherence engine on cold start.

## Version Alignment
- Project version bumped to **4.5.0** across `pyproject.toml`, `README.md`, `CHANGELOG.md`, `install_dslv_zpdi.sh`, and `tests/test_pipeline.py`.
