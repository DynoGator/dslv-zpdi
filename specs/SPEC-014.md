# SPEC-014 — Node Receiver API (Swarm Data Ingestion)

**Status:** ACTIVE
**Trust Tier:** Swarm Data Ingestion
**Layer:** Layer 3 Telemetry

## Overview

Flask-based HTTP micro-service that accepts JSON telemetry POSTs from Tier 2 swarm nodes (Pixel 9 Pro XL / GrapheneOS) and third-party sensors. Runs on port 5775 by default. Each POST body must match the standard DSLV-ZPDI Payload schema. Accepted packets are forwarded to the local HDF5Writer pipeline.

## Endpoints

### POST /api/v1/ingest
**SPEC-014.4** — Accept a JSON telemetry payload from any swarm node.

### POST /api/v1/ingest/radoneye
**SPEC-014.5** — EcoSense RadonEye Pro staging endpoint. Validates schema and writes to the secondary (quarantine) JSONL stream only. Primary-stream promotion requires SPEC-015 ratification.

### GET /api/v1/health
**SPEC-014.6** — Service health check + HDF5 writer statistics.

## Internal Functions

### _update_node_registry
**SPEC-014.1** — Maintains a JSONL registry of last-seen timestamps per node_id for dashboard tracking.

### _get_writer
**SPEC-014.2** — Lazy singleton factory for HDF5Writer to avoid import-time side effects.

### create_app
**SPEC-014.3** — Flask application factory. Accepts an optional injected HDF5Writer for testing.

### main
**SPEC-014.7** — CLI entry point. Reads DSLV_RECEIVER_PORT from environment.

### Contract Tests (HTTP surface)
**SPEC-014.8** — Contract tests exercising the public endpoints for malformed input, missing fields, writer/storage failure paths, and concurrent POST handling. Uses Flask test client with injected writers for isolation. Covers /api/v1/ingest, /api/v1/ingest/radoneye, /api/v1/health.

## Kill Conditions
- Missing payload_uuid → KILLED
- Invalid JSON → 400 Bad Request
- Missing required RadonEye fields → 422 Unprocessable Entity
- Storage failure → 500 Internal Server Error
