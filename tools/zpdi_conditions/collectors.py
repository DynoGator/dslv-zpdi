"""Metric collectors for the ZPDI_CONDITIONS dashboard.

Each collector runs in its own thread, fetches a remote source at a configured
interval, and writes a :class:`Metric` into the shared :class:`MetricStore`.
Errors are captured in-band so the UI can render them in the metric's own card.

All network access uses only the Python standard library (``urllib``) so the
dashboard adds no new PyPI dependencies and never touches SDR hardware.
"""

from __future__ import annotations

import csv
import http.cookiejar
import io
import json
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from zpdi_conditions.config import ZpdiConditionsConfig


@dataclass
class Metric:
    """One dashboard metric."""

    key: str
    label: str
    category: str
    value: str = "--"
    unit: str = ""
    trend: str = ""
    last_refresh: datetime | None = None
    error: str | None = None
    source: str = ""
    interval_seconds: int = 60

    def age_seconds(self) -> float | None:
        """Seconds since the last successful refresh."""
        if self.last_refresh is None:
            return None
        return (datetime.now(timezone.utc) - self.last_refresh).total_seconds()


@dataclass
class MetricStore:
    """Thread-safe store of the latest metric values."""

    cfg: ZpdiConditionsConfig
    metrics: dict[str, Metric] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _stop: threading.Event = field(default_factory=threading.Event)
    _manual_refresh: threading.Event = field(default_factory=threading.Event)

    def __post_init__(self) -> None:
        # Seed store with placeholder metrics so the UI has something to render
        # before the first collector completes.
        placeholders = [
            Metric(
                key="kp",
                label="Planetary K-index (Kp)",
                category="Space Weather",
                source=self.cfg.kp.name,
                interval_seconds=self.cfg.kp.interval_seconds,
            ),
            Metric(
                key="vsw",
                label="Solar Wind Speed (Vsw)",
                category="Space Weather",
                source=self.cfg.solar_wind.name,
                interval_seconds=self.cfg.solar_wind.interval_seconds,
            ),
            Metric(
                key="bt",
                label="IMF Total Field (Bt)",
                category="Space Weather",
                source=self.cfg.imf.name,
                interval_seconds=self.cfg.imf.interval_seconds,
            ),
            Metric(
                key="bz",
                label="IMF Vertical Alignment (Bz)",
                category="Space Weather",
                source=self.cfg.imf.name,
                interval_seconds=self.cfg.imf.interval_seconds,
            ),
            Metric(
                key="ionosphere",
                label="Ionospheric Density Anomalies",
                category="Space Weather",
                source=self.cfg.ionosphere.name,
                interval_seconds=self.cfg.ionosphere.interval_seconds,
            ),
            Metric(
                key="temperature",
                label="Ambient Temperature",
                category="Surface Weather",
                source=self.cfg.weather.name,
                interval_seconds=self.cfg.weather.interval_seconds,
            ),
            Metric(
                key="wind",
                label="Wind Speed & Direction",
                category="Surface Weather",
                source=self.cfg.weather.name,
                interval_seconds=self.cfg.weather.interval_seconds,
            ),
            Metric(
                key="humidity",
                label="Relative Humidity (RH)",
                category="Surface Weather",
                source=self.cfg.weather.name,
                interval_seconds=self.cfg.weather.interval_seconds,
            ),
            Metric(
                key="pressure",
                label="Station Pressure",
                category="Barometric",
                source=self.cfg.weather.name,
                interval_seconds=self.cfg.weather.interval_seconds,
            ),
            Metric(
                key="pm25",
                label="Wildfire Smoke/Soot Aerosols (PM2.5)",
                category="Aerosol Density",
                source=self.cfg.air_quality.name,
                interval_seconds=self.cfg.air_quality.interval_seconds,
            ),
            Metric(
                key="gamma",
                label="Ambient Gamma Rate",
                category="Ionizing Radiation",
                source=self.cfg.gamma.name,
                interval_seconds=self.cfg.gamma.interval_seconds,
            ),
            Metric(
                key="xray",
                label="Solar X-ray Flux",
                category="Space Weather",
                source=self.cfg.xray.name,
                interval_seconds=self.cfg.xray.interval_seconds,
            ),
            Metric(
                key="cosmic",
                label="Secondary Cosmic Ray Flux",
                category="Ionizing Radiation",
                source=self.cfg.cosmic_rays.name,
                interval_seconds=self.cfg.cosmic_rays.interval_seconds,
            ),
        ]
        for m in placeholders:
            self.metrics[m.key] = m

    def update(self, metric: Metric) -> None:
        with self._lock:
            self.metrics[metric.key] = metric

    def get(self, key: str) -> Metric:
        with self._lock:
            return self.metrics.get(key, Metric(key=key, label=key, category="Unknown"))

    def all(self) -> dict[str, Metric]:
        with self._lock:
            return dict(self.metrics)

    def request_refresh(self) -> None:
        """Signal every collector to wake immediately for a manual refresh."""
        self._manual_refresh.set()

    def _wait_for_interval(self, interval: int) -> bool:
        """Wait for the interval or until a manual refresh/stop is requested."""
        deadline = time.monotonic() + interval
        while not self._stop.is_set():
            if self._manual_refresh.wait(0.25):
                return False  # manual refresh requested
            if time.monotonic() >= deadline:
                return True  # normal interval elapsed
        return False

    def stop(self) -> None:
        self._stop.set()
        self._manual_refresh.set()


