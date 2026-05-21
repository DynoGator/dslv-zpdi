# Changelog — dslv-zpdi Tier-1 Mobile Node

All notable changes to this node deployment. Follows [Conventional Commits](https://www.conventionalcommits.org/).
**APPEND-ONLY** — existing entries are never modified or deleted.

---

## [Unreleased]

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
