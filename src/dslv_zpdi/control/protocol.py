"""Canonical implementation of the DSLV-ZPDI C2 command envelope and lifecycle.

See specs/SPEC-C2-001.md for the protocol definition.
"""

from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

PROTOCOL_NAME = "dslv-zpdi-c2/1"
MAX_CLOCK_SKEW_SECONDS = 5
MAX_COMMAND_TTL_SECONDS = 300
MAX_IDEMPOTENCY_WINDOW_SECONDS = 86400
MIN_NONCE_BYTES = 16


# SPEC-022
class ProtocolError(Exception):
    """Base class for protocol-level errors."""


# SPEC-022
class ValidationError(ProtocolError):
    """Envelope or parameter validation failed."""


# SPEC-022
class CommandState(str, Enum):
    """Command lifecycle states."""

    REQUESTED = "REQUESTED"
    AUTHENTICATED = "AUTHENTICATED"
    ACCEPTED = "ACCEPTED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    UNAUTHORIZED = "UNAUTHORIZED"


# SPEC-022
class CapabilityRegistry:
    """Capability registry and parameter schemas.

    Each capability maps to a validator function that raises ValidationError
    when parameters are malformed or out of range.
    """

    CAPABILITIES = {
        "node.status.read",
        "pipeline.status.read",
        "pipeline.start",
        "pipeline.stop",
        "pipeline.rotate_output",
        "sdr.status.read",
        "sdr.mode.set",
        "sdr.center_frequency.set",
        "sdr.sample_rate.set",
        "sdr.gain.set",
        "baseline.reset",
        "hdf5.summary.read",
        "hdf5.segment.export",
    }

    @classmethod
    def is_valid(cls, capability: str) -> bool:
        return capability in cls.CAPABILITIES

    @classmethod
    def validate_parameters(cls, capability: str, parameters: dict[str, Any]) -> None:
        """Validate parameters for a capability."""
        if not isinstance(parameters, dict):
            raise ValidationError("parameters must be an object")

        validator = getattr(cls, f"_validate_{capability.replace('.', '_')}", None)
        if validator is None:
            return
        validator(parameters)

    @staticmethod
    def _validate_sdr_mode_set(parameters: dict[str, Any]) -> None:
        mode = parameters.get("mode")
        if mode not in {"real", "simulated", "offline"}:
            raise ValidationError("mode must be one of: real, simulated, offline")

    @staticmethod
    def _validate_sdr_center_frequency_set(parameters: dict[str, Any]) -> None:
        hz = parameters.get("hz")
        if not isinstance(hz, int) or not (1_000_000 <= hz <= 6_000_000_000):
            raise ValidationError("hz must be an integer between 1 MHz and 6 GHz")

    @staticmethod
    def _validate_sdr_sample_rate_set(parameters: dict[str, Any]) -> None:
        sr = parameters.get("sample_rate_hz")
        if not isinstance(sr, int) or sr <= 0:
            raise ValidationError("sample_rate_hz must be a positive integer")

    @staticmethod
    def _validate_sdr_gain_set(parameters: dict[str, Any]) -> None:
        gain = parameters.get("gain_db")
        if not isinstance(gain, (int, float)):
            raise ValidationError("gain_db must be a number")

    @staticmethod
    def _validate_baseline_reset(parameters: dict[str, Any]) -> None:
        mode = parameters.get("mode")
        if mode not in {"soft", "hard"}:
            raise ValidationError("mode must be one of: soft, hard")