# ---------------------------------------------------------------------------
# Shared HTTP helpers
# ---------------------------------------------------------------------------

def _fetch_json(url: str, timeout: float, cookie_jar: Any | None = None) -> Any:
    """Fetch and parse JSON from ``url``."""
    opener = urllib.request.build_opener()
    if cookie_jar is not None:
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ZPDI_CONDITIONS/1.0 (dslv-zpdi; Python-urllib)",
            "Accept": "application/json",
        },
    )
    with opener.open(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def _fetch_text(url: str, timeout: float, cookie_jar: Any | None = None) -> str:
    """Fetch plain text from ``url``."""
    opener = urllib.request.build_opener()
    if cookie_jar is not None:
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ZPDI_CONDITIONS/1.0 (dslv-zpdi; Python-urllib)",
            "Accept": "text/plain,text/csv,*/*",
        },
    )
    with opener.open(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _deg_to_cardinal(deg: float) -> str:
    """Convert wind direction degrees to 16-point compass bearing."""
    dirs = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
    ]
    idx = int((deg + 11.25) / 22.5) % 16
    return dirs[idx]


# ---------------------------------------------------------------------------
# Individual collectors
# ---------------------------------------------------------------------------

def _collect_kp(cfg: ZpdiConditionsConfig) -> Metric:
    base = Metric(
        key="kp",
        label="Planetary K-index (Kp)",
        category="Space Weather",
        source=cfg.kp.name,
        interval_seconds=cfg.kp.interval_seconds,
    )
    try:
        data = _fetch_json(cfg.kp.url, cfg.kp.timeout_seconds)
        if not isinstance(data, list) or len(data) < 2:
            raise ValueError("unexpected Kp payload shape")
        # First row is header, last data row is most recent.
        latest = data[-1]
        if isinstance(latest, list):
            # legacy header-first array-of-arrays format
            kp_value = float(latest[1])
        else:
            kp_value = float(latest["Kp"])

        # Trend: compare with previous value if available.
        prev = data[-2]
        prev_val = float(prev[1] if isinstance(prev, list) else prev["Kp"])
        if kp_value > prev_val:
            trend = "▲ inclining"
        elif kp_value < prev_val:
            trend = "▼ declining"
        else:
            trend = "→ steady"

        # NOAA textual interpretation (rough mapping).
        if kp_value < 4:
            status = "Quiet"
        elif kp_value < 5:
            status = "Unsettled / Active"
        elif kp_value < 6:
            status = "G1 Minor Storm"
        elif kp_value < 7:
            status = "G2 Moderate Storm"
        elif kp_value < 8:
            status = "G3 Strong Storm"
        elif kp_value < 9:
            status = "G4 Severe Storm"
        else:
            status = "G5 Extreme Storm"

        base.value = f"{kp_value:.2f}"
        base.unit = status
        base.trend = trend
        base.last_refresh = _now()
    except Exception as exc:  # noqa: BLE001
        base.error = f"Kp fetch failed: {exc}"
    return base


