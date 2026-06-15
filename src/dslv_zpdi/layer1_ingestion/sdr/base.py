"""SPEC-004A | Abstract base class for SDR backends."""

from __future__ import annotations

from abc import ABC, abstractmethod

from dslv_zpdi.layer1_ingestion.sdr.capture_result import CaptureResult, SdrHealth
from dslv_zpdi.layer1_ingestion.sdr.capabilities import (
    AppliedConfiguration,
    CaptureProfile,
    SdrCapabilities,
)
from dslv_zpdi.layer1_ingestion.timing.attestation import ClockAttestation


class SdrBackend(ABC):
    """
    SPEC-004A.BACKEND — Abstract SDR backend.

    Backends are intentionally independent of timing authority. They report
    what they can prove about clocking (ClockAttestation) and expose all
    evidence dimensions separately.
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Short backend identifier."""
        ...

    @abstractmethod
    def discover(self) -> SdrCapabilities:
        """Return runtime-discovered capabilities."""
        ...

    @abstractmethod
    def configure(self, profile: CaptureProfile) -> AppliedConfiguration:
        """Apply capture profile and return settings read back from hardware."""
        ...

    @abstractmethod
    def verify_clocking(self) -> ClockAttestation:
        """Return clock attestation with unknown fields as None."""
        ...

    @abstractmethod
    def capture(self, request: CaptureProfile) -> CaptureResult:
        """Capture IQ samples according to the request."""
        ...

    @abstractmethod
    def health(self) -> SdrHealth:
        """Return current health snapshot."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Release hardware resources."""
        ...
