# SPEC-004A.8 — Geekworm X-1202 UPS HAT (Tier-1 Pi 5 Power Telemetry)

## 1. Purpose

This specification adds power-source telemetry and graceful-shutdown control for the Geekworm X-1202 UPS HAT on a Raspberry Pi 5 Tier-1 anchor node.

The UPS is treated as a Tier-1 health sensor: it reports battery voltage, state-of-charge, charge/discharge rate, and AC-line presence, and it is authorized to request a controlled halt when the battery is critically low or when AC power has been absent for longer than the configured hold-up time.

## 2. Hardware Interface

### 2.1 I2C fuel gauge

| Parameter | Value |
|-----------|-------|
| Gas-gauge IC | Maxim MAX17048/MAX17049 (ModelGauge) or pin-compatible variant |
| I2C bus | `1` (`/dev/i2c-1`) |
| I2C address | `0x36` |
| SDA pin | GPIO2 (header pin 3) |
| SCL pin | GPIO3 (header pin 5) |

Key registers:

| Register | Address | Resolution | Purpose |
|----------|---------|------------|---------|
| VCELL | `0x02` | `78.125 µV`/LSB | Battery cell voltage |
| SOC | `0x04` | `1/256 %`/LSB | State-of-charge (0–100%) |
| CRATE | `0x16` | `0.208 %`/h per LSB | Charge/discharge rate |
| VER | `0x08` | — | IC production version |

The X-1202 connects to the Pi 5 through pogo pins on the bottom of the Pi; no 40-pin header wiring is required. `i2c-dev` must be loaded and the running user must be in the `i2c` group.

### 2.2 GPIO status/control

| BCM GPIO | Header pin | Direction | Function |
|----------|------------|-----------|----------|
| GPIO6 | 31 | Input | AC power presence: **low** = AC lost / power adapter failed, **high** = AC OK |
| GPIO16 | 36 | Output | Battery charging control: **high** = charging disabled, **low** = charging enabled |

On a Raspberry Pi 5 the `pinctrl-rp1` GPIO controller has base offset `569`, so the sysfs numbers are `575` (GPIO6) and `585` (GPIO16). The implementation allows these to be overridden for other boards.

## 3. Software Interface

### 3.1 Library module

`src/dslv_zpdi/layer1_ingestion/x1202_ups.py` provides:

* `X1202UpsMonitor` — I2C + GPIO context manager.
* `UpsSample` — normalized telemetry dataclass.
* `ups_telemetry()` — one-shot health sample returning a JSON-serializable dict.

The module fails closed on I2C/GPIO errors: if the UPS is disconnected, `sample()` returns `health="absent"`, `error=<reason>`, and never initiates a shutdown.

### 3.2 Monitor daemon

`tools/x1202_ups_monitor.py` polls the UPS and triggers a graceful shutdown when either:

* Battery SOC falls at or below `DSLV_X1202_BATTERY_SHUTDOWN_PERCENT` (default `15`).
* Battery voltage falls at or below `DSLV_X1202_BATTERY_SHUTDOWN_VOLTAGE` (default `3.40 V`).
* AC has been continuously lost for `DSLV_X1202_AC_LOST_SHUTDOWN_SECONDS` (default `300`).

The first trigger calls `shutdown -h +1` exactly once and writes a marker file to `/var/lib/dslv_zpdi/x1202_shutdown_requested`. The operator can cancel with `shutdown -c` if power returns.

### 3.3 Systemd service

`config/dslv-zpdi-ups.service` runs the monitor as an unprivileged service. It requires:

* Membership in `i2c` and `gpio` groups.
* `i2c-dev` and GPIO sysfs access.

## 4. Trust and Safety

* The monitor must **not** shut down the node while the UPS is unreadable (disconnected, driver missing, permission denied).
* Low-battery shutdown is disabled in one-shot / telemetry-only mode.
* Charging control is exposed but defaults to "do not change"; the operator must explicitly enable charge management.
* All telemetry fields include a `health` enum: `healthy`, `degraded`, `critical`, `absent`.

## 5. References

* `src/dslv_zpdi/layer1_ingestion/x1202_ups.py`
* `tools/x1202_ups_monitor.py`
* `config/dslv-zpdi-ups.service`
* `docs/hardware/GEEKWORM_X1202_UPS.md`
* Maxim MAX17048/MAX17049 datasheet
