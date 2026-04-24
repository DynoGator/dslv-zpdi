# DSLV-ZPDI Session Report — 2026-04-24

**Session:** UX integration & polish
**Operator:** Joseph R. Fross
**Platform:** Raspberry Pi 5 + HackRF + LBE-1420 GPSDO (pending) + 5" DSI
**Branch:** `main` (uncommitted — see "Change log" below)
**Version:** v4.5.0 (unchanged) → working toward v4.6.0-ux

## 1. Executive summary

Scope delivered:

1. Dashboard compact layout tuned for the 800×480 DSI screen, with
   auto-detection, a live `c` toggle, and launcher-aware geometry.
2. HDF5 inspection tools installed (`hdf5-tools` apt, `h5py` +
   `h5glance` pip). `vitables` was removed because it forced a numpy 2
   upgrade that breaks `pyhackrf`; the downgrade back to numpy 1.26.4
   was restored and verified.
3. Interactive satellite map generator built from scratch
   (`tools/mapping/`) — aggregates primary HDF5 + secondary JSONL,
   renders a Folium HTML file with ESRI World Imagery + OSM fallback,
   red pins for tier-1 / blue pins for tier-2, anchor marker, antenna
   cone, layer control, legend, clustered rendering.
4. Auto-email pipeline built (`tools/mailer/`) — aggregates latest
   tier-1 HDF5 + tier-2 JSONL + current map into a `.tar.gz`, sends
   via Gmail SMTP App Password with a pluggable backend abstraction
   so future clients (SES, O365, local MTA) drop in without touching
   the bundler.
5. Four new desktop icons (Map / Send Data / Email Setup / HDF5
   Browser) for one-click access.
6. Sensor-location config surfaced (`config/sensor_location.example
   .yaml`) and auto-staged to `~/.config/dslv-zpdi/sensor_location.yaml`
   on first run so the map is never empty.

Nothing in the live capture pipeline was modified. All new tooling
lives under `tools/mapping/` and `tools/mailer/` and is independent of
the running `dslv-zpdi.service`.

## 2. Work performed

### 2.1 Dashboard compact mode

Files touched:
- `tools/dashboard/app.py` (+52 / -12)
- `tools/launch_project.sh` (+32 / -5)
- `tools/dashboard/READ_ME.md` (+1)

Details:
- New `_is_compact()` helper flips on when `shutil.get_terminal_size()`
  reports `< 140` cols, or when `DSLV_DASHBOARD_COMPACT=1`.
- `build_layout(..., compact=True)` returns a 2×2 status grid (system /
  pipeline over hardware / anomaly), a shorter banner (4 rows vs 9),
  and a trimmed footer.
- Runtime `c` keybinding toggles compact without restarting.
- Launcher reads screen resolution via `xrandr`; on ≤ 1024×600
  displays it skips the second waterfall window (would not fit
  800×480 anyway), exports `DSLV_DASHBOARD_COMPACT=1`, and shrinks
  lxterminal geometry to `92×24`.

### 2.2 HDF5 analysis toolchain

- `apt install hdf5-tools` → `h5ls`, `h5dump`, `h5stat`, `h5diff`,
  `h5repack`, `h5copy`.
- `pip install h5glance` (terminal structure browser — note: h5glance
  has an unrelated pager bug on Python 3.13, use `h5ls -r` as the
  reliable fallback).
- `pip install pandas folium` for map rendering.
- **Regression averted:** `vitables` install pulled in `numpy==2.4.4`,
  which breaks the `pyhackrf 0.2.0` (`numpy<2`) pin. Reverted to
  `numpy==1.26.4` and uninstalled ViTables. Runtime stack verified:
  `hackrf`, `h5py`, `folium`, `pandas`, `dslv_zpdi` all import
  cleanly. **Do not reinstall ViTables** without first upgrading
  `pyhackrf` to a numpy-2-compatible release.

### 2.3 Map generator (`tools/mapping/`)

- `aggregate.py` — walks every HDF5 under `output/primary/` and every
  line of `output/secondary/quarantine.jsonl`. Because the event
  schema has no per-event GPS (events are anchored to the sensor,
  not to a moving target), each event is scattered on a deterministic
  pseudo-random ring around the anchor:
    - Primary: inside a 35° cone along the antenna heading, 30–80 m.
    - Secondary: random bearing on a configurable secondary ring
      (default 150 m).
  Scatter is seeded from `md5(source || event_id)` so the same event
  lands on the same pixel every render — no jitter on reload.
