# Changelog — dslv-zpdi Tier-1 Mobile Node

All notable changes to this node deployment. Follows [Conventional Commits](https://www.conventionalcommits.org/).
**APPEND-ONLY** — existing entries are never modified or deleted.

---

## [Unreleased]

### Added
- `supervisor.sh` — foreground daemon supervisor with exponential back-off restart.
  Addresses the `--kill-on-exit` proot constraint that caused the daemon to die whenever
  the launch proot session exited (the root cause of the auto-start failure).
- `.githooks/pre-commit` — blocks `.env`, `*.pat`, `data/*.h5`, `*.pid` from commits.
- `.githooks/pre-push` — validates `GITHUB_PAT` and rejects plaintext-credential remote URLs.

### Changed
- `launch_daemon.sh` — rewritten to start the supervisor inside an **independent** proot
  session (`nohup proot-distro login debian -- bash supervisor.sh`), so the daemon proot
  survives terminal close and is not tied to the interactive session.
- `99-start-zpdi.sh` (Termux:Boot) — updated to the same pattern; supervisor is the
  foreground process of the boot proot, keeping it alive through device operation.
- `configure_git_auth.sh` — fixed `DynoGater` typo → `DynoGator` in fallback remote URL.
- `.githooks/README.md` — updated to reflect both hooks are now implemented.
- `zpdi_mobile_node.py` — replaced deprecated `h5py.special_dtype(vlen=bytes)` with
  `h5py.vlen_dtype(bytes)`; updated `WebSocketClientProtocol` annotation to
  `ClientConnection` (websockets 16+ asyncio API).

---

## [e7b8497] 2026-05-19 — feat: finalize deployment-ready metrology node

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
