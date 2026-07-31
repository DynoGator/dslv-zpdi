"""DSLV-ZPDI Node Control Plane package.

Implements the C2 protocol, authorization, audit logging, and command dispatch
for the optional Pixel 9 Pro XL control-node feature.
"""

from .audit import AuditLogger
from .authorization import CapabilityStore, authorize
from .protocol import (
    CapabilityRegistry,
    CommandEnvelope,
    CommandState,
    ProtocolError,
    ValidationError,
)

__all__ = [
    "CapabilityRegistry",
    "CapabilityStore",
    "CommandEnvelope",
    "CommandState",
    "ProtocolError",
    "ValidationError",
    "authorize",
    "AuditLogger",
]
