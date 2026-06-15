# Turnover Report — Tier-1 PlutoSDR+ Metrology Hardware Pivot

**Date:** 2026-06-15  
**Repository:** `/home/dynogator/Desktop/DSLV-ZPDI_GitHub_Dev/dslv-zpdi`  
**Branch:** `feat/tier1-plutosdr-plus-metrology`  
**Base commit:** `1329e76e4ee4faf02cc7fea43bb68443974759e4`  
**Current HEAD:** `e6fef50`  
**Version:** `5.0.0`  
**Python:** 3.13.5 (Debian 13 Trixie)  
**Virtualenv:** `.venv/`

---

## 1. Scope

Complete the Tier-1 hardware pivot from HackRF One to a capability-based
core that natively supports PlutoSDR-family devices (HamGeek/AD9363) with the
Leo Bodnar LBE-1421 GPSDO reference, while keeping HackRF as an optional
Tier-2/minimum-performance path.

---

## 2. Summary of Changes

### 2.1 Architecture

- Introduced a composed `HardwareHAL` that binds `TimingAuthority`,
  `SdrBackend`, optional `FrequencyTranslationStage`, and a
  `Tier1QualificationPolicy`.
- Replaced monolithic vendor HALs with backend/qualification abstractions:
  - `PlutoIioBackend` (lazy libiio import, readback validation, fail-closed)
  - `SimulatedSdrBackend` (deterministic qualification scenarios)
- Refactored timing into a dedicated subpackage:
  - `TimingAttestation` / `ClockAttestation` with nine explicit evidence states
  - `Lbe1421Authority`, `PpsListener`, `NmeaStream`, `ChronyMonitor`
- Added frequency-translation stage with converter-provenance preservation.
- Added key-provider abstraction:
  - `ProductionKeyResolver` (file → env → systemd-credential)
  - `DevelopmentKeyProvider` (requires explicit simulator opt-in)

### 2.2 Integrity & Provenance

- HDF5 writer now:
  - Finalizes files atomically (`*.partial` → `*.h5`)
  - Appends an event hash chain for tamper evidence
  - Requires a `KeyProvider` or explicit development override

### 2.3 Tooling & Configuration

- New CLIs:
  - `dslv-zpdi-probe`
  - `dslv-zpdi-preflight`
  - `dslv-zpdi-verify`
- New node profile: `config/node_profiles/tier1_pluto_lbe1421.yaml`
- `pyhackrf` moved to optional `[hackrf]` dependency group
- `pyproject.toml` updated with ruff excludes for owner WIP scripts

### 2.4 Documentation

- `docs/audits/PLUTOSDR_PIVOT_BASELINE_AUDIT.md`
- `docs/hardware/PLUTO_PCB_PORT_MAP.md`
- `docs/operations/TIER1_PREFLIGHT_CHECKLIST.md`
- `docs/qualification/HACKRF_BASELINE_MATRIX.md`
- `docs/qualification/PLUTO_ACCEPTANCE_MATRIX.md`
- `docs/security/HDF5_KEY_PROVIDER.md`
- `specs/SPEC-004A.md`, `specs/SPEC-004A.5.md`

---

## 3. Fresh Verification Evidence

All commands were run in a clean shell on 2026-06-15 from the repository root.

| Gate | Command | Result |
|------|---------|--------|
| Unit tests | `.venv/bin/python -m pytest -q` | **143 passed** |
| Lint | `.venv/bin/python -m ruff check .` | **All checks passed** |
| Format | `.venv/bin/python -m ruff format --check src tests` | **92 files already formatted** |
| SPEC orphan check | `.venv/bin/python tools/orphan_checker.py` | **OK** |
| Version sync | `.venv/bin/python tools/check_version_sync.py` | **OK — 5.0.0** |
| Repo guard | `.venv/bin/python tools/repo_guard.py` | **OK** |
| Dependency check | `.venv/bin/python -m pip check` | **No broken requirements found** |
| CLI availability | `dslv-zpdi-{probe,preflight,verify} --version` | **5.0.0** |

### Dependency environment

- The project virtualenv was rebuilt from scratch with only the declared
  dependencies (plus dev extras). `pip check` now reports no conflicts.

---

## 4. Open Physical Verification Gates

The software is complete and validated in simulation. The following gates
require the owner to connect the physical PlutoSDR+ and LBE-1421:

| Gate | Status | Owner Action |
|------|--------|--------------|
| Exact PCB revision | UNVERIFIED | Inspect silkscreen / sysfs |
| Timing connector family | UNVERIFIED | Verify micro-coaxial pinout |
| 10 MHz direction | UNVERIFIED | Scope the `10M` port |
| PPS direction | UNVERIFIED | Scope the `PPS` port |
| Electrical level | UNVERIFIED | Confirm 3.3 V CMOS tolerance |
| External reference consumed | UNVERIFIED | Inject 10 MHz, check RX path |
| PPS healthy | UNVERIFIED | Connect LBE-1421 Out1 |
| Sample epoch synchronized | UNVERIFIED | Run `dslv-zpdi-preflight --strict` |
| Sustained capture | PROVISIONAL | Run `dslv-zpdi-soak-test --duration 1h` |
| Tier-1 qualification | PROVISIONAL | Run `dslv-zpdi-qualify` and submit evidence |

See `docs/qualification/PLUTO_ACCEPTANCE_MATRIX.md` and
`docs/operations/TIER1_PREFLIGHT_CHECKLIST.md` for detailed procedures.

---

## 5. Recommended Next Steps

1. Owner completes the physical verification gates above.
2. Run the 10-minute qualification on hardware:
   `.venv/bin/dslv-zpdi-qualify --profile config/node_profiles/tier1_pluto_lbe1421.yaml`
3. Run the 1-hour soak test, then 24 h / 72 h as schedule allows.
4. Update `PLUTO_ACCEPTANCE_MATRIX.md` with measured evidence.
5. Merge `feat/tier1-plutosdr-plus-metrology` to `main` after hardware gates
   close.

---

## 6. Sign-off

- **Software implementation:** complete
- **Automated validation:** passing
- **Physical hardware qualification:** pending owner action
- **Branch push status:** pushed to `origin/feat/tier1-plutosdr-plus-metrology`

No source secrets, no `sys.path` mutation, and no orphaned SPEC claims are
present in the current tree.
