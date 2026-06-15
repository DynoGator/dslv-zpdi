"""
SPEC-004A.CONFIG — Typed configuration profile models.

Supports safe environment-variable expansion of the form ${VAR:-default}.
Does NOT support arbitrary code execution or shell-style ${VAR%pattern}.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EnvExpansionError(ValueError):
    """Raised when environment-variable expansion fails."""


_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def expand_env_vars(value: Any) -> Any:
    """
    SPEC-004A.CONFIG — Recursively expand ${VAR:-default} placeholders.

    Only plain variable names with an optional default are supported.
    """
    if isinstance(value, str):

        def _repl(match: re.Match) -> str:
            var_name = match.group(1)
            default = match.group(2)
            env_value = os.getenv(var_name)
            if env_value is None:
                if default is None:
                    raise EnvExpansionError(f"Environment variable {var_name} not set and no default provided")
                return default
            return env_value

        return _ENV_PATTERN.sub(_repl, value)
    if isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_env_vars(v) for v in value]
    return value


class HardwareProfile(BaseModel):
    """SPEC-004A.CONFIG — Device-specific hardware profile section."""

    profile_id: str
    enclosure_brand_observed: str = ""
    enclosure_model_marking_observed: str = ""
    exact_pcb_revision: str | None = None
    qualification_status: str = "unverified"

    class Config:
        extra = "forbid"


class ReferenceClockConfig(BaseModel):
    """SPEC-004A.CONFIG — External reference clock configuration."""

    required: bool = True
    source: str = "lbe1421"
    requested_hz: int = 10_000_000
    connector_label_observed: str = ""
    connector_type: str | None = None
    direction_verified: bool = False
    input_impedance_ohms: int | None = None
    maximum_input_dbm: float | None = None
    electrical_level_verified: bool = False


class SdrConfig(BaseModel):
    """SPEC-004A.CONFIG — SDR backend configuration."""

    backend: str = "auto"
    uri: str = "auto"
    expected_iio_phy: str = "ad9361-phy"
    receive_channels: list[int] = Field(default_factory=lambda: [0])
    transmit_enabled: bool = False
    sample_rate_hz: int = 10_000_000
    rf_bandwidth_hz: int = 10_000_000
    buffer_samples: int = 262_144
    gain_mode: str = "manual"
    gain_db: float = 64.0


class TimingConfig(BaseModel):
    """SPEC-004A.CONFIG — Timing authority configuration."""

    authority: str = "lbe1421"
    pps_device: str = "/dev/pps0"
    nmea_port: str = "/dev/ttyACM0"
    reference_frequency_hz: int = 10_000_000
    pps_degraded_ns: float = 1_000.0
    pps_kill_ns: float = 10_000.0
    max_fix_age_s: float = 10.0


class TrustConfig(BaseModel):
    """SPEC-004A.CONFIG — Trust/fail-closed configuration."""

    fail_closed: bool = True
    allow_simulator_fallback: bool = False
    require_firmware_fingerprint: bool = True
    require_calibration_manifest: bool = True
    require_production_hmac_key: bool = True


class RfConfig(BaseModel):
    """SPEC-004A.CONFIG — RF observation configuration."""

    center_frequency_hz: int = 100_000_000
    sample_rate_hz: int = 10_000_000
    rf_bandwidth_hz: int = 10_000_000
    gain_db: float = 64.0
    gain_mode: str = "manual"


class ConverterConfig(BaseModel):
    """SPEC-004A.CONFIG — Optional frequency-converter stage."""

    model: str = "direct_rf"
    serial: str = ""
    native_if_center_hz: int = 0
    lo_frequency_hz: int = 0
    lo_source: str = "direct_rf"
    sideband_sign: int = 1
    gain_db: float = 0.0
    loss_db: float = 0.0
    filter_low_hz: int | None = None
    filter_high_hz: int | None = None
    calibration_manifest_sha256: str = ""

    @field_validator("sideband_sign")
    @classmethod
    def _validate_sideband(cls, v: int) -> int:
        if v not in (-1, 1):
            raise ValueError("sideband_sign must be -1 or +1")
        return v


class NodeProfile(BaseModel):
    """SPEC-004A.CONFIG — Combined node profile (hardware + timing + RF + trust)."""

    schema_version: str = "1"
    identity: HardwareProfile
    hardware: dict[str, Any] = Field(default_factory=dict)
    sdr: SdrConfig = Field(default_factory=SdrConfig)
    timing: TimingConfig = Field(default_factory=TimingConfig)
    rf: RfConfig = Field(default_factory=RfConfig)
    converter: ConverterConfig | None = None
    trust: TrustConfig = Field(default_factory=TrustConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "NodeProfile":
        """Load and validate a node profile from YAML with env expansion."""
        import yaml  # pylint: disable=import-outside-toplevel

        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        if not isinstance(raw, dict):
            raise ValueError(f"Profile {path} is not a YAML mapping")
        expanded = expand_env_vars(raw)
        return cls(**expanded)

