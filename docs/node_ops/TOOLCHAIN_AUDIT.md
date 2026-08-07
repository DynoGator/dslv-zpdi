# DSLV-ZPDI Tier-1 Toolchain Audit

**Date:** 2026-07-09  
**Node:** `raspberrypi` (Raspberry Pi 5 16 GB)  
**Profile:** `config/node_profiles/tier1_pluto_lbe1421.yaml`

## 1. Pipeline Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│  LBE-1421 GPSDO ──┬── 1 PPS ──▶ GPIO 18 ──▶ /dev/pps0 ──▶ chrony (Stratum 1) │
│                   │                                                         │
│                   └── 10 MHz ──▶ PlutoSDR+ EXT_REF_CLK (physical, unverified)│
│                                                                             │
│  LBE-1421 USB-C ──▶ /dev/ttyACM0 ──▶ gpsd ──▶ NMEA GGA ──▶ pipeline         │
│                                                                             │
│  PlutoSDR+ Ethernet ──▶ libiio @ ip:192.168.2.1 ──▶ PlutoIioBackend        │
│                                                                             │
│  X-1202 UPS ──▶ I2C:1/0x36 + GPIO6/16 ──▶ x1202_ups.py                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  LBE1421TimingAuthority       │
                    │  - PpsListener (sysfs assert) │
                    │  - NmeaStream (gpsd TCP)      │
                    │  - ChronyMonitor              │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  HardwareHAL                   │
                    │  - ingest_sdr() / ingest_pps() │
                    │  - Tier1QualificationPolicy    │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  CoherenceScorer               │
                    │  - Kuramoto order parameter    │
                    │  - 72-hour baseline learning   │
                    └───────────────────────┬───────┘
                                            │
                    ┌───────────────────────▼───────┐
                    │  DualStreamRouter              │
                    │  - PRIMARY / SECONDARY         │
                    └───────────────────────┬───────┘
                                            │
                    ┌───────────────────────▼───────┐
                    │  HDF5Writer                    │
                    │  - SHA-256 event-chain hashes  │
                    │  - HMAC-SHA256 manifest        │
                    └───────────────────────────────┘