def _collect_solar_wind(cfg: ZpdiConditionsConfig) -> Metric:
    base = Metric(
        key="vsw",
        label="Solar Wind Speed (Vsw)",
        category="Space Weather",
        source=cfg.solar_wind.name,
        interval_seconds=cfg.solar_wind.interval_seconds,
    )
    try:
        data = _fetch_json(cfg.solar_wind.url, cfg.solar_wind.timeout_seconds)
        if not isinstance(data, list) or not data:
            raise ValueError("unexpected solar-wind payload shape")
        # The JSON is newest-first in practice, but be defensive.
        latest = max(
            (row for row in data if row.get("active")),
            key=lambda row: row.get("time_tag", ""),
            default=None,
        )
        if latest is None:
            latest = data[0]
        speed = float(latest["proton_speed"])

        prev = data[1] if len(data) > 1 else latest
        prev_speed = float(prev.get("proton_speed", speed))
        if speed > prev_speed:
            trend = "▲ gaining velocity"
        elif speed < prev_speed:
            trend = "▼ slowing"
        else:
            trend = "→ steady"

        base.value = f"{speed:.1f}"
        base.unit = "km/s"
        base.trend = trend
        base.last_refresh = _now()
    except Exception as exc:  # noqa: BLE001
        base.error = f"Solar-wind fetch failed: {exc}"
    return base


def _collect_imf(cfg: ZpdiConditionsConfig) -> tuple[Metric, Metric]:
    bt = Metric(
        key="bt",
        label="IMF Total Field (Bt)",
        category="Space Weather",
        source=cfg.imf.name,
        interval_seconds=cfg.imf.interval_seconds,
    )
    bz = Metric(
        key="bz",
        label="IMF Vertical Alignment (Bz)",
        category="Space Weather",
        source=cfg.imf.name,
        interval_seconds=cfg.imf.interval_seconds,
    )
    try:
        data = _fetch_json(cfg.imf.url, cfg.imf.timeout_seconds)
        if not isinstance(data, list) or not data:
            raise ValueError("unexpected IMF payload shape")
        latest = max(
            (row for row in data if row.get("active")),
            key=lambda row: row.get("time_tag", ""),
            default=None,
        )
        if latest is None:
            latest = data[0]
        bt_val = float(latest["bt"])
        bz_val = float(latest["bz_gsm"])

        prev = data[1] if len(data) > 1 else latest
        prev_bt = float(prev.get("bt", bt_val))
        prev_bz = float(prev.get("bz_gsm", bz_val))

        bt.value = f"{bt_val:.2f}"
        bt.unit = "nT"
        if bt_val > prev_bt:
            bt.trend = "▲ compressing higher"
        elif bt_val < prev_bt:
            bt.trend = "▼ weakening"
        else:
            bt.trend = "→ steady"
        bt.last_refresh = _now()

        bz.value = f"{bz_val:.2f}"
        bz.unit = "nT (Southward)" if bz_val < 0 else "nT (Northward)"
        if bz_val < prev_bz:
            bz.trend = "▲ negative deflection"
        elif bz_val > prev_bz:
            bz.trend = "▼ positive deflection"
        else:
            bz.trend = "→ steady"
        bz.last_refresh = _now()
    except Exception as exc:  # noqa: BLE001
        bt.error = f"IMF fetch failed: {exc}"
        bz.error = f"IMF fetch failed: {exc}"
    return bt, bz


def _collect_ionosphere(cfg: ZpdiConditionsConfig) -> Metric:
    base = Metric(
        key="ionosphere",
        label="Ionospheric Density Anomalies",
        category="Space Weather",
        source=cfg.ionosphere.name,
        interval_seconds=cfg.ionosphere.interval_seconds,
    )
    try:
        data = _fetch_json(cfg.ionosphere.url, cfg.ionosphere.timeout_seconds)
        if not isinstance(data, dict):
            raise ValueError("unexpected scales payload shape")
        # The scales object is keyed by integer index strings. Index "0" is
        # the current observed scale, "1" is the next forecast period, etc.
        current = data.get("0") or data.get(0)
        if not isinstance(current, dict):
            raise ValueError("missing current scale entry")
        s = current.get("S", {}) or {}
        scale = s.get("Scale")
        text = s.get("Text") or "none"
        if scale is None or scale == "":
            scale_str = "0"
        else:
            scale_str = str(scale)
        labels = {
            "0": "No storm",
            "1": "Minor phase scintillation",
            "2": "Moderate phase scintillation",
            "3": "Strong phase scintillation",
            "4": "Severe phase scintillation",
            "5": "Extreme phase scintillation",
        }
        base.value = f"S{scale_str}"
        base.unit = labels.get(scale_str, text)
        base.trend = "→ monitoring TEC jitter"
        base.last_refresh = _now()
    except Exception as exc:  # noqa: BLE001
        base.error = f"Ionosphere fetch failed: {exc}"
    return base


