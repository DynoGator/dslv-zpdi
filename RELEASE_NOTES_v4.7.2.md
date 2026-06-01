# Release Notes — v4.7.2

**Date:** 2026-06-01
**Theme:** Robustness, Reliability & Security Hardening
**Baseline:** Rev 4.7.1 → Rev 4.7.2

This is a quality-and-hardening release. The trust pipeline's behaviour is
unchanged; the work makes shutdown safe for the data on disk, shrinks the swarm
receiver's attack surface, and raises overall code health. The objective for the
pass was system stability and trustworthy data output.

## Highlights

### Reliability / data integrity
- **Graceful shutdown.** `main_pipeline.py` previously terminated via
  `os._exit(0)` inside the signal handler, which could leave the open HDF5 file
  truncated. Shutdown is now cooperative: SIGINT/SIGTERM stop the worker threads,
  join them, then flush and close the HDF5 writer, timing monitor, and health
  reporter. `SIGTERM` (systemd's stop signal) is now handled as well as `SIGINT`.
- **Latent import crash fixed.** The deprecated `cm5_ingestion` shim imported
  `BaseHAL` from `hal_factory`, which never exported it — importing the module
  raised `ImportError`. `hal_factory` now re-exports the canonical HAL surface and
  every package submodule imports cleanly.

### Security
- **Request-size cap** on the Flask node receiver (`MAX_CONTENT_LENGTH = 1 MiB`)
  rejects oversized bodies before they are buffered into memory.
- **Atomic, locked node registry** writes remove a read-modify-write corruption
  race under concurrent POSTs.
- **RadonEye numeric validation** returns a clean `422` for a non-numeric
  `radon_bq_m3` reading instead of a later `500`.
- **Loud insecure-key warning** when `HDF5Writer` falls back to the development
  HMAC key, so weakened attestation cannot silently ship to the field.

### Code health
- Ruff is clean across `src/`, `tools/`, and `tests/` (~240 findings resolved).
- Pylint rating improved from **9.31 → 9.64 / 10**.
- Type hints modernized to PEP 585/604 behind `from __future__ import annotations`
  (3.9-safe).
- `dslv_zpdi.__version__` is now defined and enforced against `pyproject.toml` by
  `tools/check_version_sync.py`.

## Verification

Run from the editable `.venv`:

- `pip check`: clean
- `tools/check_version_sync.py`: clean at 4.7.2
- `tools/orphan_checker.py`: clean
- `tools/repo_guard.py`: passed
- `ruff check src/ tools/ tests/`: all checks passed
- `pylint src/dslv_zpdi/`: 9.64/10
- `DEV_SIMULATOR=1 pytest tests/ -v`: 47 passed
- `DEV_SIMULATOR=1 tests/test_pipeline.py`: 10/10 passed

## Upgrade notes

No configuration or schema changes. Operators running the node receiver behind a
reverse proxy may align the proxy body-size limit with the new 1 MiB cap.
