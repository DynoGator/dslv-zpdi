# Geekworm X-1202 UPS HAT — Tier-1 Pi 5 Integration

## Hardware

- **HAT:** Geekworm X-1202 (Raspberry Pi 5 UPS with 4× 18650 battery holder)
- **Fuel gauge:** Maxim MAX17048 / MAX17049 (ModelGauge)
- **I2C bus:** `/dev/i2c-1`, address `0x36`
- **Status GPIO:**
  - GPIO6 (header pin 31) — AC power presence input (high = AC OK)
  - GPIO16 (header pin 36) — battery charging control output (low = charge enabled)

The HAT attaches via pogo pins; no 40-pin wiring is required.

## Software

- Library: `src/dslv_zpdi/layer1_ingestion/x1202_ups.py`
- Monitor daemon: `tools/x1202_ups_monitor.py`
- Systemd service: `config/dslv-zpdi-ups.service`

## Runtime

```bash
# One-shot telemetry sample
/home/dynogator/dslv-zpdi/.venv/bin/python -c \
  "from dslv_zpdi.layer1_ingestion.x1202_ups import ups_telemetry; print(ups_telemetry())"

# Service control
sudo systemctl start dslv-zpdi-ups
sudo systemctl status dslv-zpdi-ups
```

## Configuration

Environment variables (set in `/home/dynogator/dslv-zpdi/.env`):

| Variable | Default | Meaning |
|----------|---------|---------|
| `DSLV_X1202_POLL_SECONDS` | 10 | Polling interval |
| `DSLV_X1202_BATTERY_SHUTDOWN_PERCENT` | 15 | Emergency shutdown SOC |
| `DSLV_X1202_BATTERY_SHUTDOWN_VOLTAGE` | 3.40 V | Emergency shutdown voltage |
| `DSLV_X1202_AC_LOST_SHUTDOWN_SECONDS` | 300 | Max AC-loss hold-up time |

## Safety Notes

- Shutdown is disabled when the UPS is unreadable (fail-safe).
- Only one shutdown is scheduled per event; marker file at `/var/lib/dslv_zpdi/x1202_shutdown_requested`.
- Cancel a pending shutdown with `sudo shutdown -c` if power returns.

## References

- `specs/SPEC-004A.8.md`
- Maxim MAX17048/MAX17049 datasheet
