# Handoff — Pending Hardware Adapter & PlutoSDR Firmware

**Date:** 2026-06-15  
**Repository:** `/home/dynogator/Desktop/DSLV-ZPDI_GitHub_Dev/dslv-zpdi`  
**Branch:** `feat/tier1-plutosdr-plus-metrology`  
**HEAD:** `0d20b83`  
**Status:** Software complete, virtualenv clean, branch pushed. Waiting on hardware.

---

## What is blocked

- Physical adapter cable for the PlutoSDR+ timing ports (`10M` / `PPS`) is not
  yet available.
- PlutoSDR+ firmware has not yet been flashed/verified.

## Current clean state

- `.venv/` rebuilt from scratch with only project-declared dependencies.
- `pip check` reports **No broken requirements found**.
- All automated gates pass:
  - `pytest -q` → 143 passed
  - `ruff check .` → All checks passed
  - `ruff format --check src tests` → 92 files already formatted
  - `tools/orphan_checker.py` → OK
  - `tools/check_version_sync.py` → OK — 5.0.0
  - `tools/repo_guard.py` → OK
  - `dslv-zpdi-{probe,preflight,verify} --version` → 5.0.0

## When the adapter cable arrives

1. Inspect the cable pinout against `docs/hardware/HAMGEEK_AD9363_TIMING_PORT_VERIFICATION.md`.
2. Connect LBE-1421 `Out2` (10 MHz) to the Pluto `10M` port.
3. Connect LBE-1421 `Out1` (1 PPS) to the Pluto `PPS` port.
4. Power both units and verify lock LEDs.

## When you flash the Pluto firmware

1. Note the exact firmware version flashed.
2. Update `docs/hardware/HAMGEEK_AD9363_PLUTOSDR_PLUS.md` with the version.
3. Re-run the software probe to confirm libiio still discovers the device:

   ```bash
   cd /home/dynogator/Desktop/DSLV-ZPDI_GitHub_Dev/dslv-zpdi
   .venv/bin/dslv-zpdi-probe
   ```

## Next commands to run (in order)

```bash
cd /home/dynogator/Desktop/DSLV-ZPDI_GitHub_Dev/dslv-zpdi
source .venv/bin/activate

# 1. Strict preflight (will fail-closed if timing is not healthy)
dslv-zpdi-preflight --profile config/node_profiles/tier1_pluto_lbe1421.yaml --strict

# 2. Tier-1 hardware qualification
dslv-zpdi-qualify --profile config/node_profiles/tier1_pluto_lbe1421.yaml

# 3. Short soak test
dslv-zpdi-soak-test --profile config/node_profiles/tier1_pluto_lbe1421.yaml --duration 10m

# 4. Longer soak tests after the 10-minute run passes
# dslv-zpdi-soak-test --duration 1h
# dslv-zpdi-soak-test --duration 24h
# dslv-zpdi-soak-test --duration 72h
```

## Documentation to update with measured evidence

- `docs/qualification/PLUTO_ACCEPTANCE_MATRIX.md`
- `docs/hardware/HAMGEEK_AD9363_PLUTOSDR_PLUS.md`
- `docs/hardware/HAMGEEK_AD9363_TIMING_PORT_VERIFICATION.md`
- `TURNOVER_2026-06-15_Tier1_PlutoSDR_Pivot.md`

## Before you shut down now

- All changes are committed and pushed.
- No background tasks are running.
- Disk writes are in sync.

Safe to power off.
