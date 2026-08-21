# DSLV-ZPDI Tier-1 Node — Reboot Preparation Report

**Date:** 2026-07-09  
**Node:** `raspberrypi` (Raspberry Pi 5 16 GB)  
**Operator:** Kimi Code CLI / dynogator  
**Goal:** Prepare the local node for a clean reboot, ensure all hardware data is real and all startup paths are persistent, then issue the reboot.

## 1. Hardware Data Verification

All telemetry flowing through the pipeline and dashboard is sourced from real hardware:

| Subsystem | Source | Status |
|-----------|--------|--------|
| Clock discipline | LBE-1421 GPSDO 1 PPS → GPIO 8 → `/dev/pps0` → `chronyd` | **Stratum 1**, PPS1 selected, RMS offset ~786 ns |
| RF ingestion | PlutoSDR+ (AD9363 REV5) via Ethernet `ip:192.168.2.1` | **REAL**, `clock_src: external`, 0 transport errors |
| GPS NMEA | LBE-1421 USB-C → `/dev/ttyACM0` → `gpsd` → TCP 2947 | Active, consumed by pipeline |
| UPS / power | Geekworm X-1202 HAT, MAX17048 on I2C-1 0x36 | **Healthy**, 97.8% battery, AC present |

Web dashboard `/api/status` reflects the live state above. The Rich TUI dashboard’s system, pipeline, hardware, and UPS panels also read from `/run/dslv-zpdi/health.json`, which is written by the live pipeline.

## 2. Pipeline Output Verification

- Baseline state: **LOCKED**
- Event threshold: 0.30 (dev override for single-node validation)
- PRIMARY HDF5 events written and growing
- Secondary stream logging structured background / below-threshold records
- HMAC-SHA256 manifest and SHA-256 event-chain hashes active

## 3. Boot Persistence Checklist

| Item | State |
|------|-------|
| `dslv-zpdi-tuning.service` | enabled, active |
| `dslv-zpdi-preflight.service` | enabled, active |
| `dslv-zpdi.service` | enabled, active |
| `dslv-zpdi-ups.service` | enabled, active |
| `dslv-zpdi-webdash.service` | enabled, active |
| `chrony.service` | enabled, active |
| `gpsd.service` | **enabled** during this prep pass |
| Autostart desktop entry `~/.config/autostart/dslv-zpdi-dashboard.desktop` | present, launches boot orchestrator |
| Autologin for `dynogator` | configured in `/etc/lightdm/lightdm.conf` and getty |
| `dynogator` sudo access | NOPASSWD ALL, boot orchestrator can start services |
| `.env` baseline / mono-node settings | persisted, mode 0600 |
| `.secrets/` credentials | persisted, mode 0600, gitignored |

## 4. Startup Blockers Addressed

- **gpsd** was disabled; now enabled so the NMEA feed starts automatically.
- **Service file drift** eliminated: installed systemd units now match the repo files exactly (`diff` clean for all services).
- **No duplicate autostart entries**; only `dslv-zpdi-dashboard.desktop` is present.
- **No conflicting NTP daemon** (`systemd-timesyncd` is inactive/not enabled).
- **Main pipeline service** runs with `--simulator`; profile `allow_simulator_fallback: false` ensures it fails closed on missing hardware rather than silently simulating.
- **Boot orchestrator** runs as `dynogator`, verifies the service chain, and `exec`s the Rich TUI dashboard on success.

## 5. Known Limitations at Reboot

- The **waterfall panel** in the Rich TUI dashboard uses `hackrf_sweep` for real-time spectrum data. No HackRF (legacy/optional) is connected to this node (only PlutoSDR+), so the waterfall defaults to SIM mode and is the only simulated dashboard element. All other dashboard telemetry is real.
- The 1024×600 touchscreen layout has been configured but not visually verified in this session.
- The node is intentionally in **mono-node dev mode**; the 4-node confirmation gate is bypassed.

## 6. Reboot Command Issued

```bash
sudo reboot
```

After reboot, the expected sequence is:

1. System boots; systemd starts `chrony`, `gpsd`, `dslv-zpdi-tuning`, `dslv-zpdi-preflight`, `dslv-zpdi`, `dslv-zpdi-ups`, `dslv-zpdi-webdash`.
2. LightDM autologins `dynogator` into labwc.
3. `~/.config/autostart/dslv-zpdi-dashboard.desktop` launches `tools/boot_orchestrator.py` in a 120×40 `lxterminal`.
4. The boot orchestrator verifies all services, prints retro ASCII status, and starts the Rich TUI dashboard.
5. The pipeline re-locks the baseline from persisted `/var/lib/dslv-zpdi/baseline.json` and resumes PRIMARY HDF5 output.

## 7. Post-Reboot Spot-Check (for operators)

```bash
# Verify service chain
systemctl is-active dslv-zpdi-tuning dslv-zpdi-preflight dslv-zpdi \
               dslv-zpdi-ups dslv-zpdi-webdash chrony gpsd

# Verify real data
curl -s http://127.0.0.1:8080/api/status | python3 -m json.tool
ls -lh /home/dynogator/dslv-zpdi/output/primary/
```

## 8. References

- `docs/node_ops/WORK_LOG.md` — full commissioning and optimization log.
- `docs/node_ops/TURNOVER_NOTES.md` — collaborator hand-off.
- `docs/node_ops/TOOLCHAIN_AUDIT.md` — component evaluation.
- `specs/SPEC-009.md` — baseline learning FSM specification.
