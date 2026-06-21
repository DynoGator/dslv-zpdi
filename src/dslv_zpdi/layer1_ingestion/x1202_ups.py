"""
SPEC-004A.8 — Geekworm X-1202 UPS HAT monitor for Tier-1 Raspberry Pi 5 nodes.

Reads battery voltage, state-of-charge, and charge/discharge rate from the
Maxim MAX17048/MAX17049 fuel gauge over I2C, and reports AC-line presence
and charging control via GPIO.

The module is designed to fail gracefully: if the UPS is disconnected, the
I2C bus is unavailable, or GPIO access is denied, ``sample()`` returns a
degraded/absent result rather than raising an unhandled exception.
"""

from __future__ import annotations

import logging
import struct
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("dslv-zpdi.x1202")

# ── MAX17048/MAX17049 register map ─────────────────────────────────────────
_REG_VCELL = 0x02
_REG_SOC = 0x04
_REG_MODE = 0x06
_REG_VER = 0x08
_REG_HIBRT = 0x0A
_REG_CONFIG = 0x0C
_REG_VALRT = 0x14
_REG_CRATE = 0x16
_REG_VRESET = 0x18
_REG_STATUS = 0x1A
_REG_TABLE = 0x40
_REG_CMD = 0xFE

_VCELL_LSB_V = 78.125e-6
_SOC_LSB_PERCENT = 1.0 / 256.0
_CRATE_LSB_PERCENT_PER_HOUR = 0.208

# Raspberry Pi 5 pinctrl-rp1 base offset; GPIO6=575, GPIO16=585
_PI5_RP1_GPIO_BASE = 569


@dataclass
class UpsSample:
    """SPEC-004A.8.1 — Normalized X-1202 telemetry sample."""

    spec_id: str = "SPEC-004A.8.1"
    timestamp_utc: float = 0.0
    battery_voltage_v: float = 0.0
    battery_percent: float = 0.0
    charge_rate_percent_per_hour: float = 0.0
    ac_present: bool | None = None
    charging_enabled: bool | None = None
    ic_name: str = ""
    ic_version: int = 0
    i2c_address: int = 0x36
    i2c_bus: int = 1
    alert_low_battery: bool = False
    alert_ac_lost: bool = False
    health: str = "unknown"
    error: str | None = None
    hardware_tier: int = 1
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """SPEC-004A.8.1 — Serialize sample to a JSON-safe dict."""
        return asdict(self)