- `render_map.py` — Folium map with:
    - ESRI World Imagery (default, no API key)
    - OSM streets (fallback)
    - ESRI Labels overlay
    - Anchor marker + antenna-cone polygon
    - Primary / Secondary feature groups, each with `MarkerCluster`
      so 2000+ events render without slowing the browser
    - Floating legend + LayerControl
  Invocation: `venv/bin/python tools/mapping/render_map.py --out
  ~/.local/share/dslv-zpdi/map.html --open`.
- `open_map.sh` — desktop-icon launcher. Regenerates map, opens in
  `xdg-open`; if regen fails, opens the previous map so the click is
  never dead.
- `open_hdf5_browser.sh` — menu-driven `h5ls`/`h5dump`/`h5stat`
  interactive browser for the 20 most recent captures.

### 2.4 Email pipeline (`tools/mailer/`)

- `backends.py` — pluggable send dispatch. `gmail` and `smtp` today;
  add `BACKENDS["ses"] = send_ses` etc. without touching the bundler.
- `send_data.py` — bundles latest primary HDF5 + full secondary
  JSONL + map HTML into a `.tar.gz` with a `manifest.json` listing
  sha256 + sizes + inclusion reasons. Honours
  `max_attachment_mb` (default 20 MB, matches Gmail's limit).
  `--dry-run` builds but does not send; `--regen-map` forces a fresh
  map.
- `configure.py` — tkinter GUI (stdlib only). Three tabs:
  Account (backend, user, App Password, host/port), Recipients
  (one per line), Options (tier inclusion, subject prefix,
  attachment cap). Saves to `~/.config/dslv-zpdi/email.yaml` with
  `chmod 0600`.
- `send_now.sh` — desktop-icon launcher. If no config found, opens
  the GUI; otherwise runs the sender with `--regen-map`.

### 2.5 Desktop icons

Added to `~/Desktop/`:
- `DSLV-ZPDI-Map.desktop`
- `DSLV-ZPDI-Send-Data.desktop`
- `DSLV-ZPDI-Email-Setup.desktop`
- `DSLV-ZPDI-HDF5.desktop`

### 2.6 Config surface

- `config/sensor_location.example.yaml` (new) — anchor lat/lon,
  antenna heading, secondary ring radius.
- `config/email.example.yaml` (new) — backend, SMTP creds,
  recipients, per-tier include toggles.
- Auto-staged `~/.config/dslv-zpdi/sensor_location.yaml` so the map
  is never empty on first run.

## 3. Change log

```
tools/dashboard/app.py                  modified   compact layout + c keybinding
tools/dashboard/panels/waterfall.py     modified   (untouched this session; pre-existing uncommitted work)
tools/dashboard/panels/anomaly.py       unchanged  (pre-existing uncommitted work)
tools/dashboard/panels/storm.py         unchanged  (pre-existing uncommitted work)
tools/dashboard/panels/weather.py       unchanged  (pre-existing uncommitted work)
tools/dashboard/noaa.py                 unchanged  (pre-existing uncommitted work)
tools/dashboard/READ_ME.md              modified   DSLV_DASHBOARD_COMPACT documented
tools/launch_project.sh                 modified   screen-aware geometry + compact dispatch
tools/mapping/__init__.py               new
tools/mapping/aggregate.py              new        HDF5 + JSONL event aggregator
tools/mapping/render_map.py             new        Folium satellite map renderer
tools/mapping/open_map.sh               new        desktop-icon launcher
tools/mapping/open_hdf5_browser.sh      new        h5ls/h5dump picker
tools/mailer/__init__.py                new
tools/mailer/backends.py                new        pluggable SMTP send
tools/mailer/send_data.py               new        bundle + send CLI
tools/mailer/configure.py               new        tkinter GUI
tools/mailer/send_now.sh                new        desktop-icon launcher
config/sensor_location.example.yaml     new
config/email.example.yaml               new
~/Desktop/DSLV-ZPDI-Map.desktop         new
~/Desktop/DSLV-ZPDI-Send-Data.desktop   new
~/Desktop/DSLV-ZPDI-Email-Setup.desktop new
~/Desktop/DSLV-ZPDI-HDF5.desktop        new
~/.config/dslv-zpdi/sensor_location.yaml staged from example
apt:   hdf5-tools, python3-tk            installed
pip:   h5glance, folium, pandas, tables  installed (ViTables removed — see §2.2)
```

## 4. Verification

| Item | Result |
|---|---|
| `dashboard` package imports | PASS |
| `build_layout(compact=True)` structure | PASS — 2×2 status grid confirmed |
| `tools/mapping/aggregate.py` | PASS — 4000 events emitted (2000 primary / 2000 secondary) |
| `tools/mapping/render_map.py` | PASS — 2.6 MB HTML; ESRI + OSM + clusters present |
| `tools/mailer/send_data.py --dry-run` | PASS — bundle 0.34 MB, subject / recipients formatted |
| `numpy` / `pyhackrf` compatibility | PASS — numpy 1.26.4, `import hackrf` OK |
| `dslv_zpdi` package | PASS — imports after the numpy rollback |

## 5. Turnover

### 5.1 One-time setup for the user

1. **Sensor anchor** — edit `~/.config/dslv-zpdi/sensor_location.yaml`
   with your real lat/lon/heading. The example coords point at
   Denver; replace before using the map for anything real.
2. **Email** — double-click "DSLV-ZPDI Email Setup" on the desktop.
   Paste a Google App Password (generate at
   https://myaccount.google.com/apppasswords — requires 2FA on the
   Google account). Add recipients, click Save.

### 5.2 Day-to-day usage

- **Dashboard**: `DSLV-ZPDI.desktop` — unchanged. Now auto-detects the
  DSI screen and switches to compact mode. Press `c` to toggle.
- **Map**: `DSLV-ZPDI-Map.desktop` — regenerates and opens in Chromium.
- **Send data**: `DSLV-ZPDI-Send-Data.desktop` — bundles + sends.
  Opens a terminal so you see the send log.
- **HDF5 browser**: `DSLV-ZPDI-HDF5.desktop` — menu-driven inspector.

### 5.3 Known limitations

- **No per-event GPS in HDF5.** Map pins are scattered around the
  sensor anchor by a deterministic pseudo-random function — visually
  informative but geographically synthetic. Adding real per-event
  GPS requires (a) a `gpsd` feed on capture, (b) extending the
  layer3 HDF5 writer to stamp lat/lon into each event group, and
  (c) updating `aggregate.py` to prefer real coords when present.
- **Gmail attachment cap is 25 MB.** `max_attachment_mb` defaults
  to 20 MB. Primary HDF5 captures under `output/primary/` can be
  200+ MB — the largest files are skipped with a reason recorded in
  the bundle manifest. A future "chunked send" backend or a small
  S3/Drive upload shim would handle the big ones.
- **ViTables disabled.** See §2.2. Use `h5glance` / `h5ls -r` /
  `h5dump` instead. Once `pyhackrf` upgrades past numpy 2, reinstall
  with `pip install vitables`.
- **Compact dashboard is terminal-based.** At 800×480 with a 9-pt
  monospace font, we fit ≈ 92×24 cells — enough for the stacked
  layout but the waterfall gets tight. If you want more RF detail
  on the DSI, toggle compact off (`c`) and scroll the terminal.

### 5.4 Follow-ups / nice-to-haves

- Wire `tools/mailer/send_now.sh` into cron / systemd timer for
  scheduled daily bundles. Timer unit is a 10-line file.
- Add `tools/mapping/aggregate.py` support for a sidecar
  `<h5>.geo.json` so captures with per-event GPS (future) get
  plotted at real coordinates.
- Add an SES backend in `tools/mailer/backends.py` — the dispatch
  table is already set up for it.
- The waterfall panel already publishes `last_dbm_row` to the
  anomaly panel. A compact mode variant of the waterfall that
  renders only the spectrum line (no history) would let us run
  compact mode on a 480-line screen without losing signal density.

---

**DSLV-ZPDI :: DynoGatorLabs :: Tier 1 Anchor**
*If it moves, it gets coherence-scored — and now it gets pinned,
bundled, and mailed, too.*