def _collect_weather(cfg: ZpdiConditionsConfig) -> tuple[Metric, Metric, Metric, Metric]:
    temp = Metric(
        key="temperature",
        label="Ambient Temperature",
        category="Surface Weather",
        source=cfg.weather.name,
        interval_seconds=cfg.weather.interval_seconds,
    )
    wind = Metric(
        key="wind",
        label="Wind Speed & Direction",
        category="Surface Weather",
        source=cfg.weather.name,
        interval_seconds=cfg.weather.interval_seconds,
    )
    humidity = Metric(
        key="humidity",
        label="Relative Humidity (RH)",
        category="Surface Weather",
        source=cfg.weather.name,
        interval_seconds=cfg.weather.interval_seconds,
    )
    pressure = Metric(
        key="pressure",
        label="Station Pressure",
        category="Barometric",
        source=cfg.weather.name,
        interval_seconds=cfg.weather.interval_seconds,
    )
    try:
        data = _fetch_json(cfg.weather_url, cfg.weather.timeout_seconds)
        current = data.get("current", {})

        celsius = float(current.get("temperature_2m", 0))
        fahrenheit = celsius * 9 / 5 + 32
        temp.value = f"{fahrenheit:.1f}°F"
        temp.unit = f"({celsius:.1f}°C)"
        temp.trend = "→ surface forecast current"
        temp.last_refresh = _now()

        speed = float(current.get("wind_speed_10m", 0))
        # Open-Meteo returns km/h by default; convert to mph.
        mph = speed * 0.621371
        deg = float(current.get("wind_direction_10m", 0))
        wind.value = f"{mph:.1f} mph"
        wind.unit = f"from {_deg_to_cardinal(deg)}"
        wind.trend = "→ surface forecast current"
        wind.last_refresh = _now()

        rh = float(current.get("relative_humidity_2m", 0))
        humidity.value = f"{rh:.0f}%"
        humidity.unit = ""
        humidity.trend = "→ surface forecast current"
        humidity.last_refresh = _now()

        # Use pressure_msl (mean sea level) to match meteorological station
        # pressure reporting at elevation. Surface pressure at ~1627 m would
        # read ~840 mb; MSL is what the NWS/local report references.
        mb = current.get("pressure_msl")
        if mb is None:
            mb = current.get("surface_pressure", 0)
        mb = float(mb)
        inhg = mb * 0.02953
        pressure.value = f"{mb:.1f} mb"
        pressure.unit = f"({inhg:.2f} inHg)"
        pressure.trend = "→ surface forecast current"
        pressure.last_refresh = _now()
    except Exception as exc:  # noqa: BLE001
        err = f"Weather fetch failed: {exc}"
        temp.error = err
        wind.error = err
        humidity.error = err
        pressure.error = err
    return temp, wind, humidity, pressure


def _collect_air_quality(cfg: ZpdiConditionsConfig) -> Metric:
    base = Metric(
        key="pm25",
        label="Wildfire Smoke/Soot Aerosols (PM2.5)",
        category="Aerosol Density",
        source=cfg.air_quality.name,
        interval_seconds=cfg.air_quality.interval_seconds,
    )
    try:
        data = _fetch_json(cfg.air_quality_url, cfg.air_quality.timeout_seconds)
        current = data.get("current", {})
        pm25 = float(current.get("pm2_5", 0))
        if pm25 <= 12:
            desc = "Good"
        elif pm25 <= 35.4:
            desc = "Moderate"
        elif pm25 <= 55.4:
            desc = "Unhealthy for sensitive"
        elif pm25 <= 150.4:
            desc = "Unhealthy"
        elif pm25 <= 250.4:
            desc = "Very unhealthy"
        else:
            desc = "Hazardous"
        base.value = f"{pm25:.1f} µg/m³"
        base.unit = desc
        base.trend = "→ regional aerosol load"
        base.last_refresh = _now()
    except Exception as exc:  # noqa: BLE001
        base.error = f"PM2.5 fetch failed: {exc}"
    return base


