"""
SPEC-012 - Runtime Configuration Loader
Loads config/deployment.yaml with Pydantic validation and DSLV_* env overrides.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class ClockDiscipline(BaseModel):
    pps_required: bool = True
    pps_device: str = "/dev/pps0"
    chrony_tracking_required: bool = True
    max_pps_jitter_ns: float = 1000.0
    gps_lock_required: bool = True


class HealthThresholds(BaseModel):
    max_calibration_drift_percent: float = 20.0
    min_confirming_nodes: int = 4
    confirmation_window_ms: int = 300
    router_candidate_floor: float = 0.15


class Spec009Config(BaseModel):
    baseline_duration_hours: int = 72
    min_baseline_samples: int = 240
    persist_state: bool = True
    block_primary_while_learning: bool = True

    model_config = {"extra": "allow"}


class NodeProfile(BaseModel):
    hardware_tier: int = 1
    role: str = "institutional_anchor"
    timing_source: str = "gpsdo_clk_in"
    baseline_learning_enabled: bool = True
    allow_primary_output: bool = True


class PipelineConfig(BaseModel):
    center_freq_hz: float = Field(default=100e6)
    sample_rate_hz: float = Field(default=20e6)
    num_samples: int = 262144
    ingest_interval_sec: float = 0.1
    mode: str = "sdr"
    output_dir: str = "/home/dynogator/dslv-zpdi/output"


class Config(BaseModel):
    version: str = "1"
    project: str = "DSLV-ZPDI"
    environment: str = "field"
    paths: Dict[str, str] = Field(default_factory=dict)
    clock_discipline: ClockDiscipline = Field(default_factory=ClockDiscipline)
    health_thresholds: HealthThresholds = Field(default_factory=HealthThresholds)
    spec009: Spec009Config = Field(default_factory=Spec009Config)
    nodes: Dict[str, NodeProfile] = Field(default_factory=dict)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    env: Dict[str, str] = Field(default_factory=dict)

    model_config = {"extra": "allow"}

    @field_validator("paths", mode="before")
    @classmethod
    def _default_paths(cls, v: Any) -> Any:
        if not v:
            return {
                "primary_output": "/home/dynogator/dslv-zpdi/output/primary",
                "secondary_output": "/home/dynogator/dslv-zpdi/output/secondary",
                "state_dir": "/var/lib/dslv_zpdi",
                "baseline_state": "/var/lib/dslv_zpdi/baseline.json",
            }
        return v


def _env_override(config: Config) -> Config:
    """Apply DSLV_* environment variables over YAML config."""
    env_map: Dict[str, Any] = {}
    for key, val in os.environ.items():
        if not key.startswith("DSLV_"):
            continue
        env_map[key[5:].lower()] = val

    if "primary_output_dir" in env_map:
        config.paths["primary_output"] = env_map["primary_output_dir"]
    if "secondary_output_dir" in env_map:
        config.paths["secondary_output"] = env_map["secondary_output_dir"]
    if "baseline_state_path" in env_map:
        config.paths["baseline_state"] = env_map["baseline_state_path"]
    if "baseline_hours" in env_map:
        try:
            config.spec009.baseline_duration_hours = int(env_map["baseline_hours"])
        except ValueError:
            pass
    if "min_baseline_samples" in env_map:
        try:
            config.spec009.min_baseline_samples = int(env_map["min_baseline_samples"])
        except ValueError:
            pass
    if "center_freq_hz" in env_map:
        try:
            config.pipeline.center_freq_hz = float(env_map["center_freq_hz"])
        except ValueError:
            pass
    if "sample_rate_hz" in env_map:
        try:
            config.pipeline.sample_rate_hz = float(env_map["sample_rate_hz"])
        except ValueError:
            pass
    if "ingest_interval_sec" in env_map:
        try:
            config.pipeline.ingest_interval_sec = float(env_map["ingest_interval_sec"])
        except ValueError:
            pass

    return config


def load_config(path: Optional[str] = None) -> Config:
    """SPEC-012.1 - Load runtime configuration.

    Priority: env vars > YAML file > defaults.
    """
    config_path = path or os.getenv("DSLV_CONFIG_PATH", "config/deployment.yaml")
    config_file = Path(config_path)

    raw: Dict[str, Any] = {}
    if config_file.is_file():
        with open(config_file, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    config = Config.model_validate(raw)
    config = _env_override(config)
    return config
