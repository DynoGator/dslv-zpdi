"""Configuration for the ZPDI_CONDITIONS local dashboard.

All settings are overridable through environment variables so the dashboard
can be adapted to different locations without editing source files.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Penrose, CO tracking footprint (Front Range / Fremont County).
DEFAULT_LATITUDE = 38.425
DEFAULT_LONGITUDE = -105.023
DEFAULT_LOCATION_NAME = "Penrose, CO"


@dataclass(frozen=True)
class DataSource:
    """A remote or local data source."""

    name: str
    url: str
    interval_seconds: int
    timeout_seconds: float = 15.0


@dataclass(frozen=True)
class ZpdiConditionsConfig:
    """Runtime configuration for ZPDI_CONDITIONS."""

    location_name: str = DEFAULT_LOCATION_NAME
    latitude: float = DEFAULT_LATITUDE
    longitude: float = DEFAULT_LONGITUDE

    # Tuning ------------------------------------------------------------------
    tui_refresh_hz: float = 2.0
    card_layout: str = "two_column"  # two_column | one_column | auto

    # Data sources ------------------------------------------------------------
    kp: DataSource = field(
        default_factory=lambda: DataSource(
            name="NOAA Planetary K-index",
            url="https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
            interval_seconds=300,
        )
    )
    solar_wind: DataSource = field(
        default_factory=lambda: DataSource(
            name="NOAA RTSW Solar Wind",
            url="https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json",
            interval_seconds=60,
        )
    )
    imf: DataSource = field(
        default_factory=lambda: DataSource(
            name="NOAA RTSW Magnetometer",
            url="https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json",
            interval_seconds=60,
        )
    )
    ionosphere: DataSource = field(
        default_factory=lambda: DataSource(
            name="NOAA Space Weather Scales",
            url="https://services.swpc.noaa.gov/products/noaa-scales.json",
            interval_seconds=600,
        )
    )
    weather: DataSource = field(
        default_factory=lambda: DataSource(
            name="Open-Meteo Forecast",
            url="https://api.open-meteo.com/v1/forecast",
            interval_seconds=900,
        )
    )
    air_quality: DataSource = field(
        default_factory=lambda: DataSource(
            name="Open-Meteo Air Quality",
            url="https://air-quality-api.open-meteo.com/v1/air-quality",
            interval_seconds=1800,
        )
    )
    cosmic_rays: DataSource = field(
        default_factory=lambda: DataSource(
            name="NMDB Real-Time Neutron Monitor",
            url="https://rt.nmdb.eu/realtime.txt",
            interval_seconds=900,
        )
    )
    gamma: DataSource = field(
        default_factory=lambda: DataSource(
            name="EPA RadNet Colorado Springs",
            url="https://radnet.epa.gov/cdx-radnet-rest/api/rest/csv/{year}/fixed/CO/COLORADO%20SPRINGS",
            interval_seconds=1800,
            timeout_seconds=45.0,
        )
    )
    xray: DataSource = field(
        default_factory=lambda: DataSource(
            name="NOAA Solar X-ray Flux",
            url="https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json",
            interval_seconds=300,
        )
    )

    @property
    def weather_url(self) -> str:
        """Build the Open-Meteo forecast URL for the configured location."""
        return (
            f"{self.weather.url}"
            f"?latitude={self.latitude:.5f}"
            f"&longitude={self.longitude:.5f}"
            "&current=temperature_2m,relative_humidity_2m,"
            "pressure_msl,surface_pressure,wind_speed_10m,wind_direction_10m"
            "&timezone=America%2FDenver"
        )

    @property
    def air_quality_url(self) -> str:
        """Build the Open-Meteo air-quality URL for the configured location."""
        return (
            f"{self.air_quality.url}"
            f"?latitude={self.latitude:.5f}"
            f"&longitude={self.longitude:.5f}"
            "&current=pm2_5"
            "&timezone=America%2FDenver"
        )


def load_config() -> ZpdiConditionsConfig:
    """Load configuration from environment variables and defaults."""
    kwargs: dict[str, object] = {
        "location_name": os.getenv("ZPDI_COND_LOCATION", DEFAULT_LOCATION_NAME),
        "latitude": float(os.getenv("ZPDI_COND_LAT", str(DEFAULT_LATITUDE))),
        "longitude": float(os.getenv("ZPDI_COND_LON", str(DEFAULT_LONGITUDE))),
        "tui_refresh_hz": float(os.getenv("ZPDI_COND_REFRESH_HZ", "2.0")),
        "card_layout": os.getenv("ZPDI_COND_LAYOUT", "two_column"),
    }

    # Allow per-source interval overrides for tuning refresh cadence.
    for key in ("kp", "solar_wind", "imf", "ionosphere", "weather", "air_quality", "cosmic_rays", "gamma", "xray"):
        env_interval = os.getenv(f"ZPDI_COND_{key.upper()}_INTERVAL")
        if env_interval:
            source = getattr(ZpdiConditionsConfig, key)
            assert isinstance(source, DataSource), source
            kwargs[key] = DataSource(
                name=source.name,
                url=source.url,
                interval_seconds=int(env_interval),
                timeout_seconds=source.timeout_seconds,
            )

    return ZpdiConditionsConfig(**kwargs)
