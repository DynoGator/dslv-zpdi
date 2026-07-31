"""Tests for the DSLV-ZPDI C2 control-plane protocol."""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from dslv_zpdi.control import (
    AuditLogger,
    CapabilityStore,
    CommandEnvelope,
    CommandState,
    ValidationError,
    authorize,
)
from dslv_zpdi.control.protocol import PROTOCOL_NAME, CapabilityRegistry

LOCAL_NODE_ID = "test-node-01"


def _nonce() -> str:
    return base64.b64encode(b"1234567890123456").decode("ascii")


def _make_envelope(
    *,
    command_id: str | None = None,
    idempotency_key: str | None = None,
    issuer_node_id: str = "pixel-control-01",
    target_node_id: str = LOCAL_NODE_ID,
    capability: str = "node.status.read",
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
    nonce: str | None = None,
    parameters: dict | None = None,
    signature: str | None = None,
    seen: set[str] | None = None,
) -> CommandEnvelope:
    now = datetime.now(timezone.utc)
    data = {
        "protocol": PROTOCOL_NAME,
        "command_id": command_id or str(uuid.uuid4()),
        "idempotency_key": idempotency_key or str(uuid.uuid4()),
        "issuer_node_id": issuer_node_id,
        "target_node_id": target_node_id,
        "capability": capability,
        "issued_at": (issued_at or now).isoformat().replace("+00:00", "Z"),
        "expires_at": (expires_at or (now + timedelta(seconds=60))).isoformat().replace(
            "+00:00", "Z"
        ),
        "nonce": nonce or _nonce(),
        "parameters": parameters or {},
    }
    if signature:
        data["signature"] = signature
    return CommandEnvelope.from_dict(data, local_node_id=LOCAL_NODE_ID, seen_idempotency_keys=seen)


def test_valid_command_accepted() -> None:
    cmd = _make_envelope(capability="node.status.read")
    assert cmd.command_id
    assert cmd.idempotency_key
    assert cmd.capability == "node.status.read"
    assert cmd.state == CommandState.REQUESTED


def test_unknown_capability_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown capability"):
        _make_envelope(capability="node.destroy")


def test_missing_protocol_rejected() -> None:
    now = datetime.now(timezone.utc)
    data = {
        "command_id": str(uuid.uuid4()),
        "idempotency_key": str(uuid.uuid4()),
        "issuer_node_id": "pixel-control-01",
        "target_node_id": LOCAL_NODE_ID,
        "capability": "node.status.read",
        "issued_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(seconds=60)).isoformat().replace("+00:00", "Z"),
        "nonce": _nonce(),
        "parameters": {},
    }
    with pytest.raises(ValidationError, match="protocol"):
        CommandEnvelope.from_dict(data, local_node_id=LOCAL_NODE_ID)


def test_expired_command_rejected() -> None:
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError, match="expired"):
        _make_envelope(issued_at=now - timedelta(seconds=10), expires_at=now - timedelta(seconds=5))


def test_ttl_too_long_rejected() -> None:
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError, match="TTL exceeds maximum"):
        _make_envelope(issued_at=now, expires_at=now + timedelta(seconds=400))


def test_future_issued_at_rejected() -> None:
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError, match="future"):
        _make_envelope(issued_at=now + timedelta(seconds=10))


def test_duplicate_idempotency_key_rejected() -> None:
    key = str(uuid.uuid4())
    _make_envelope(idempotency_key=key)
    with pytest.raises(ValidationError, match="duplicate idempotency key"):
        _make_envelope(idempotency_key=key, seen={key})


def test_invalid_target_rejected() -> None:
    with pytest.raises(ValidationError, match="target_node_id"):
        _make_envelope(target_node_id="wrong-node")


def test_broadcast_target_accepted() -> None:
    cmd = _make_envelope(target_node_id="*")
    assert cmd.target_node_id == "*"


def test_invalid_uuid_rejected() -> None:
    with pytest.raises(ValidationError, match="UUID"):
        _make_envelope(command_id="not-a-uuid")


def test_short_nonce_rejected() -> None:
    short_nonce = base64.b64encode(b"short").decode("ascii")
    with pytest.raises(ValidationError, match="at least 16 bytes"):
        _make_envelope(nonce=short_nonce)


def test_malformed_base64_nonce_rejected() -> None:
    with pytest.raises(ValidationError, match="not valid base64"):
        _make_envelope(nonce="!!!not-base64!!!")


