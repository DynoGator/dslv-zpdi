"""
SPEC-005A.HAL | Hardware Abstraction Layer Base (Rev 4.0.2)
Defines the abstract interface for all Tier 1 ingestion sources.
"""

from abc import ABC, abstractmethod

from .payload import IngestionPayload


class BaseHAL(ABC):
    """SPEC-005A.HAL — Abstract base for hardware and simulated ingestion."""

    @abstractmethod
    def ingest_gps_pps(self, **kwargs) -> IngestionPayload:
        """SPEC-005A.4a — Abstract GPS/PPS Ingestion."""

    @abstractmethod
    def ingest_sdr(self, **kwargs) -> IngestionPayload:
        """SPEC-005A.4b — Abstract SDR IQ Ingestion."""