@dataclass
# SPEC-022
class CommandEnvelope:
    """Validated C2 command envelope."""

    command_id: str
    idempotency_key: str
    issuer_node_id: str
    target_node_id: str
    capability: str
    issued_at: datetime
    expires_at: datetime
    nonce: str
    parameters: dict[str, Any]
    signature: str | None = None
    state: CommandState = CommandState.REQUESTED
    result: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        local_node_id: str,
        seen_idempotency_keys: set[str] | None = None,
        now: datetime | None = None,
    ) -> CommandEnvelope:
        """Validate a raw dict and return a CommandEnvelope.

        Raises:
            ValidationError: if the envelope is malformed, expired, or unauthorized.
        """
        seen_idempotency_keys = seen_idempotency_keys or set()
        now = now or datetime.now(timezone.utc)

        if data.get("protocol") != PROTOCOL_NAME:
            raise ValidationError(f"protocol must be {PROTOCOL_NAME}")

        command_id = cls._require_uuid(data, "command_id")
        idempotency_key = cls._require_uuid(data, "idempotency_key")
        issuer_node_id = cls._require_string(data, "issuer_node_id")
        target_node_id = cls._require_string(data, "target_node_id")
        capability = cls._require_string(data, "capability")
        issued_at = cls._require_iso(data, "issued_at")
        expires_at = cls._require_iso(data, "expires_at")
        nonce = cls._require_nonce(data, "nonce")
        parameters = data.get("parameters", {})
        signature = data.get("signature")

        if target_node_id != local_node_id and target_node_id != "*":
            raise ValidationError("target_node_id does not match this node")

        if not CapabilityRegistry.is_valid(capability):
            raise ValidationError(f"unknown capability: {capability}")

        CapabilityRegistry.validate_parameters(capability, parameters)

        if idempotency_key in seen_idempotency_keys:
            raise ValidationError("duplicate idempotency key")

        skew = (issued_at - now).total_seconds()
        if skew > MAX_CLOCK_SKEW_SECONDS:
            raise ValidationError("issued_at is in the future")

        ttl = (expires_at - issued_at).total_seconds()
        if ttl <= 0:
            raise ValidationError("expires_at must be after issued_at")
        if ttl > MAX_COMMAND_TTL_SECONDS:
            raise ValidationError("command TTL exceeds maximum")

        if expires_at < now:
            raise ValidationError("command has expired")

        return cls(
            command_id=command_id,
            idempotency_key=idempotency_key,
            issuer_node_id=issuer_node_id,
            target_node_id=target_node_id,
            capability=capability,
            issued_at=issued_at,
            expires_at=expires_at,
            nonce=nonce,
            parameters=parameters,
            signature=signature,
        )

    def is_expired(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return self.expires_at < now

    @staticmethod
    def _require_uuid(data: dict[str, Any], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str):
            raise ValidationError(f"{key} must be a string UUID")
        try:
            uuid.UUID(value, version=4)
        except ValueError as exc:
            raise ValidationError(f"{key} must be a UUID v4") from exc
        return value

    @staticmethod
    def _require_string(data: dict[str, Any], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value:
            raise ValidationError(f"{key} must be a non-empty string")
        return value

    @staticmethod
    def _require_iso(data: dict[str, Any], key: str) -> datetime:
        value = data.get(key)
        if not isinstance(value, str):
            raise ValidationError(f"{key} must be an ISO 8601 timestamp")
        # Python 3.11+ fromisoformat handles trailing Z.
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(f"{key} is not a valid ISO 8601 timestamp") from exc

    @staticmethod
    def _require_nonce(data: dict[str, Any], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str):
            raise ValidationError(f"{key} must be a base64 string")
        try:
            decoded = base64.b64decode(value, validate=True)
        except Exception as exc:
            raise ValidationError(f"{key} is not valid base64") from exc
        if len(decoded) < MIN_NONCE_BYTES:
            raise ValidationError(f"{key} must decode to at least {MIN_NONCE_BYTES} bytes")
        # Return the raw value so the canonical form is preserved in audit logs.
        return value

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "protocol": PROTOCOL_NAME,
            "command_id": self.command_id,
            "idempotency_key": self.idempotency_key,
            "issuer_node_id": self.issuer_node_id,
            "target_node_id": self.target_node_id,
            "capability": self.capability,
            "issued_at": self.issued_at.isoformat().replace("+00:00", "Z"),
            "expires_at": self.expires_at.isoformat().replace("+00:00", "Z"),
            "nonce": self.nonce,
            "parameters": self.parameters,
            "state": self.state.value,
        }
        if self.signature:
            result["signature"] = self.signature
        if self.result:
            result["result"] = self.result
        return result