class X1202UpsMonitor:
    """
    SPEC-004A.8 — Minimal, fail-safe interface to the Geekworm X-1202 UPS HAT.

    Args:
        i2c_bus: Linux I2C bus number (default 1 for ``/dev/i2c-1``).
        i2c_address: 7-bit MAX17048 address (default ``0x36``).
        ac_gpio_bcm: BCM GPIO number for AC presence input (default 6).
        charge_gpio_bcm: BCM GPIO number for charging control output (default 16).
        ac_gpio_sysfs: Optional sysfs GPIO number override for AC input.
        charge_gpio_sysfs: Optional sysfs GPIO number override for charge control.
    """

    def __init__(
        self,
        i2c_bus: int = 1,
        i2c_address: int = 0x36,
        ac_gpio_bcm: int = 6,
        charge_gpio_bcm: int = 16,
        ac_gpio_sysfs: int | None = None,
        charge_gpio_sysfs: int | None = None,
    ) -> None:
        self.i2c_bus = i2c_bus
        self.i2c_address = i2c_address
        self.ac_gpio_bcm = ac_gpio_bcm
        self.charge_gpio_bcm = charge_gpio_bcm
        self.ac_gpio_sysfs = ac_gpio_sysfs or (_PI5_RP1_GPIO_BASE + ac_gpio_bcm)
        self.charge_gpio_sysfs = charge_gpio_sysfs or (_PI5_RP1_GPIO_BASE + charge_gpio_bcm)

        self._bus: Any = None
        self._gpio_exported: set[int] = set()
        self._gpio_closed: bool = False

    # ── Context manager ─────────────────────────────────────────────────────
    def __enter__(self) -> "X1202UpsMonitor":
        """SPEC-004A.8 — Open I2C and GPIO resources."""
        self.open()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """SPEC-004A.8 — Release all resources."""
        self.close()

    # ── I2C helpers ─────────────────────────────────────────────────────────
    def _read_word(self, register: int) -> int | None:
        """SPEC-004A.8.2 — Read a 16-bit MAX17048 register (MSB-first)."""
        if self._bus is None:
            return None
        try:
            data = self._bus.read_i2c_block_data(self.i2c_address, register, 2)
            return (data[0] << 8) | data[1]
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug("I2C read failed at reg 0x%02x: %s", register, exc)
            return None

    def _write_word(self, register: int, value: int) -> bool:
        """SPEC-004A.8.2 — Write a 16-bit MAX17048 register (MSB-first)."""
        if self._bus is None:
            return False
        try:
            self._bus.write_i2c_block_data(
                self.i2c_address, register, [(value >> 8) & 0xFF, value & 0xFF]
            )
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug("I2C write failed at reg 0x%02x: %s", register, exc)
            return False

    # ── GPIO helpers (sysfs fallback) ───────────────────────────────────────
    def _gpio_path(self, gpio: int, name: str) -> Path:
        return Path(f"/sys/class/gpio/gpio{gpio}/{name}")

    def _export_gpio(self, gpio: int, direction: str) -> bool:
        """SPEC-004A.8.3 — Export a sysfs GPIO line and set direction."""
        if self._gpio_closed:
            return False
        try:
            if not self._gpio_path(gpio, "").exists():
                Path("/sys/class/gpio/export").write_text(str(gpio), encoding="utf-8")
            self._gpio_path(gpio, "direction").write_text(direction, encoding="utf-8")
            self._gpio_exported.add(gpio)
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug("GPIO %d export/%s failed: %s", gpio, direction, exc)
            return False

    def _read_gpio(self, gpio: int) -> int | None:
        """SPEC-004A.8.3 — Read a sysfs GPIO line."""
        try:
            return int(self._gpio_path(gpio, "value").read_text(encoding="utf-8").strip())
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug("GPIO %d read failed: %s", gpio, exc)
            return None

    def _write_gpio(self, gpio: int, value: int) -> bool:
        """SPEC-004A.8.3 — Write a sysfs GPIO line."""
        try:
            self._gpio_path(gpio, "value").write_text(str(value), encoding="utf-8")
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug("GPIO %d write failed: %s", gpio, exc)
            return False

    def _unexport_gpio(self, gpio: int) -> None:
        """SPEC-004A.8.3 — Unexport a sysfs GPIO line."""
        try:
            Path("/sys/class/gpio/unexport").write_text(str(gpio), encoding="utf-8")
        except Exception:  # pylint: disable=broad-except
            pass
        self._gpio_exported.discard(gpio)

    # ── Public lifecycle ────────────────────────────────────────────────────
    def open(self) -> None:
        """SPEC-004A.8 — Initialize SMBus and GPIO lines."""
        if self._bus is not None:
            return
        try:
            import smbus2  # pylint: disable=import-outside-toplevel

            self._bus = smbus2.SMBus(self.i2c_bus)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Cannot open I2C bus %d: %s", self.i2c_bus, exc)
            self._bus = None

        self._export_gpio(self.ac_gpio_sysfs, "in")
        self._export_gpio(self.charge_gpio_sysfs, "out")

    def close(self) -> None:
        """SPEC-004A.8 — Release SMBus and GPIO lines."""
        self._gpio_closed = True
        for gpio in list(self._gpio_exported):
            self._unexport_gpio(gpio)
        if self._bus is not None:
            try:
                self._bus.close()
            except Exception:  # pylint: disable=broad-except
                pass
            self._bus = None

    # ── Fuel-gauge readings ─────────────────────────────────────────────────
    def read_voltage(self) -> float | None:
        """SPEC-004A.8.2 — Battery cell voltage in volts."""
        raw = self._read_word(_REG_VCELL)
        return None if raw is None else raw * _VCELL_LSB_V

    def read_soc(self) -> float | None:
        """SPEC-004A.8.2 — State-of-charge as a percentage (0–100)."""
        raw = self._read_word(_REG_SOC)
        return None if raw is None else raw * _SOC_LSB_PERCENT

    def read_charge_rate(self) -> float | None:
        """SPEC-004A.8.2 — Charge/discharge rate in %/hour."""
        raw = self._read_word(_REG_CRATE)
        if raw is None:
            return None
        signed = struct.unpack(">h", struct.pack(">H", raw))[0]
        return signed * _CRATE_LSB_PERCENT_PER_HOUR

    def read_version(self) -> int | None:
        """SPEC-004A.8.2 — IC production version register."""
        return self._read_word(_REG_VER)

    # ── GPIO readings/control ───────────────────────────────────────────────
    def read_ac_present(self) -> bool | None:
        """
        SPEC-004A.8.3 — Return True when AC power is present.

        GPIO6 is high when the power adapter is OK and low when AC is lost.
        """
        value = self._read_gpio(self.ac_gpio_sysfs)
        if value is None:
            return None
        return bool(value)

    def read_charging_enabled(self) -> bool | None:
        """
        SPEC-004A.8.3 — Return True if battery charging is currently enabled.

        GPIO16 is active-low: low = charging enabled, high = charging disabled.
        """
        value = self._read_gpio(self.charge_gpio_sysfs)
        if value is None:
            return None
        return value == 0

    def set_charging_enabled(self, enabled: bool) -> bool:
        """
        SPEC-004A.8.3 — Enable or disable battery charging.

        Args:
            enabled: ``True`` to allow charging (drive GPIO16 low),
                     ``False`` to disable charging (drive GPIO16 high).
        """
        return self._write_gpio(self.charge_gpio_sysfs, 0 if enabled else 1)

    # ── Compound sample ─────────────────────────────────────────────────────
    def sample(self) -> UpsSample:
        """SPEC-004A.8.1 — Read a complete UPS telemetry sample."""
        now = time.time()
        s = UpsSample(
            timestamp_utc=now,
            i2c_address=self.i2c_address,
            i2c_bus=self.i2c_bus,
        )

        if self._bus is None:
            s.health = "absent"
            s.error = f"i2c bus {self.i2c_bus} not available"
            return s

        voltage = self.read_voltage()
        soc = self.read_soc()
        crate = self.read_charge_rate()
        version = self.read_version()
        ac_present = self.read_ac_present()
        charging = self.read_charging_enabled()

        if voltage is None or soc is None:
            s.health = "absent"
            s.error = "MAX17048 not responding at 0x36"
            return s

        s.battery_voltage_v = round(voltage, 4)
        s.battery_percent = round(soc, 2)
        s.charge_rate_percent_per_hour = round(crate, 2) if crate is not None else 0.0
        s.ic_name = "MAX17048/MAX17049"
        s.ic_version = version if version is not None else 0
        s.ac_present = ac_present
        s.charging_enabled = charging

        # Health classification
        if soc <= 15 or voltage <= 3.40:
            s.health = "critical"
            s.alert_low_battery = True
        elif soc <= 30 or voltage <= 3.60:
            s.health = "degraded"
        else:
            s.health = "healthy"

        if ac_present is False:
            s.alert_ac_lost = True
            if s.health == "healthy":
                s.health = "degraded"

        s.provenance = {
            "registers": {
                "vcell_raw": self._read_word(_REG_VCELL),
                "soc_raw": self._read_word(_REG_SOC),
                "crate_raw": self._read_word(_REG_CRATE),
                "version_raw": version,
            },
            "gpio": {
                "ac_bcm": self.ac_gpio_bcm,
                "ac_sysfs": self.ac_gpio_sysfs,
                "charge_bcm": self.charge_gpio_bcm,
                "charge_sysfs": self.charge_gpio_sysfs,
            },
        }

        return s


def ups_telemetry(
    i2c_bus: int = 1,
    i2c_address: int = 0x36,
    ac_gpio_bcm: int = 6,
    charge_gpio_bcm: int = 16,
) -> dict[str, Any]:
    """
    SPEC-004A.8 — One-shot X-1202 UPS health telemetry.

    Returns a JSON-serializable dict. This function is safe to call from
    health checks, the dashboard, or the ingestion pipeline: if the UPS is
    absent, the returned dict carries ``health: absent`` instead of raising.
    """
    with X1202UpsMonitor(
        i2c_bus=i2c_bus,
        i2c_address=i2c_address,
        ac_gpio_bcm=ac_gpio_bcm,
        charge_gpio_bcm=charge_gpio_bcm,
    ) as monitor:
        return monitor.sample().to_dict()
