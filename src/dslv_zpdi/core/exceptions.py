"""SPEC-005A | Canonical exceptions for DSLV-ZPDI."""


class DSLVZPDIError(Exception):
    """SPEC-005A — Base exception for all DSLV-ZPDI errors."""


class HardwareInitializationError(DSLVZPDIError):
    """SPEC-005A — Raised when hardware HAL fails to initialize."""


class ClockVerificationError(DSLVZPDIError):
    """SPEC-005A — Raised when external clock verification fails."""


class DriverUnavailableError(DSLVZPDIError):
    """SPEC-005A — Raised when required SDR driver is not available."""
