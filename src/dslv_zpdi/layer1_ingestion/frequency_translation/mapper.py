"""
SPEC-004A.FREQ-MAP — Frequency mapping between native IF and translated RF.
"""

from __future__ import annotations

from dslv_zpdi.layer1_ingestion.frequency_translation.model import FrequencyTranslationStage


class FrequencyMapper:
    """
    SPEC-004A.FREQ-MAP — Map between native SDR IF and RF via a converter stage.

    The raw IQ samples remain at the native IF. Translated frequency axes are
    derived metadata stored alongside the native metadata.
    """

    @staticmethod
    def translate(
        native_if_center_hz: int,
        lo_frequency_hz: int,
        sideband_sign: int,
    ) -> int:
        """
        SPEC-004A.FREQ-MAP — Compute RF frequency from IF and LO.

        rf = lo + sideband_sign * if
        """
        if sideband_sign not in (-1, 1):
            raise ValueError("sideband_sign must be -1 or +1")
        return lo_frequency_hz + sideband_sign * native_if_center_hz

    @staticmethod
    def from_stage(stage: FrequencyTranslationStage) -> int:
        """SPEC-004A.FREQ-MAP — Return translated RF center from a stage."""
        return stage.translated_rf_center_hz

    @staticmethod
    def build_direct_rf_stage(center_frequency_hz: int) -> FrequencyTranslationStage:
        """
        SPEC-004A.FREQ-MAP — Build a no-converter direct-RF stage.

        Used when the SDR samples the RF band directly.
        """
        return FrequencyTranslationStage(
            native_if_center_hz=center_frequency_hz,
            lo_frequency_hz=0,
            lo_source="direct_rf",
            sideband_sign=1,
            converter_model="direct_rf",
            converter_serial="N/A",
            calibration_manifest_sha256="",
        )
