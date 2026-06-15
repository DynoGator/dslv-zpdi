"""
SPEC-005A.TIMING-LBE1421 — Leo Bodnar LBE-1421 dual-output GPSDO timing authority.

Combines kernel PPS edges, NMEA GGA fixes, and chronyd discipline into a single
structured TimingAttestation. Each evidence dimension remains available; the
convenience summary Booleans are derived, not fabricated.
"""

from __future__ import annotations

import time
from typing import Any

from dslv_zpdi.layer1_ingestion.timing.attestation import TimingAttestation
from dslv_zpdi.layer1_ingestion.timing.base import TimingAuthority
from dslv_zpdi.layer1_ingestion.timing.chrony_monitor import ChronyMonitor
from dslv_zpdi.layer1_ingestion.timing.nmea_stream import NmeaStream
from dslv_zpdi.layer1_ingestion.timing.pps_listener import PpsListener


class LBE1421TimingAuthority(TimingAuthority):
    """
    SPEC-005A.TIMING-LBE1421 — Timing authority for the Leo Bodnar LBE-1421 GPSDO.

    Args:
        pps_device: Host PPS character device (default /dev/pps0).
        nmea_port: GPSDO USB-C virtual serial port (default /dev/ttyACM0).
        pps_degraded_ns: PPS RMS jitter threshold for DEGRADED state.
        pps_kill_ns: PPS RMS jitter threshold for FAIL state.
        max_fix_age_s: GPS fix older than this is stale.
        reference_frequency_hz: Expected external reference frequency.
    """

    def __init__(
        self,
        pps_device: str = "/dev/pps0",
        nmea_port: str = "/dev/ttyACM0",
        pps_degraded_ns: float = 1_000.0,
        pps_kill_ns: float = 10_000.0,
        max_fix_age_s: float = 10.0,
        reference_frequency_hz: int = 10_000_000,
    ) -> None:
        self.reference_frequency_hz = reference_frequency_hz
        self.pps_degraded_ns = pps_degraded_ns
        self.pps_kill_ns = pps_kill_ns
        self.max_fix_age_s = max_fix_age_s

        self._pps = PpsListener(device=pps_device)
        self._pps.start()
        self._nmea = NmeaStream(port=nmea_port)
        self._nmea.start()
        self._chrony = ChronyMonitor()

    def attest(self) -> TimingAttestation:
        """SPEC-005A.TIMING-LBE1421 — Produce a structured timing attestation."""
        pps_snap = self._pps.snapshot()
        nmea = self._nmea.latest()
        chrony = self._chrony.snapshot()

        pps_present = pps_snap["history_len"] >= 2
        pps_jitter = pps_snap["rms_jitter_ns"] if pps_present else float("inf")

        fix_age = time.time() - nmea.get("ts", 0.0)
        gps_fix_valid = bool(nmea.get("gps_fix"))
        if gps_fix_valid and fix_age > self.max_fix_age_s:
            gps_fix_valid = False

        warnings: list[str] = []
        if not pps_present:
            warnings.append("PPS history has fewer than 2 samples")
        if pps_present and pps_jitter > self.pps_degraded_ns:
            warnings.append(
                f"PPS RMS jitter {pps_jitter:.0f} ns exceeds {self.pps_degraded_ns:.0f} ns target"
            )
        if not nmea.get("gps_fix"):
            warnings.append("No GPS fix")
        elif fix_age > self.max_fix_age_s:
            warnings.append(f"GPS fix is {fix_age:.0f} s stale")
        if not chrony.available:
            warnings.append("chronyc tracking unavailable")
        elif not chrony.reference_id:
            warnings.append("chrony has no reference ID")

        # The GPSDO produces the frequency reference and PPS; we cannot prove
        # the SDR consumed either without SDR-specific evidence.
        chrony_sync = self._chrony.synchronized()
        frequency_disciplined = (
            pps_present and pps_jitter <= self.pps_kill_ns and gps_fix_valid and chrony_sync
        )
        utc_epoch_disciplined = pps_present and gps_fix_valid and chrony_sync

        evidence: dict[str, Any] = {
            "pps_snapshot": pps_snap,
            "nmea_fix": nmea,
            "chrony_snapshot": chrony.summary(),
            "pps_degraded_ns": self.pps_degraded_ns,
            "pps_kill_ns": self.pps_kill_ns,
            "max_fix_age_s": self.max_fix_age_s,
        }

        return TimingAttestation(
            gps_fix_valid=gps_fix_valid,
            gps_fix_age_seconds=fix_age,
            satellites_used=int(nmea.get("satellites_used", 0)),
            hdop=float(nmea.get("hdop", 99.9)) if nmea.get("hdop") is not None else None,
            pps_present=pps_present,
            pps_history_samples=pps_snap["history_len"],
            pps_rms_jitter_ns=pps_jitter if pps_present else float("inf"),
            chrony_synchronized=chrony_sync,
            chrony_reference_id=chrony.reference_id,
            chrony_system_offset_ns=chrony.system_offset_ns,
            external_reference_configured=True,  # LBE-1421 is the reference source
            external_reference_detected=None,  # host cannot detect output power
            reference_frequency_hz=self.reference_frequency_hz,
            baseband_pll_locked=None,
            rx_rf_pll_locked=None,
            tx_rf_pll_locked=None,
            frequency_disciplined=frequency_disciplined,
            utc_epoch_disciplined=utc_epoch_disciplined,
            sample_epoch_synchronized=False,  # not proven until FPGA path verified
            inter_node_sample_phase_synchronized=False,
            rf_phase_synchronized=False,
            evidence=evidence,
            warnings=tuple(warnings),
        )

    def healthy(self, degraded_ok: bool = False) -> bool:
        """
        SPEC-005A.TIMING-LBE1421 — Return True if timing meets configured threshold.

        Args:
            degraded_ok: If True, allow DEGRADED (jitter between target and kill).
        """
        att = self.attest()
        if not att.pps_present or not att.gps_fix_valid:
            return False
        if att.pps_rms_jitter_ns > self.pps_kill_ns:
            return False
        if not att.chrony_synchronized:
            return False
        if not degraded_ok and att.pps_rms_jitter_ns > self.pps_degraded_ns:
            return False
        return True

    def close(self) -> None:
        """SPEC-005A.TIMING-LBE1421 — Stop background listeners."""
        self._pps.stop()
        self._nmea.stop()
