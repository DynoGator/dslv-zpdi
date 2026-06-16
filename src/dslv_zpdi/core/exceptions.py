"""SPEC-005A | Canonical exceptions for DSLV-ZPDI."""


class DSLVZPDIError(Exception):
    """SPEC-005A — Base exception for all DSLV-ZPDI errors."""


class HardwareInitializationError(DSLVZPDIError):
    """SPEC-005A — Raised when hardware HAL fails to initialize."""


class ClockVerificationError(DSLVZPDIError):
    """SPEC-005A — Raised when external clock verification fails."""


class DriverUnavailableError(DSLVZPDIError):
    """SPEC-005A — Raised when required SDR driver is not available."""


class SecurityError(DSLVZPDIError):
    """SPEC-018 — Raised when cryptographic provenance or key handling fails."""


class ConfigurationError(DSLVZPDIError):
    """SPEC-004A — Raised when a hardware or node profile is invalid."""


class QualificationError(DSLVZPDIError):
    """SPEC-004A — Raised when a candidate SDR fails Tier-1 qualification."""


class TimingError(DSLVZPDIError):
    """SPEC-005A — Raised when timing attestation cannot be satisfied."""