def test_parameters_must_be_object() -> None:
    now = datetime.now(timezone.utc)
    data = {
        "protocol": PROTOCOL_NAME,
        "command_id": str(uuid.uuid4()),
        "idempotency_key": str(uuid.uuid4()),
        "issuer_node_id": "pixel-control-01",
        "target_node_id": LOCAL_NODE_ID,
        "capability": "node.status.read",
        "issued_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(seconds=60)).isoformat().replace("+00:00", "Z"),
        "nonce": _nonce(),
        "parameters": "not-a-dict",
    }
    with pytest.raises(ValidationError, match="parameters must be an object"):
        CommandEnvelope.from_dict(data, local_node_id=LOCAL_NODE_ID)


def test_sdr_frequency_validation() -> None:
    # Valid frequency.
    cmd = _make_envelope(capability="sdr.center_frequency.set", parameters={"hz": 144_390_000})
    assert cmd.parameters["hz"] == 144_390_000

    # Too low.
    with pytest.raises(ValidationError, match="1 MHz and 6 GHz"):
        _make_envelope(capability="sdr.center_frequency.set", parameters={"hz": 100_000})

    # Too high.
    with pytest.raises(ValidationError, match="1 MHz and 6 GHz"):
        _make_envelope(capability="sdr.center_frequency.set", parameters={"hz": 7_000_000_000})

    # Wrong type.
    with pytest.raises(ValidationError, match="1 MHz and 6 GHz"):
        _make_envelope(capability="sdr.center_frequency.set", parameters={"hz": "144M"})


def test_sdr_mode_validation() -> None:
    cmd = _make_envelope(capability="sdr.mode.set", parameters={"mode": "simulated"})
    assert cmd.parameters["mode"] == "simulated"

    with pytest.raises(ValidationError, match="real, simulated, offline"):
        _make_envelope(capability="sdr.mode.set", parameters={"mode": "invalid"})


def test_baseline_reset_validation() -> None:
    cmd = _make_envelope(capability="baseline.reset", parameters={"mode": "soft"})
    assert cmd.parameters["mode"] == "soft"

    with pytest.raises(ValidationError, match="soft, hard"):
        _make_envelope(capability="baseline.reset", parameters={"mode": "nuke"})


def test_capability_registry_membership() -> None:
    assert CapabilityRegistry.is_valid("node.status.read")
    assert not CapabilityRegistry.is_valid("not.a.capability")
    assert "sdr.center_frequency.set" in CapabilityRegistry.CAPABILITIES


def test_command_to_dict_round_trip() -> None:
    cmd = _make_envelope(capability="sdr.mode.set", parameters={"mode": "offline"})
    data = cmd.to_dict()
    assert data["protocol"] == PROTOCOL_NAME
    assert data["capability"] == "sdr.mode.set"
    assert data["parameters"]["mode"] == "offline"
    assert data["state"] == CommandState.REQUESTED.value


def test_is_expired() -> None:
    now = datetime.now(timezone.utc)
    cmd = _make_envelope(issued_at=now, expires_at=now + timedelta(seconds=60))
    assert not cmd.is_expired(now)
    assert cmd.is_expired(now + timedelta(seconds=120))


def test_authorize_allowed_capability() -> None:
    store = CapabilityStore()
    authorize(store, "pixel-control-01", "sdr.mode.set", "tier2-c2-master")


def test_authorize_denied_capability() -> None:
    store = CapabilityStore()
    with pytest.raises(Exception, match="not authorized"):
        authorize(store, "edge-node", "sdr.mode.set", "tier3-edge")


def test_authorize_unknown_capability_raises() -> None:
    store = CapabilityStore()
    with pytest.raises(ValidationError, match="unknown capability"):
        store.is_authorized("pixel-control-01", "not.real")


def test_audit_logger_writes_record(tmp_path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(audit_path)
    cmd = _make_envelope(capability="node.status.read")
    cmd.state = CommandState.COMPLETED
    cmd.result = {"status": "ok"}
    audit_id = logger.log(envelope=cmd, client_ip="127.0.0.1", user_agent="test")

    assert audit_id
    lines = audit_path.read_text().strip().splitlines()
    assert len(lines) == 1
    record = __import__("json").loads(lines[0])
    assert record["command_id"] == cmd.command_id
    assert record["capability"] == "node.status.read"
    assert record["state"] == "COMPLETED"
    assert record["client_ip"] == "127.0.0.1"
