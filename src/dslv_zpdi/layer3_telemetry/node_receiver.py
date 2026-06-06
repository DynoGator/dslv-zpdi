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
import time
from http import HTTPStatus

try:
    from flask import Flask, Response, jsonify, request

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

from dslv_zpdi.layer3_telemetry.hdf5_writer import HDF5Writer


# SPEC-014.1 — Node registry maintenance
def _update_node_registry(node_id: str) -> None:
    """Write/update last-seen timestamp for a node in the secondary registry."""
    reg_path = os.path.join(
        os.getenv("DSLV_SECONDARY_OUTPUT_DIR", "./output/secondary"),
        "node_registry.jsonl",
    )
    try:
        os.makedirs(os.path.dirname(reg_path), exist_ok=True)
        entries: dict = {}
        if os.path.exists(reg_path):
            with open(reg_path) as f:
                for line in f:
                    try:
                        e = json.loads(line)
                        entries[e.get("node_id", "?")] = e
                    except Exception:
                        pass
        entries[node_id] = {"node_id": node_id, "last_seen_utc": time.time()}
        with open(reg_path, "w") as f:
            for entry in entries.values():
                f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.warning("node registry update failed: %s", exc)

logger = logging.getLogger("dslv-zpdi.node-receiver")

_writer: HDF5Writer | None = None


# SPEC-014.2 — Lazy HDF5 writer singleton
def _get_writer() -> HDF5Writer:
    global _writer
    if _writer is None:
        _writer = HDF5Writer(
            output_path=os.getenv("DSLV_PRIMARY_OUTPUT_DIR", "./output/primary"),
            secondary_path=os.getenv("DSLV_SECONDARY_OUTPUT_DIR", "./output/secondary"),
        )
    return _writer


# SPEC-014.3 — Flask application factory
def create_app(writer: HDF5Writer | None = None) -> "Flask":
    if not FLASK_AVAILABLE:
        raise RuntimeError("flask is required for the node receiver (pip install flask)")

    app = Flask("dslv-zpdi-node-receiver")

    if writer is not None:
        global _writer
        _writer = writer

    # ── Mobile-node telemetry (Pixel 9 Pro XL / any swarm node) ─────────────

    @app.route("/api/v1/ingest", methods=["POST"])
    # SPEC-014.4 — Swarm node telemetry ingestion endpoint
    def ingest_node() -> Response:
        """Accept a JSON telemetry payload from any swarm node."""
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

    _RADONEYE_REQUIRED_FIELDS = {"source", "radon_bq_m3", "timestamp_utc", "unit_id"}

    @app.route("/api/v1/ingest/radoneye", methods=["POST"])
    # SPEC-014.5 — RadonEye Pro staging endpoint (secondary stream only)
    def ingest_radoneye() -> Response:
        """[PLACEHOLDER] Accept EcoSense RadonEye Pro sensor readings."""
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
            float(payload.get("radon_bq_m3", 0)),
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
    # SPEC-014.6 — Service health endpoint
    def health() -> Response:
        stats = _get_writer().get_stats() if _writer else {}
        return jsonify({"status": "ok", "stats": stats}), HTTPStatus.OK

    return app


# SPEC-014.7 — CLI entry point
def main() -> None:
    port = int(os.getenv("DSLV_RECEIVER_PORT", "5775"))
    app = create_app()
    logger.info("DSLV-ZPDI node receiver starting on 0.0.0.0:%d", port)
    app.run(host="0.0.0.0", port=port, threaded=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