def _collect_cosmic_rays(cfg: ZpdiConditionsConfig) -> Metric:
    base = Metric(
        key="cosmic",
        label="Secondary Cosmic Ray Flux",
        category="Ionizing Radiation",
        source=cfg.cosmic_rays.name,
        interval_seconds=cfg.cosmic_rays.interval_seconds,
    )
    try:
        text = _fetch_text(cfg.cosmic_rays.url, cfg.cosmic_rays.timeout_seconds)
        lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
        if not lines:
            raise ValueError("no data rows in NMDB realtime file")
        latest = lines[-1]
        parts = latest.split(";")
        if len(parts) < 3:
            raise ValueError(f"unexpected NMDB row: {latest}")
        ts_str, station, value_str = parts[0], parts[1], parts[2]
        value = float(value_str)
        # Compute a simple 1-hour trend from the last ~60 rows.
        recent = [float(ln.split(";")[2]) for ln in lines[-60:] if len(ln.split(";")) >= 3]
        if len(recent) >= 2:
            recent_avg = sum(recent) / len(recent)
            if value > recent_avg * 1.02:
                trend = "▲ elevated"
            elif value < recent_avg * 0.98:
                trend = "▼ suppressed"
            else:
                trend = "→ base equilibrium"
        else:
            trend = "→ base equilibrium"
        base.value = f"{value:.1f}"
        base.unit = f"counts/min ({station})"
        base.trend = trend
        base.last_refresh = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
    except Exception as exc:  # noqa: BLE001
        base.error = f"Cosmic-ray fetch failed: {exc}"
    return base


def _collect_gamma(cfg: ZpdiConditionsConfig) -> Metric:
    base = Metric(
        key="gamma",
        label="Ambient Gamma Rate",
        category="Ionizing Radiation",
        source=cfg.gamma.name,
        interval_seconds=cfg.gamma.interval_seconds,
    )
    cookie_jar = http.cookiejar.CookieJar()
    try:
        url = cfg.gamma.url.format(year=datetime.now(timezone.utc).year)
        # The EPA endpoint sets a session cookie on first request and returns
        # a CSV. A second request with the same cookie jar succeeds.
        text = _fetch_text(url, cfg.gamma.timeout_seconds, cookie_jar=cookie_jar)
        if not text.strip():
            # Prime the cookie jar with a lightweight HEAD-like GET.
            _fetch_text(url, 10.0, cookie_jar=cookie_jar)
            text = _fetch_text(url, cfg.gamma.timeout_seconds, cookie_jar=cookie_jar)

        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            raise ValueError("empty RadNet CSV")
        latest = rows[-1]
        dose = latest.get("DOSE EQUIVALENT RATE (nSv/h)", "").strip()
        if not dose:
            raise ValueError("DOSE EQUIVALENT RATE column empty")
        dose_val = float(dose)

        # Very crude trend: compare with the previous row if it has a value.
        prev_val = dose_val
        for row in reversed(rows[:-1]):
            prev_dose = row.get("DOSE EQUIVALENT RATE (nSv/h)", "").strip()
            if prev_dose:
                prev_val = float(prev_dose)
                break
        if dose_val > prev_val:
            trend = "▲ upward jitter"
        elif dose_val < prev_val:
            trend = "▼ downward drift"
        else:
            trend = "→ steady"

        base.value = f"{dose_val:.0f}"
        base.unit = "nSv/h"
        base.trend = trend
        # RadNet timestamps are local US/Mountain for Colorado Springs monitors.
        ts_raw = latest.get("SAMPLE COLLECTION TIME", "").strip()
        try:
            naive = datetime.strptime(ts_raw, "%m/%d/%Y %H:%M:%S")
            base.last_refresh = naive.replace(tzinfo=timezone.utc)
        except ValueError:
            base.last_refresh = _now()
    except Exception as exc:  # noqa: BLE001
        base.error = f"RadNet fetch failed: {exc}"
    return base


