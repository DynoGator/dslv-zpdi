# DSLV-ZPDI Operations Dashboard

The customizable, real-time TUI for the DSLV-ZPDI anchor node. Runs in
any ANSI terminal (≥ ~120 cols recommended) and shows system health,
the systemd pipeline, HackRF/PPS/GPSDO hardware, a live journald tail,
a dark-humor notification ticker, and a rolling SDR spectrograph
waterfall that can be driven from a live `hackrf_sweep` stream.

## Launching

| Command | What it does |
|---|---|
| `bash tools/launch_project.sh` | Full "nuke and pave" — kills stale SDR processes, restarts the systemd chain, opens the dashboard. |
| `bash tools/dashboard/launch.sh` | Just the dashboard, nothing else. |
| `venv/bin/python -m dashboard --help` | Show CLI flags. |

Useful flags:

```
--refresh 0.25        faster refresh (default 0.5s)
--no-banner           hide the top banner
--no-boot             skip the boot animation
--real-sdr            start with real-SDR mode already on
--config <path>       use a custom dashboard.toml
--print-config        dump the resolved config and exit
```

## Keybindings

All keys are remappable in `~/.config/dslv-zpdi/dashboard.toml` under
`[dashboard.keybindings]`.

### Core
| Key | Action |
|---|---|
| `q` | quit |
| `space` | pause / resume rendering (pipeline keeps running) |
| `h` | toggle the big banner |
| `m` | cycle waterfall mode: `SWEEP` → `NARROW` → `SCOPE` |
| `r` | toggle REAL SDR mode (flips `DSLV_DASHBOARD_REAL_SDR`) |

### Waterfall (live SDR)
| Key | Action |
|---|---|
| `←` / `→` | tune center frequency by ±10% of span |
| `↑` / `↓` | zoom span in (×0.5) / out (×2) |
| `g` | cycle LNA gain (0, 8, 16, 24, 32, 40 dB) |
| `a` | toggle RF front-end amp (`hackrf_sweep -a 1`) |

Tune/zoom/gain/amp each restart the underlying `hackrf_sweep` so they
take effect within one sweep (~50–200 ms).

## The waterfall panel

* **SIM mode** — default. A synthesized FFT with drifting carriers and
  pulse injection. Useful for demos and when no HackRF is plugged in.
* **HACKRF mode** — spawns `hackrf_sweep` in a background thread,
  accumulates each sweep, resamples it to the terminal width, and
  publishes a new row on every completed sweep. The title strip shows:

  ```
  ▓ WATERFALL ▓ (SWEEP · HACKRF · 20.0 MHz span · lna 24dB vga 20dB amp off · sweeps 34)
  ```

  While the subprocess is warming up, the label reads `HACKRF…` and the
  simulator is rendered so the waterfall never goes blank. If
  `hackrf_sweep` prints anything to stderr before exiting, the last line
  is appended to the title so you can see what went wrong.

`r` flips between sources at any time.

## Customizing — `dashboard.toml`

Copy `config/dashboard.toml.example` to `~/.config/dslv-zpdi/dashboard.toml`
and edit what you need. Anything you omit falls back to the built-in default.

```toml
[dashboard]
refresh       = 0.5
show_banner   = true
service_unit  = "dslv-zpdi"

[dashboard.panels]
system        = true
pipeline      = true
hardware      = true
waterfall     = true
logs          = true
notifications = true

[dashboard.theme]
system_border        = "bright_cyan"
pipeline_border      = "bright_green"
hardware_border      = "yellow"
waterfall_border     = "bright_magenta"
logs_border          = "bright_white"
notifications_border = "bright_magenta"
banner_border        = "bright_green"
footer_border        = "bright_black"

[dashboard.waterfall]
mode       = "SWEEP"        # SWEEP | NARROW | SCOPE
center_hz  = 100_000_000    # starting center frequency
span_hz    = 20_000_000     # starting span
history    = 12             # visible history rows

[dashboard.notifications]
humor_every_s  = 4.0
glitch_every_s = 37.0
max_items      = 8

[dashboard.logs]
max_lines = 14

[dashboard.keybindings]
quit      = "q"
pause     = " "
wf_mode   = "m"
real_sdr  = "r"
help      = "h"
```

Turning a panel off collapses its row — set `hardware = false` and the
top strip becomes two columns instead of three with no blank gap.

## Environment variables

| Var | Effect |
|---|---|
| `DSLV_DASHBOARD_CONFIG` | Path to an alternate TOML config. |
| `DSLV_DASHBOARD_REAL_SDR` | `1` = use real `hackrf_sweep`, `0` (or unset) = simulator. The `r` key toggles this. |

## Requirements

* Python 3.11+ (for `tomllib`)
* `rich`, `pyfiglet` (installed by `bootstrap.sh` into the venv)
* `hackrf-tools` (`apt install hackrf`) for real-SDR mode
* User in the `plugdev` group for HackRF without sudo
* `/lib/udev/rules.d/60-libhackrf0.rules` installed by `libhackrf0`

`tools/launch_project.sh` checks all of these on boot and prints warnings.

## Troubleshooting

* **Banner looks cut off** — your terminal is under ~100 cols. Resize it;
  the banner is tuned to fit comfortably at ≥100 cols and the layout
  reserves `BANNER_HEIGHT` (11 rows) for it.
* **"HACKRF…" never turns into "HACKRF"** — another process owns the
  device. `tools/launch_project.sh` kills gqrx / sdrangel / rtl_* /
  hackrf_transfer before starting; re-run it. Or look at the error
  shown in the waterfall title bar.
* **Log panel says "waiting for journald…"** — the systemd unit named in
  `service_unit` has never logged. Either the unit name is wrong for
  your install or the service hasn't started; check `systemctl status
  dslv-zpdi`.
* **Arrow keys print `^[[A`** — your terminal isn't passing escape
  sequences (rare with modern lxterminal / xterm). Try the letter
  fallbacks in the keybindings section of the config file, or run the
  dashboard inside a different terminal.

## Files

```
tools/dashboard/
├── app.py            Live app + keyboard/layout wiring
├── banner.py         Top banner + boot animation
├── config.py         TOML loader, dataclasses, defaults
├── humor.py          Scan/glitch quip corpus
├── launch.sh         venv/python -m dashboard wrapper
├── __main__.py       `python -m dashboard` entry point
├── READ_ME.md        This file
└── panels/
    ├── hardware.py        HackRF, PPS, GPSDO, chrony
    ├── logs.py            journalctl -fu <unit> tail
    ├── notifications.py   notification queue + humor ticker
    ├── pipeline.py        systemd state, PID, uptime, packet rate
    ├── system.py          CPU, mem, load, temp, throttling
    └── waterfall.py       SIM + HackRF streaming waterfall
```
