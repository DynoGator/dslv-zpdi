"""
SPEC-013 - Structured JSON Logging Configuration
Replaces unstructured print() with journald-ingestible JSON logs.
"""

import logging
import sys
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger


class _DSLVEncoder(jsonlogger.JsonFormatter):
    """Custom JSON formatter injecting node_id, spec_id, and utc timestamp."""

    def __init__(self, node_id: str = "UNKNOWN", fmt: Optional[str] = None, *args: Any, **kwargs: Any):
        self.node_id = node_id
        super().__init__(fmt, *args, **kwargs)

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record.setdefault("timestamp_utc", self.formatTime(record))
        log_record.setdefault("level", record.levelname)
        log_record.setdefault("logger", record.name)
        log_record.setdefault("node_id", self.node_id)
        log_record.setdefault("spec_id", getattr(record, "spec_id", "N/A"))
        log_record.setdefault("context", getattr(record, "context", {}))


def setup_logging(
    level: int = logging.INFO,
    node_id: str = "UNKNOWN",
    log_format: str = "json",
) -> logging.Logger:
    """SPEC-013.1 - Configure root logger for DSLV-ZPDI."""
    root = logging.getLogger("dslv-zpdi")
    root.setLevel(level)

    for handler in root.handlers[:]:
        root.removeHandler(handler)

    if log_format == "json":
        formatter: logging.Formatter = _DSLVEncoder(
            node_id=node_id,
            fmt="%(timestamp_utc)s %(level)s %(name)s %(message)s",
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root.addHandler(handler)

    logging.captureWarnings(True)

    return root


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger under dslv-zpdi."""
    return logging.getLogger(f"dslv-zpdi.{name}")
