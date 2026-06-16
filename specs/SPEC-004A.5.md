# SPEC-004A.5 — PlutoSDR+ (ADALM-PLUTO clone) SDR Source

## 1. Purpose

This specification defines first-class support for the Analog Devices ADALM-PLUTO / PlutoSDR+ software-defined radio as a Tier 1/2 RF ingestion source for the DSLV-ZPDI pipeline and operations dashboard.

The PlutoSDR+ may operate as:

* **Tier 1 source** only when a GPSDO 10 MHz reference is wired to the `CLKIN` pin and a 1 PPS signal is wired to the relevant GPIO/PPS input and the configuration explicitly sets `pluto_external_clock: true`.
* **Tier 2 / secondary-quarantined source** in all other configurations. The code cannot verify external clock wiring in software, so `pluto_external_clock: false` keeps `clock_source="internal"` and the ingestion payload is routed to the secondary stream.

## 2. Hardware Interface

* **Primary driver:** `libiio` (Python binding `iio`) — direct access to the AD9363 PHY and RX LO / data buffer.
* **Fallback driver:** `SoapyPlutoSDR` via SoapySDR (available but not used in the primary HAL because attribute control is less direct).
* **Default URI:** `ip:192.168.3.80` (Gigabit Ethernet / Tezuka-Libre firmware).
* **Alternative URIs:** `ip:pluto.local`, `usb:<bus>.<device>`.
* **RX manual gain range:** -10 to +62 dB for the on-board AD9361 class transceiver (AD9363 variants report a similar effective range).

### 2.1 Required host setup

* `dfu-util`, `openocd`, and `libiio`/`libiio-dev` must be installed.
* `SoapyPlutoSDR` must be built/installed from source if the packaged version is unavailable.
* udev rules granting `plugdev`/`dialout` access to the Pluto USB IDs (`0456:b673`, `0456:b674`).
* A NetworkManager profile, netplan stanza, or manual network setup so the host has an address on `192.168.3.0/24` and the Pluto is reachable at `192.168.3.80`.

## 3. HAL Implementation

`src/dslv_zpdi/layer1_ingestion/hal_pluto.py` provides `PlutoHAL(BaseHAL)`.

### 3.1 Constructor

```python
PlutoHAL(
    uri: str = "ip:192.168.3.80",
    pps_device: str = "/dev/pps0",
    nmea_port: str = "/dev/ttyACM0",
    external_clock: bool = False,
    gain: int = 62,
)
```

* `external_clock` must only be set to `True` when the GPSDO 10 MHz reference is physically wired to `EXT_REF_CLK` and 1 PPS is wired.
* `gain` maps to the AD9361 `hardwaregain` attribute in manual mode. The safe verified upper bound is +62 dB.

### 3.2 Ingestion methods

* `ingest_gps_pps()` — reuses the shared `PpsListener` / `NmeaStream` logic for timing verification.
* `ingest_sdr()` — opens an `iio.Context`, configures `ad9361-phy` RX_LO and `cf-ad9361-lpc` buffer, captures `num_samples`, and returns an `IngestionPayload`.
* `verify_tier1_phase_lock()` / `verify_gpsdo_lock()` — verify that a PPS device and GPSDO NMEA fix are available; they do **not** verify the actual AD9363 PLL lock to the external reference (this is wiring-dependent).

### 3.3 Trust model

| `external_clock` | Payload `clock_source` | `IngestionPayload.validate()` result |
|------------------|------------------------|--------------------------------------|
| `false`          | `"internal"`           | Secondary quarantine                 |
| `true`           | `"external"`           | Primary eligible (subject to PPS/GPSDO health) |

## 4. Factory and Configuration

### 4.1 HAL factory

`src/dslv_zpdi/layer1_ingestion/hal_factory.py` extended:

```python
def get_hal(
    tier: int = 1,
    simulator: bool = False,
    sdr_type: str = "auto",
    pluto_uri: str | None = None,
    pluto_external_clock: bool = False,
    pluto_gain: int = 64,
) -> HardwareHAL | PlutoHAL | SimulatedHAL
```

* `sdr_type="auto"` detection order: HackRF → Pluto → simulator fallback.
* `sdr_type="pluto"` forces `PlutoHAL`.
* `sdr_type="hackrf"` forces `HardwareHAL`.
* `sdr_type="sim"` forces `SimulatedHAL`.

### 4.2 Config loader

`src/dslv_zpdi/config_loader.py` accepts:

```yaml
pipeline:
  sdr_type: "auto"          # auto | hackrf | pluto | sim
  pluto_uri: "ip:192.168.3.80"
  pluto_external_clock: false
  pluto_gain: 62
```

Environment overrides:

* `DSLV_SDR_TYPE`
* `DSLV_PLUTO_URI`
* `DSLV_PLUTO_EXTERNAL_CLOCK` (`1`/`true`/`yes`)
* `DSLV_PLUTO_GAIN`

### 4.3 Main pipeline

`src/dslv_zpdi/main_pipeline.py` adds `--sdr-type {hackrf,pluto,sim}` and passes the resolved selection to `get_hal()`.

## 5. Dashboard Integration

`tools/dashboard/panels/waterfall.py` supports three live sources:

* `SIM` — synthesized spectrum (default fallback)
* `HACKRF` — `hackrf_sweep` subprocess
* `PLUTO` — `PlutoSweepStream` libiio FFT thread

Source selection:

* Config key: `waterfall.sdr_source` (`hackrf`, `pluto`, `sim`).
* Env var: `DSLV_DASHBOARD_SDR_SOURCE`.
* CLI flag: `--sdr-source {hackrf,pluto,sim}`.
* Runtime key: `r` cycles through detected sources: HackRF → PlutoSDR → SIM.

The waterfall title and the RF anomaly panel indicate the active source (`HACKRF`, `PLUTO`, `SIM`, or `…-WAIT` while the stream starts). The hardware panel displays both HackRF and PlutoSDR detection status.

## 6. Python Environment

`libiio` and `SoapySDR` are system/apt packages, not available from PyPI. Because the project venv is isolated, add a `.pth` file so the interpreter can find the system bindings:

```bash
echo '/usr/lib/python3/dist-packages' > \
  .venv/lib/python3.13/site-packages/system-dist-packages.pth
```

This makes `iio` and `SoapySDR` importable from inside the venv without recreating it with `--system-site-packages`.

## 7. Tests

`tests/test_pluto_hal.py` covers:

* Initialization with missing driver.
* Missing devices on the libiio context.
* External-clock mode without PPS/GPSDO raises a clock-verification error.
* Internal-clock payloads are quarantined to the secondary stream.
* GPSDO lock verification with a mocked context.

Tests use the same module-dict patching pattern used for `SoapySDR`, `pyhackrf`, and `serial` mocks elsewhere in the suite.

## 8. Safety Notes

* Do **not** set `pluto_external_clock: true` unless the GPSDO 10 MHz and 1 PPS wiring is physically verified.
* The AD9363 front-end is not designed for strong nearby transmitters; use appropriate filtering/attenuation.
* Do **not** enable the HackRF front-end amp (`a` key in the dashboard) until the blown amplifier is replaced.
