"""Immutable JSONL audit logging for the C2 control plane."""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .protocol import CommandEnvelope


# SPEC-022
class AuditLogger:
    """Thread-safe append-only audit logger."""

    def __init__(self, path: str | Path, *, max_bytes: int = 100 * 1024 * 1024) -> None:
        self.path = Path(path)
        self.max_bytes = max_bytes
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _rotate_if_needed(self) -> None:
        if not self.path.exists():
            return
        if self.path.stat().st_size >= self.max_bytes:
            backup = self.path.with_suffix(f".jsonl.{datetime.now(timezone.utc):%Y%m%d%H%M%S}")
            self.path.rename(backup)

    def log(
        self,
        *,
        envelope: CommandEnvelope,
        client_ip: str | None = None,
        user_agent: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> str:
        """Append an audit record and return the audit log ID."""
        audit_log_id = str(uuid.uuid4())
        record = {
            "audit_log_id": audit_log_id,
            "command_id": envelope.command_id,
            "idempotency_key": envelope.idempotency_key,
            "issuer_node_id": envelope.issuer_node_id,
            "target_node_id": envelope.target_node_id,
            "capability": envelope.capability,
            "parameters": envelope.parameters,
            "state": envelope.state.value,
            "result": envelope.result,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        if extra:
            record.update(extra)

        with self._lock:
            self._rotate_if_needed()
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        return audit_log_id