def _collect_xray(cfg: ZpdiConditionsConfig) -> Metric:
    base = Metric(
        key="xray",
        label="Solar X-ray Flux",
        category="Space Weather",
        source=cfg.xray.name,
        interval_seconds=cfg.xray.interval_seconds,
    )
    try:
        data = _fetch_json(cfg.xray.url, cfg.xray.timeout_seconds)
        if not isinstance(data, list) or not data:
            raise ValueError("unexpected X-ray payload shape")
        # Find latest long-band (0.1-0.8 nm) flux
        latest_long = max(
            (row for row in data if row.get("energy") == "0.1-0.8nm"),
            key=lambda row: row.get("time_tag", ""),
            default=None,
        )
        if latest_long is None:
            raise ValueError("no long-band X-ray flux found")

        flux = float(latest_long["flux"])
        
        # Determine flare class (A, B, C, M, X)
        if flux < 1e-7:
            flare_class = "A/B"
        elif flux < 1e-6:
            flare_class = "C"
        elif flux < 1e-5:
            flare_class = "M"
        else:
            flare_class = "X"
            
        # Very crude trend logic if we want to iterate.
        base.value = f"{flux:.2e}"
        base.unit = f"W/m² ({flare_class}-class)"
        if flare_class in ("M", "X"):
            base.trend = "▲ active flare"
        else:
            base.trend = "→ background"
            
        base.last_refresh = _now()
    except Exception as exc:  # noqa: BLE001
        base.error = f"X-ray fetch failed: {exc}"
    return base


# ---------------------------------------------------------------------------
# Collector threads
# ---------------------------------------------------------------------------

Collector = Callable[[ZpdiConditionsConfig, MetricStore], None]


def _make_loop(
    cfg: ZpdiConditionsConfig,
    store: MetricStore,
    name: str,
    interval: int,
    fn: Callable[[ZpdiConditionsConfig], Metric | tuple[Metric, ...]],
) -> Callable[[], None]:
    """Return a thread target that repeatedly calls ``fn`` and updates the store."""

    def _loop() -> None:
        while not store._stop.is_set():
            try:
                result = fn(cfg)
                if isinstance(result, tuple):
                    for metric in result:
                        store.update(metric)
                else:
                    store.update(result)
            except Exception as exc:  # noqa: BLE001
                # Defensive: should never reach here because collectors catch
                # their own exceptions, but if one leaks, at least the thread
                # survives and the error is visible.
                store.update(
                    Metric(
                        key=name,
                        label=name,
                        category="Internal",
                        error=f"Collector crashed: {exc}",
                    )
                )
            if store._wait_for_interval(interval):
                pass  # normal interval elapsed
            else:
                # Manual refresh requested: clear the flag only once all loops
                # have observed it. Since clearing too early would starve other
                # collectors, we use a simple countdown heuristic: wait a short
                # moment so every active loop sees the event, then clear.
                time.sleep(0.3)
                store._manual_refresh.clear()

    return _loop


def start_collectors(cfg: ZpdiConditionsConfig, store: MetricStore) -> list[threading.Thread]:
    """Start one background thread per metric source."""
    jobs: list[tuple[str, int, Callable[[ZpdiConditionsConfig], Any]]] = [
        ("kp", cfg.kp.interval_seconds, _collect_kp),
        ("vsw", cfg.solar_wind.interval_seconds, _collect_solar_wind),
        ("imf", cfg.imf.interval_seconds, _collect_imf),
        ("ionosphere", cfg.ionosphere.interval_seconds, _collect_ionosphere),
        ("weather", cfg.weather.interval_seconds, _collect_weather),
        ("air_quality", cfg.air_quality.interval_seconds, _collect_air_quality),
        ("cosmic_rays", cfg.cosmic_rays.interval_seconds, _collect_cosmic_rays),
        ("gamma", cfg.gamma.interval_seconds, _collect_gamma),
        ("xray", cfg.xray.interval_seconds, _collect_xray),
    ]
    threads: list[threading.Thread] = []
    for name, interval, fn in jobs:
        t = threading.Thread(
            target=_make_loop(cfg, store, name, interval, fn),
            name=f"zpdi-collector-{name}",
            daemon=True,
        )
        t.start()
        threads.append(t)
    return threads
