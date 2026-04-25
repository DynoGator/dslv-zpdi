"""Dashboard configuration loader.

Loads a TOML file (default: ~/.config/dslv-zpdi/dashboard.toml) and merges
it over the baked-in defaults. Env var DSLV_DASHBOARD_CONFIG overrides
the search path.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "dslv-zpdi" / "dashboard.toml"


@dataclass
class ThemeCfg:
    system_border: str = "bright_cyan"
    pipeline_border: str = "bright_green"
    hardware_border: str = "yellow"
    waterfall_border: str = "bright_magenta"
    logs_border: str = "bright_white"
    notifications_border: str = "bright_magenta"
    banner_border: str = "bright_green"
    footer_border: str = "bright_black"
    accent: str = "bright_cyan"


@dataclass
class PanelsCfg:
    system: bool = True
    pipeline: bool = True
    hardware: bool = True
    waterfall: bool = True
    anomaly: bool = True
    weather: bool = True
    storm: bool = True
    logs: bool = True
    notifications: bool = True


@dataclass
class WaterfallCfg:
    mode: str = "SWEEP"
    center_hz: int = 100_000_000
    span_hz: int = 20_000_000
    history: int = 12


@dataclass
class NotificationsCfg:
    humor_every_s: float = 4.0
    glitch_every_s: float = 37.0
    max_items: int = 8


@dataclass
class LogsCfg:
    max_lines: int = 14


@dataclass
class KeyCfg:
    quit: str = "q"
    pause: str = " "
    wf_mode: str = "m"
    real_sdr: str = "r"
    help: str = "h"


@dataclass
class DashboardConfig:
    refresh: float = 0.5
    show_banner: bool = True
    service_unit: str = "dslv-zpdi"
    source_path: str = ""
    theme: ThemeCfg = field(default_factory=ThemeCfg)
    panels: PanelsCfg = field(default_factory=PanelsCfg)
    waterfall: WaterfallCfg = field(default_factory=WaterfallCfg)
    notifications: NotificationsCfg = field(default_factory=NotificationsCfg)
    logs: LogsCfg = field(default_factory=LogsCfg)
    keys: KeyCfg = field(default_factory=KeyCfg)


def _apply(section: dict, target) -> None:
    """Merge a dict onto a dataclass in place (ignoring unknown keys)."""
    if not isinstance(section, dict):
        return
    known = set(target.__dataclass_fields__.keys())
    for k, v in section.items():
        if k in known:
            setattr(target, k, v)


def load_config(path: Path | None = None) -> DashboardConfig:
    """Load config from path (or DSLV_DASHBOARD_CONFIG env, or default).
    Silently returns defaults if the file is missing or malformed."""
    cfg = DashboardConfig()

    if path is None:
        env = os.getenv("DSLV_DASHBOARD_CONFIG")
        path = Path(env) if env else DEFAULT_CONFIG_PATH

    cfg.source_path = str(path)

    if not path.exists():
        return cfg

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return cfg

    dash = data.get("dashboard", {})
    for k in ("refresh", "show_banner", "service_unit"):
        if k in dash:
            setattr(cfg, k, dash[k])

    _apply(dash.get("theme", {}), cfg.theme)
    _apply(dash.get("panels", {}), cfg.panels)
    _apply(dash.get("waterfall", {}), cfg.waterfall)
    _apply(dash.get("notifications", {}), cfg.notifications)
    _apply(dash.get("logs", {}), cfg.logs)
    _apply(dash.get("keybindings", {}), cfg.keys)

    return cfg
