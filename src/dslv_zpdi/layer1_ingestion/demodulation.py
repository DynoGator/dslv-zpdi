"""
SPEC-023.1 — Demodulation Engine for Signal Demodulation into Audio, Data, Video, and Telemetry.
Includes intelligent presets for various demodulation modes (AM, FM, LSB, USB, CW, FSK, PSK, QAM, etc.).
"""

from typing import Any

import numpy as np


class DemodulationPreset:
    """SPEC-023.1 — Value holder for a demodulation preset (name, category, rates, params)."""

    def __init__(self, name: str, category: str, sample_rate_hz: int, bandwidth_hz: int, params: dict[str, Any]):
        self.name = name
        self.category = category  # "audio", "data", "video", "telemetry"
        self.sample_rate_hz = sample_rate_hz
        self.bandwidth_hz = bandwidth_hz
        self.params = params


class Demodulator:
    """SPEC-023.1 — Preset registry and mode selector; DSP chain is a staged integration hook."""

    PRESETS = {
        "AM_AUDIO": DemodulationPreset("AM", "audio", 48000, 10000, {"squelch": -60.0}),
        "NFM_AUDIO": DemodulationPreset("NFM", "audio", 48000, 12500, {"squelch": -60.0, "deemphasis": 75e-6}),
        "WFM_AUDIO": DemodulationPreset("WFM", "audio", 192000, 200000, {"squelch": -60.0, "deemphasis": 50e-6}),
        "LSB_AUDIO": DemodulationPreset("LSB", "audio", 48000, 3000, {"squelch": -70.0, "bfo": -1500}),
        "USB_AUDIO": DemodulationPreset("USB", "audio", 48000, 3000, {"squelch": -70.0, "bfo": 1500}),
        "CW_AUDIO": DemodulationPreset("CW", "audio", 48000, 500, {"squelch": -80.0, "bfo": 700}),
        "APRS_DATA": DemodulationPreset("AFSK1200", "data", 48000, 15000, {"baud": 1200, "mark": 1200, "space": 2200}),
        "BPSK31_DATA": DemodulationPreset("BPSK", "data", 8000, 3000, {"baud": 31.25}),
        "ATV_VIDEO": DemodulationPreset("AM_VIDEO", "video", 6000000, 6000000, {"sync_detect": True}),
        "QAM_TELEMETRY": DemodulationPreset("QAM16", "telemetry", 1000000, 1000000, {"constellation": 16}),
    }

    def __init__(self):
        self.active_mode: str | None = None
        self.current_preset: DemodulationPreset | None = None

    def set_mode(self, mode_key: str):
        if mode_key not in self.PRESETS:
            raise ValueError(f"Unknown demodulation mode: {mode_key}")
        self.active_mode = mode_key
        self.current_preset = self.PRESETS[mode_key]

    def process(self, iq_samples: np.ndarray) -> dict[str, Any]:
        """
        Hook for processing IQ samples into audio, video, data, or telemetry.
        """
        if not self.active_mode or not self.current_preset:
            return {"status": "inactive", "output": None}

        # TODO: Implement actual DSP logic for demodulation based on self.current_preset
        # Currently acts as an integration hook and stub for future DSP pipelines.
        output_data = np.zeros(len(iq_samples), dtype=np.float32)

        return {
            "status": "active",
            "mode": self.active_mode,
            "category": self.current_preset.category,
            "output": output_data,
            "metadata": self.current_preset.params
        }
