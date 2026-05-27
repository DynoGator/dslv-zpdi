# Changelog — dslv-zpdi Tier-1 Mobile Node

All notable changes to this node deployment. Follows [Conventional Commits](https://www.conventionalcommits.org/).
**APPEND-ONLY** — existing entries are never modified or deleted.

---

## [Unreleased]

### Added
- `src/layer1_ingestion/gps_poller.py`: Async GPS/Network/Passive location poller with capped exponential backoff, accuracy gating, and non-blocking integration with Layer 1 enrichment.
- `zpdi_mobile_node.py` (Rev 3.5): Hardened WSS transport with jittered exponential backoff, circuit-breaker pattern (5-failure threshold / 30s cooldown), and Bearer token authentication via `additional_headers`.
- SPEC-008 payload security: HMAC-SHA256 signing (`hmac` field) and optional AES-256-GCM envelope encryption controlled by `ZPDI_HMAC_SECRET` and `ZPDI_AES_KEY`.
- Expanded sensor vectoring suite: `ICM45631 Gyroscope`, `Rotation Vector Sensor`, `Geomagnetic Rotation Vector Sensor`, `Gravity Sensor` added to `SENSORS` and `SENSOR_MODALITY_MAP`.
- Location metadata embedding (`latitude`, `longitude`, `altitude`, `accuracy`, `location_provider`, `location_timestamp`) in every `IngestionPayload`.
- `ZPDI_NODE_ID` environment variable for configurable edge-node identity.
- `tests/test_mobile_compliance.py`: 5 additional hardening regression tests (HMAC, AES envelope, GPS enrichment, expanded modalities, gyroscope phase extraction).

### Changed
- `requirements.txt`: Added `cryptography>=42.0` dependency for AES-256-GCM support.
- `.env.example`: Documented `ZPDI_WSS_TOKEN`, `ZPDI_HMAC_SECRET`, `ZPDI_AES_KEY`, `ZPDI_NODE_ID`, and GPS poller tuning variables.
- `zpdi_mobile_node.py`: Health watchdog now reports GPS fix state and WSS circuit-breaker status.

### Fixed
- `src/layer1_ingestion/mobile_ingestion.py`: Phase extraction now correctly handles magnitude-vector modalities (accel, magnetometer, gyroscope, gravity) while treating rotation vectors and barometer as reference-only.

## [2026-05-27] — feat: mobile node hardening Phase-2 (GPS, expanded vectoring, crypto, WSS auth)

### Added
- `src/layer1_ingestion/mobile_ingestion.py`: Canonical Layer 1 driver for Tier-2 mobile nodes with Hilbert phase extraction.
- `src/layer2_core/coherence.py`: KCET-ATLAS CoherenceScorer with EWMA smoothing and global weighted R(t).
- `src/layer2_core/wiring.py`: Layer 2 wiring gate (canonical + mobile variant).
- `src/layer3_telemetry/mobile_router.py`: Dual-Stream Router enforcing Tier-2 quarantine with coherence-based categorisation.
- `tests/test_mobile_compliance.py`: 14-test validation suite covering SPEC-005/006/007.
- `AUDIT_VIOLATIONS.md`: SPEC violation baseline for the pre-compliance `main` branch.
- Health watchdog (`logs/health.jsonl`) with PID, sensor liveness, queue depths, and WSS state.
- Log rotation for `SecondaryLog` at 10 MB with gzip archival.

### Changed
- `zpdi_mobile_node.py`: Refactored from flat-file logger to three-layer architecture using `IngestionPayload`, `CoherenceScorer`, and `DualStreamRouter`.
- `supervisor.sh`: Added health-log staleness check (>90s triggers forced restart).
- `README.md`: Clarified Tier-2 Swarm status and institutional-grade hardware requirements.

### Fixed
- `HDF5Sink` now rejects all non-`PRIMARY_ACCEPTED` packets (mobile primary stream is intentionally empty).
- All mobile packets correctly self-declare `hardware_tier=2` and `trust_state=SECONDARY_QUARANTINED`.

## [2026-05-21] — Audit & Architectural Upgrade

### Added
- `zpdi_web_server.py`: FastAPI-based web backend providing `/health`, `/latest`, and `/ws/live` endpoints.
- `SQLiteCache` in `zpdi_mobile_node.py`: Lightweight WAL-mode cache for the latest sensor state, enabling concurrent polling without HDF5 lock contention.
- `README_WEB.md`: Detailed guide for Termux-specific network interface constraints and Vite frontend integration.
- `ZPDI_SQLITE_PATH` and `ZPDI_WEB_*` configuration parameters to `.env.example`.

### Fixed
- `zpdi_mobile_node.py`: Fragile WebSocket state check (string comparison) replaced with `websockets.protocol.State` enum.
- `zpdi_mobile_node.py`: Race condition in queue "drop-oldest" logic hardened with `try/except` blocks for `asyncio.QueueFull` and `asyncio.QueueEmpty`.
- `edge_listener_stub.py`: Added defensive typing guards (`isinstance`) for received messages.
- `configure_git_auth.sh`: Prevented plaintext GITHUB_PAT persistence in `.git/config` by using a runtime helper that reads from `.env`.
- `.githooks/pre-commit`: Explicitly allowed `.env.example` while maintaining security for other `.env` files.

### Changed
- `requirements.txt`: Added `fastapi` and `uvicorn` dependencies.
- `zpdi_mobile_node.py`: Set `PRAGMA journal_mode=WAL` on SQLite cache for concurrent-safe access.

---

## [2026-05-19] — feat: finalize deployment-ready metrology node

- Continuous sensor streaming via `termux-sensor -d 250` (streaming mode, not polling).
- `asyncio.wait_for` wrapper removed from `readline()` after empirical measurement showed
  it starved the reader (0/18 objects in 6s with wrapper, 18/18 without).
- SWMR mode enabled on HDF5 writer; `zpdi_verifier.py` can tail while daemon writes.
- `ZPDI_STREAM_DELAY_MS` / `ZPDI_WSS_URI` / `ZPDI_HDF5_PATH` / `ZPDI_FALLBACK_LOG`
  environment variables for per-deployment configuration.

## [7c4fbda] 2026-05-19 — refactor(node): switch sensor IPC to continuous streaming mode

- Replaced polled `-n 1` invocations with persistent `-d <ms>` streaming subprocess.
- `_consume_stream()` uses `json.JSONDecoder.raw_decode` to parse back-to-back JSON objects
  emitted by the streaming process without relying on newline delimiters.

## [c48fd94] 2026-05-19 — fix(node): use exact sensor names from termux-sensor -l

- `termux-sensor` requires full vendor strings (e.g. `ICM45631 Accelerometer`);
  substring matches silently return no rows.

## [f75d5c0] 2026-05-19 — build(deps): pin requirements.lock for tier-1 reproducibility

## [61c0f95] 2026-05-19 — feat(verifier): add SHA-256 provenance verifier for HDF5 stream

## [df3f14f] 2026-05-19 — feat(node): add async metrology daemon zpdi_mobile_node.py

## [b7cd356] 2026-05-19 — chore(scaffold): initialize dslv-zpdi tier-1 node workspace
