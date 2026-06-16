"""SPEC-005A | Timing authority abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod

from dslv_zpdi.layer1_ingestion.timing.attestation import TimingAttestation


class TimingAuthority(ABC):
    """
    SPEC-005A.TIMING-AUTH — Abstract source of timing evidence.

    A timing authority is independent of any SDR backend. It produces a
    structured TimingAttestation that callers must not collapse into a single
    misleading Boolean.
    """

    @abstractmethod
    def attest(self) -> TimingAttestation:
        """Return current timing evidence."""
        ...

    @abstractmethod
    def healthy(self, degraded_ok: bool = False) -> bool:
        """
        Return True if the timing authority meets the configured threshold.

        Args:
            degraded_ok: If True, allow DEGRADED states that are not FAIL.
        """
        ...

    @abstractmethod
    def close(self) -> None:
        """Release any resources (daemon threads, file handles)."""
        ...
