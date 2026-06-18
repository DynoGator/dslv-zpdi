"""SPEC-005A.TIMING-SIM — Hardware-free timing authority for simulator runs."""

from __future__ import annotations

from dslv_zpdi.layer1_ingestion.timing.attestation import TimingAttestation
from dslv_zpdi.layer1_ingestion.timing.base import TimingAuthority


class SimulatedTimingAuthority(TimingAuthority):
    """
    SPEC-005A.TIMING-SIM — Deterministic timing evidence for CI and development.

    This authority is selected only by explicit simulator mode. It prevents
    hardware-free runs from opening PPS or NMEA devices while still making every
    simulated evidence dimension visible to downstream qualification logic.
    """

    def __init__(
        self,
        reference_frequency_hz: int = 10_000_000,
        pps_rms_jitter_ns: float = 100.0,
    ) -> None:
        self.reference_frequency_hz = reference_frequency_hz
        self.pps_rms_jitter_ns = pps_rms_jitter_ns

    def attest(self) -> TimingAttestation:
        """SPEC-005A.TIMING-SIM — Return explicit simulated timing evidence."""
        return TimingAttestation(
            gps_fix_valid=True,
            gps_fix_age_seconds=0.0,
            satellites_used=12,
            hdop=0.8,
            pps_present=True,
            pps_history_samples=16,
            pps_rms_jitter_ns=self.pps_rms_jitter_ns,
            chrony_synchronized=True,
            chrony_reference_id="SIM",
            chrony_system_offset_ns=0.0,
            external_reference_configured=True,
            external_reference_detected=True,
            reference_frequency_hz=self.reference_frequency_hz,
            baseband_pll_locked=True,
            rx_rf_pll_locked=True,
            tx_rf_pll_locked=None,
            frequency_disciplined=True,
            utc_epoch_disciplined=True,
            sample_epoch_synchronized=True,
            inter_node_sample_phase_synchronized=False,
            rf_phase_synchronized=False,
            evidence={
                "simulated": True,
                "pps_snapshot": {
                    "history_len": 16,
                    "history": [],
                    "rms_jitter_ns": self.pps_rms_jitter_ns,
                    "last_edge_mono_ns": 0,
                },
                "nmea_fix": {
                    "gps_fix": True,
                    "fix_quality": 1,
                    "satellites_used": 12,
                    "hdop": 0.8,
                    "utc_time": "000000.00",
                    "ts": 0.0,
                },
                "chrony_snapshot": {
                    "available": True,
                    "reference_id": "SIM",
                    "system_offset_ns": 0.0,
                },
            },
            warnings=("Simulated timing authority: not field evidence",),
        )

    def healthy(self, degraded_ok: bool = False) -> bool:
        """SPEC-005A.TIMING-SIM — Simulator timing is healthy by explicit selection."""
        _ = degraded_ok
        return True

    def close(self) -> None:
        """SPEC-005A.TIMING-SIM — No hardware resources are opened."""
        return
