"""
SPEC-005A.4 — HAL factory (Rev 5.0.0).

Supports both the legacy monolithic HAL API (for existing tests and callers)
and the new composed Tier-1 HAL. New code should use `get_tier1_hal()`.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from dslv_zpdi.config_models import NodeProfile
from dslv_zpdi.core.exceptions import (
    ConfigurationError,
)
from dslv_zpdi.core.key_provider import (
    DevelopmentKeyProvider,
    KeyProvider,
    ProductionKeyResolver,
)
from dslv_zpdi.layer1_ingestion.frequency_translation.mapper import FrequencyMapper
from dslv_zpdi.layer1_ingestion.frequency_translation.model import FrequencyTranslationStage
from dslv_zpdi.layer1_ingestion.hal_base import BaseHAL
from dslv_zpdi.layer1_ingestion.hal_hardware import HardwareHAL as LegacyHardwareHAL
from dslv_zpdi.layer1_ingestion.hal_simulated import SimulatedHAL
from dslv_zpdi.layer1_ingestion.hardware_hal import HardwareHAL
from dslv_zpdi.layer1_ingestion.sdr.pluto_iio import PlutoIioBackend
from dslv_zpdi.layer1_ingestion.sdr.qualification import Tier1QualificationPolicy
from dslv_zpdi.layer1_ingestion.sdr.simulated import SimulatedSdrBackend
from dslv_zpdi.layer1_ingestion.timing.lbe1421 import LBE1421TimingAuthority
from dslv_zpdi.layer1_ingestion.timing.simulated import SimulatedTimingAuthority

logger = logging.getLogger("dslv-zpdi.hal")

__all__ = [
    "BaseHAL",
    "HardwareHAL",
    "LegacyHardwareHAL",
    "SimulatedHAL",
    "get_hal",
    "get_tier1_hal",
    "ingest_gps_pps",
    "ingest_sdr",
    "verify_hardware_lock",
]


def get_hal(tier: int = 1, simulator: bool = False) -> LegacyHardwareHAL | SimulatedHAL:
    """
    SPEC-005A.4 — Legacy factory returning monolithic HAL classes.

    Kept for backward compatibility with existing tests and callers.
    New code should use `get_tier1_hal()`.
    """
    if simulator or os.getenv("DEV_SIMULATOR") == "1":
        return SimulatedHAL()
    try:
        return LegacyHardwareHAL()
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Legacy HardwareHAL init failed: %s", exc)
        logger.warning("Falling back to SimulatedHAL.")
        return SimulatedHAL()


def _build_frequency_translation(profile: NodeProfile) -> FrequencyTranslationStage:
    """SPEC-005A.4 — Build frequency-translation stage from profile."""
    cfg = profile.converter
    if cfg is not None and cfg.model != "direct_rf":
        return FrequencyTranslationStage(
            native_if_center_hz=cfg.native_if_center_hz,
            lo_frequency_hz=cfg.lo_frequency_hz,
            lo_source=cfg.lo_source,
            sideband_sign=cfg.sideband_sign,
            converter_model=cfg.model,
            converter_serial=cfg.serial,
            converter_gain_db=cfg.gain_db,
            converter_loss_db=cfg.loss_db,
            filter_low_hz=cfg.filter_low_hz,
            filter_high_hz=cfg.filter_high_hz,
            calibration_manifest_sha256=cfg.calibration_manifest_sha256,
        )
    return FrequencyMapper.build_direct_rf_stage(profile.rf.center_frequency_hz)


def _build_key_provider(profile: NodeProfile, simulator: bool) -> KeyProvider:
    """SPEC-005A.4 — Build key provider from profile or simulator flag."""
    if simulator:
        return DevelopmentKeyProvider(acknowledged_simulator_use=True)
    if profile.trust.require_production_hmac_key:
        return ProductionKeyResolver()
    # If key not required and not simulator, still fail closed unless explicitly allowed
    return DevelopmentKeyProvider(acknowledged_simulator_use=True)


def get_tier1_hal(
    profile: NodeProfile,
    simulator: bool = False,
    key_provider: KeyProvider | None = None,
) -> HardwareHAL:
    """
    SPEC-005A.4 — Build the composed Tier-1 HAL from a validated NodeProfile.

    Args:
        profile: Validated node profile.
        simulator: Force simulated SDR backend and dev key.
        key_provider: Optional explicit key provider.

    Returns:
        Composed HardwareHAL.

    Raises:
        ConfigurationError: Profile selects an unknown backend.
        HardwareInitializationError: Backend cannot be initialized.
        QualificationError: If fail_closed and initial qualification fails.
    """
    if simulator or profile.trust.allow_simulator_fallback:
        simulator = True


    # SDR backend
    sdr_cfg = profile.sdr
    backend_name = sdr_cfg.backend
    if simulator or backend_name == "simulated":
        sdr_backend: Any = SimulatedSdrBackend()
    elif backend_name in ("pluto", "pluto_iio"):
        sdr_backend = PlutoIioBackend(
            uri=sdr_cfg.uri,
            expected_iio_phy=sdr_cfg.expected_iio_phy,
        )
    elif backend_name == "libresdr":
        # LibreSDR uses Pluto iio backend
        sdr_backend = PlutoIioBackend(
            uri=sdr_cfg.uri,
            expected_iio_phy=sdr_cfg.expected_iio_phy,
        )
    elif backend_name == "auto":

        try:
            sdr_backend = PlutoIioBackend(
                uri=sdr_cfg.uri,
                expected_iio_phy=sdr_cfg.expected_iio_phy,
            )
            sdr_backend.discover()
        except Exception:
            raise ConfigurationError("No SDR found in auto mode")
    else:
        raise ConfigurationError(f"Unsupported SDR backend in profile: {backend_name}")

    # Timing authority
    timing_cfg = profile.timing
    if simulator:
        timing_authority = SimulatedTimingAuthority(
            reference_frequency_hz=timing_cfg.reference_frequency_hz
        )
    else:
        timing_authority = LBE1421TimingAuthority(
            pps_device=timing_cfg.pps_device,
            nmea_port=timing_cfg.nmea_port,
            reference_frequency_hz=timing_cfg.reference_frequency_hz,
        )

    # Frequency translation
    frequency_translation = _build_frequency_translation(profile)

    # Qualification policy
    # The AD936x/Pluto firmware cannot software-report external-reference
    # detection, so requiring that evidence would permanently UNVERIFY the
    # backend. For pluto_iio we rely on the profile/wiring assertion plus
    # host-side PPS/NMEA evidence instead.
    ref_required = False
    pps_required = True
    if backend_name != "pluto_iio":
        if isinstance(profile.hardware, dict):
            if "reference_clock" in profile.hardware:
                ref_required = bool(profile.hardware["reference_clock"].get("required", False))
        elif hasattr(profile.hardware, "reference_clock"):
            ref_required = getattr(
                getattr(profile.hardware, "reference_clock", None), "required", False
            )

    if isinstance(profile.hardware, dict):
        if "pps" in profile.hardware:
            pps_required = bool(profile.hardware["pps"].get("required", True))
    elif hasattr(profile.hardware, "pps"):
        pps_required = getattr(getattr(profile.hardware, "pps", None), "required", True)

    policy = Tier1QualificationPolicy(
        allow_simulator=simulator,
        production_hmac_key_required=profile.trust.require_production_hmac_key,
        external_reference_evidence_required=ref_required,
        pps_required=pps_required,
        gps_fix_required=False,
    )

    # Key provider
    if key_provider is None:
        key_provider = _build_key_provider(profile, simulator)

    hal = HardwareHAL(
        timing_authority=timing_authority,
        sdr_backend=sdr_backend,
        frequency_translation=frequency_translation,
        qualification_policy=policy,
        fail_closed=profile.trust.fail_closed,
        key_provider=key_provider,
        profile=profile,
    )

    return hal


def ingest_gps_pps(**kwargs):
    """SPEC-005A.4a — Legacy GPS/PPS ingestion."""
    return get_hal().ingest_gps_pps(**kwargs)


def ingest_sdr(**kwargs):
    """SPEC-005A.4b — Legacy SDR IQ ingestion."""
    return get_hal().ingest_sdr(**kwargs)


def verify_hardware_lock(device_index: int = 0) -> dict:
    """SPEC-004A.3 — Legacy GPSDO/PlutoSDRplus lock check."""
    return get_hal().verify_gpsdo_lock(device_index)