```

## 2. Component-by-Component Evaluation

### 2.1 Timing Discipline

**Current stack:** `gpsd` + `chronyd` + kernel `pps-gpio` + custom `PpsListener`.

| Role | Current Tool | Assessment | Alternatives | Recommendation |
|------|--------------|------------|--------------|----------------|
| NMEA reader | `gpsd` daemon + `NmeaStream` TCP | Stable; handles port ownership cleanly | Direct pyserial (contended), `gpsmon` | Keep `gpsd`; it is the de-facto standard |
| PPS timestamp | Kernel `pps-gpio` + sysfs assert | Works on Pi 5; ioctl path unreliable | `ptp4l` (requires hardware PTP), custom kernel module | Keep sysfs path |
| Clock discipline | `chronyd` | Stratum 1, fast convergence, PPS priority | `ntpd` (slower), `phc2sys` (NIC PTP) | Keep `chronyd` |
| Jitter monitoring | `chronyc tracking` RMS offset | Stable metric once locked | Direct PPS interrupt variance | Keep RMS; add PPS jitter from `PpsListener` to health |

**Optimization applied:** `PpsListener` switched from `PPS_FETCH` ioctl to `/sys/class/pps/pps0/assert`. `TimingMonitor` now uses `RMS offset` from chronyc for a stable jitter figure.

### 2.2 SDR Ingestion

**Current stack:** `libiio` Python bindings → `PlutoIioBackend`.

| Role | Current Tool | Assessment | Alternatives | Recommendation |
|------|--------------|------------|--------------|----------------|
| Pluto control | `libiio` | Native, low overhead, context kept open | SoapySDR/SoapyPlutoSDR (more abstraction, slower setup), `pyadi-iio` (higher-level) | Keep `libiio`; add SoapySDR only if multi-backend needed |
| Sample transport | `iio.Buffer` over Ethernet | 10 MSPS sustained, no drops observed | USB (more CPU on Pi), DMA (requires custom FPGA) | Keep Ethernet |
| Clock verification | None (UNVERIFIED_PHYSICAL_PROPERTY) | Stock Pluto firmware cannot report external ref lock | Custom Pluto firmware exposing `xo_correction` or `clk_lock` attribute, spectrum analyzer | Document as physical verification |

### 2.3 Persistence / Trust

**Current stack:** `HDF5Writer` + `h5py` + HMAC-SHA256.

| Role | Current Tool | Assessment | Alternatives | Recommendation |
|------|--------------|------------|--------------|----------------|
| Structured storage | `h5py` / HDF5 | Proven, chunkable, good metadata | Zarr, Parquet, SQLite | Keep HDF5; matches SPEC-007 |
| Tamper evidence | SHA-256 chain + HMAC-SHA256 manifest | Strong, verifiable offline | GPG detached signatures, TPM-backed keys | Keep current; consider TPM for key storage |
| Key storage | Plain file `/etc/dslv-zpdi/hmac.key` | Practical but not hardware-protected | systemd-creds, TPM2 sealed blob, HashiCorp Vault | Evaluate TPM2 on Pi 5 in future |
| Routing | `DualStreamRouter` | Clean PRIMARY/SECONDARY semantics | Apache Kafka, Redis Streams | Keep in-process for latency |

### 2.4 UPS / Power

**Current stack:** Custom `smbus2` reader + sysfs GPIO.

| Role | Current Tool | Assessment | Alternatives | Recommendation |
|------|--------------|------------|--------------|----------------|
| Fuel gauge | `smbus2` direct MAX17048 | Fast, no extra dependencies | `upower` (abstracts poorly for this HAT), `python-periphery` | Keep custom module |
| AC/charge GPIO | sysfs GPIO | Reliable on Pi 5 | `libgpiod` (cleaner but requires binding) | Keep sysfs; migrate to `gpiod` if sysfs deprecated |
| Shutdown policy | `tools/x1202_ups_monitor.py` | Conservative, fail-safe | `upsd` / NUT (overkill for single HAT) | Keep custom monitor |

### 2.5 Dashboard / Visualization

**Current stack:** Flask web dashboard (`tools/dashboard/web_server.py`) + Rich TUI (`tools/dashboard/app.py`).

| Role | Current Tool | Assessment | Alternatives | Recommendation |
|------|--------------|------------|--------------|----------------|
| Web dashboard | Flask + vanilla JS | Lightweight, no build step, fast on LAN | Grafana + Prometheus (heavier but richer), FastAPI | Keep Flask for now; consider Grafana for multi-node ops center |
| TUI dashboard | Rich (`dashboard/app.py`) | Beautiful on HDMI touchscreen, low CPU | `blessed`, `urwid` | Keep Rich |
| Health endpoint | `/run/dslv-zpdi/health.json` | Fast, decouples dashboard from pipeline | HTTP health endpoint inside pipeline | Keep JSON file; faster than subprocess probes |

**Optimization applied:** `main_pipeline.py` now publishes `sdr_health`, `pps`, and `ups` into `health.json`. Web dashboard and TUI hardware panel consume this directly instead of re-probing hardware every cycle.

### 2.6 Process Supervision

**Current stack:** systemd services.

| Role | Current Tool | Assessment | Alternatives | Recommendation |
|------|--------------|------------|--------------|----------------|
| Service manager | systemd | Mature, dependency ordering, sandboxing | supervisord, pm2 | Keep systemd |
| Restart policy | `Restart=on-failure` | Safe, avoids restart loops | `Restart=always` | Keep on-failure; added `StartLimitIntervalSec` / `StartLimitBurst` |
| Sandboxing | `ProtectSystem=strict`, etc. | Containment without breaking I/O | Manual chroot, containers | Applied to pipeline service |
| Resource limits | `MemoryMax=2G`, `CPUAffinity=2 3` | Protects system, pins pipeline | cgroups v2 manual tuning | Applied |

## 3. Bottlenecks and Mitigations

| Bottleneck | Impact | Mitigation |
|------------|--------|------------|
| 72-hour baseline learning | No PRIMARY output until locked | Expected by SPEC-009; baseline state persists across restarts |
| 4-node confirmation gate | Single-anchor node cannot produce confirmed events | Tier-2 mobile nodes (Pixel) must join the swarm |
| `libiio` capture latency | ~tens of ms per buffer | Buffer size tuned in profile; pipeline is PPS-aligned so one capture/s is acceptable |
| Health JSON I2C read every 10 payloads | Brief I2C bus contention | Tuned to every ~10 s; acceptable for monitoring |
| Realtime IO scheduling | Could starve GUI/dashboard | CPU affinity pins pipeline to cores 2+3; Wayland/compositor runs on others |

## 4. Suggested Future Tools

- **TPM2 / OP-TEE on Pi 5** for sealed HMAC key storage.
- **Grafana + Prometheus Node Exporter** for long-term trend dashboards off-node.
- **`phc2sys`** or custom kernel PTP if a hardware PTP-capable NIC is added.
- **SoapySDR** if HackRF (legacy/optional) / RTL-SDR / other backends need to be supported alongside Pluto.
- **`nftables`** rules in `config/os-hardening/nftables-dslv-zpdi.rules` should be reviewed and enabled for field deployment.

## 5. Operational Verification Commands

```bash
# Timing discipline
chronyc tracking
cat /run/dslv-zpdi/health.json | python3 -m json.tool

# Service chain
systemctl status dslv-zpdi-tuning dslv-zpdi-preflight dslv-zpdi \
               dslv-zpdi-ups dslv-zpdi-webdash

# SDR reachability
.venv/bin/python -c "import iio; print(iio.Context('ip:192.168.2.1').attrs.get('hw_model'))"

# UPS
.venv/bin/python -c "from dslv_zpdi.layer1_ingestion.x1202_ups import ups_telemetry; import json; print(json.dumps(ups_telemetry(), indent=2))"

# Dashboards
# Web:  http://<pi-ip>:8080/
# TUI:  tools/dashboard/launch.sh --compact
# Boot: tools/boot_orchestrator.py
```
