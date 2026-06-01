"""
SPEC-014 | Trust Tier: Swarm Data Ingestion
Layer 3 HTTP receiver — accepts telemetry POSTs from mobile swarm nodes
(Pixel 9 Pro XL / GrapheneOS) and third-party sensors.

Runs as a standalone Flask micro-service on port 5775 (configurable via
DSLV_RECEIVER_PORT env var).  Each POST body must be a JSON payload matching
the standard dslv-zpdi Payload schema.  Accepted packets are forwarded to the
local HDF5Writer pipeline.

RadonEye Pro integration path
──────────────────────────────
POST /api/v1/ingest/radoneye with a JSON body:
  {
    "source": "EcoSense_RadonEye_Pro",
    "radon_bq_m3": <float>,
    "timestamp_utc": <unix-float>,
    "unit_id": "<serial>",
    ...arbitrary sensor fields...
  }
The endpoint is wired but stubbed — it validates the schema and writes to the
secondary (quarantine) JSONL stream.  Full primary-stream promotion is deferred
pending SPEC-015 (RadonEye calibration baseline specification).
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from http import HTTPStatus

try:
    from flask import Flask, Response, jsonify, request

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

from dslv_zpdi.layer3_telemetry.hdf5_writer import HDF5Writer

logger = logging.getLogger("dslv-zpdi.node-receiver")

# SPEC-014 — Reject oversized request bodies before they are buffered into
# memory. Swarm telemetry packets are small; anything larger is malformed or
# hostile and must not be allowed to exhaust receiver memory.
MAX_CONTENT_LENGTH_BYTES = 1 * 1024 * 1024  # 1 MiB

# SPEC-015 — Minimum schema a RadonEye Pro packet must satisfy before staging.
_RADONEYE_REQUIRED_FIELDS = {"source", "radon_bq_m3", "timestamp_utc", "unit_id"}

_writer: HDF5Writer | None = None
_registry_lock = threading.Lock()


def _update_node_registry(node_id: str) -> None:
    """SPEC-014 — Write last-seen metadata for a swarm node.

    Serialized through ``_registry_lock`` so concurrent POSTs handled by the
    threaded Flask server cannot interleave the read-modify-write and corrupt
    ``node_registry.jsonl``.
    """
    reg_path = os.path.join(
        os.getenv("DSLV_SECONDARY_OUTPUT_DIR", "./output/secondary"),
        "node_registry.jsonl",
    )
    try:
        with _registry_lock:
            os.makedirs(os.path.dirname(reg_path), exist_ok=True)
            entries: dict = {}
            if os.path.exists(reg_path):
                with open(reg_path, encoding="utf-8") as f:
                    for line in f:
                        try:
                            e = json.loads(line)
                            entries[e.get("node_id", "?")] = e
                        except json.JSONDecodeError:
                            continue
            entries[node_id] = {"node_id": node_id, "last_seen_utc": time.time()}
            tmp_path = reg_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                for entry in entries.values():
                    f.write(json.dumps(entry) + "\n")
            os.replace(tmp_path, reg_path)
    except OSError as exc:
        logger.warning("node registry update failed: %s", exc)


def _get_writer() -> HDF5Writer:
    """SPEC-014 — Lazily construct the telemetry writer for node packets."""
    global _writer
    if _writer is None:
        _writer = HDF5Writer(
            output_path=os.getenv("DSLV_PRIMARY_OUTPUT_DIR", "./output/primary"),
            secondary_path=os.getenv("DSLV_SECONDARY_OUTPUT_DIR", "./output/secondary"),
        )
    return _writer


def create_app(writer: HDF5Writer | None = None) -> Flask:
    """SPEC-014 — Create the Flask receiver for swarm telemetry ingestion."""
    if not FLASK_AVAILABLE:
        raise RuntimeError("flask is required for the node receiver (pip install flask)")

    app = Flask("dslv-zpdi-node-receiver")
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH_BYTES

    if writer is not None:
        global _writer
        _writer = writer

    # ── Mobile-node telemetry (Pixel 9 Pro XL / any swarm node) ─────────────

    @app.route("/api/v1/ingest", methods=["POST"])
    def ingest_node() -> Response:
        """SPEC-014 — Accept a JSON telemetry payload from any swarm node."""
        raw = request.get_data(as_text=True)
        if not raw:
            return jsonify({"error": "empty body"}), HTTPStatus.BAD_REQUEST

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            return jsonify({"error": f"invalid JSON: {exc}"}), HTTPStatus.BAD_REQUEST

        # Stamp source IP if node_id is missing
        if "node_id" not in payload:
            payload["node_id"] = request.remote_addr or "UNKNOWN"

        # Ensure timestamp
        payload.setdefault("timestamp_utc", time.time())

        node_id = payload["node_id"]
        decision = _get_writer().ingest(json.dumps(payload))

        # Update node registry so the web dashboard can track last-seen time.
        _update_node_registry(node_id)

        logger.info(
            "INGEST node=%s stream=%s reason=%s",
            node_id,
            decision.stream,
            decision.reason,
        )
        return jsonify({"stream": decision.stream, "reason": decision.reason}), HTTPStatus.OK

    # ── RadonEye Pro placeholder ─────────────────────────────────────────────
    # SPEC-015 PLACEHOLDER — full primary-stream promotion pending calibration
    # baseline specification. For now, validated packets go to the secondary
    # (quarantine) JSONL stream only.

    @app.route("/api/v1/ingest/radoneye", methods=["POST"])
    def ingest_radoneye() -> Response:
        """SPEC-015 — Stage EcoSense RadonEye Pro sensor readings."""
        raw = request.get_data(as_text=True)
        if not raw:
            return jsonify({"error": "empty body"}), HTTPStatus.BAD_REQUEST

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            return jsonify({"error": f"invalid JSON: {exc}"}), HTTPStatus.BAD_REQUEST

        missing = _RADONEYE_REQUIRED_FIELDS - set(payload.keys())
        if missing:
            return (
                jsonify({"error": f"missing required fields: {sorted(missing)}"}),
                HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        # SPEC-015 — Validate radon reading is numeric before it is staged so a
        # malformed sensor value yields a clean 422 rather than a later 500.
        try:
            radon_value = float(payload["radon_bq_m3"])
        except (TypeError, ValueError):
            return (
                jsonify({"error": "radon_bq_m3 must be numeric"}),
                HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        # Route to secondary stream only — SPEC-015 not yet ratified.
        quarantine_path = (
            os.path.join(
                os.getenv("DSLV_SECONDARY_OUTPUT_DIR", "./output/secondary"),
                "radoneye_staging.jsonl",
            )
        )
        entry = {
            "received_utc": time.time(),
            "source": "radoneye_placeholder",
            "spec_status": "SPEC-015-PENDING",
            **payload,
        }
        try:
            with open(quarantine_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
        except OSError as exc:
            logger.error("RadonEye staging write failed: %s", exc)
            return jsonify({"error": "storage failure"}), HTTPStatus.INTERNAL_SERVER_ERROR

        logger.info(
            "RADONEYE STAGING: unit=%s radon=%.2f Bq/m³",
            payload.get("unit_id"),
            radon_value,
        )
        return (
            jsonify(
                {
                    "stream": "secondary",
                    "reason": "SPEC-015-PENDING",
                    "note": "RadonEye ingestion staged; primary promotion pending SPEC-015 ratification.",
                }
            ),
            HTTPStatus.ACCEPTED,
        )

    # ── Health check ─────────────────────────────────────────────────────────

    @app.route("/api/v1/health", methods=["GET"])
    def health() -> Response:
        """SPEC-014 — Report node receiver health and writer statistics."""
        stats = _get_writer().get_stats() if _writer else {}
        return jsonify({"status": "ok", "stats": stats}), HTTPStatus.OK

    return app


def main() -> None:
    """SPEC-014 — Run the node receiver service entrypoint."""
    port = int(os.getenv("DSLV_RECEIVER_PORT", "5775"))
    app = create_app()
    logger.info("DSLV-ZPDI node receiver starting on 0.0.0.0:%d", port)
    app.run(host="0.0.0.0", port=port, threaded=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
