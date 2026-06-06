# KIMI Phase 2B Intake — Environmental Metrology Fusion (Radon + Mobile Node)

**Date:** 2026-06-05
**Agent:** KIMI_CODE_CLI
**Branch:** `phase-2b/radon-metrology-fusion`

---

## 1. Governance Docs Read

| Document | Key Takeaways |
|----------|---------------|
| `MASTER_SPEC.md` | Canonical SPEC-ID law layer. Every module must carry a valid SPEC-ID docstring. `tools/orphan_checker.py` enforces. |
| `V3_DSLV-ZPDI_LIVING_MASTER.md` | Full system spec. LBE-1421 dual-output is the clock authority. Tier 1 = GPS-disciplined phase-locked RF only. Tier 2 = context/tamper-evidence, never primary stream. Packet state machine: RAW_CAPTURED → ASSEMBLED → TIME_TRUSTED → CAL_TRUSTED → CORE_PROCESSED → PRIMARY_CANDIDATE/ACCEPTED or SECONDARY_QUARANTINED. |
| `README.md` | v4.7.0 architecture: Layer 1 Ingestion → Layer 2 Core (Kuramoto) → Layer 3 Telemetry (HDF5 dual-stream). HackRF + LBE-1421 GPSDO. Pixel 9 Pro XL already bridged as Tier 2 node via PiRepo hotspot (10.42.0.x). Dashboard is Rich TUI with glitch/plasma aesthetic. |
| `CONTRIBUTING.md` | Conventional commits: `<type>(<scope>): <Active_Revision> — <description>`. Run orphan_checker + test_pipeline before push. Hardware abstraction via BaseHAL; simulator for CI/CD. |
| `repo_manifest.yaml` | Canonical validation: editable_install, pip_check, pytest, orphan_checker, version_sync, repo_guard. Source roots: `src/`, `tests/`, `tools/`, `specs/`. |
| `pyproject.toml` | v4.7.1. Dependencies: numpy, scipy, h5py, pyserial, pyhackrf, pydantic, pyyaml, rich, pyfiglet, flask, psutil. Dev: pytest, black, pylint, mypy, ruff. |
| `src/dslv_zpdi/layer3_telemetry/hdf5_writer.py` | Current HDF5 schema: event groups with `r_local`, `r_smooth`, `r_global`, `payload_uuid`, `timestamp_utc`, plus attestation attrs (HMAC, SHA-256, chronyc state). File rotation at 500 MB. |
| `tools/orphan_checker.py` | AST-based checker. Scans `src/` for functions/classes missing SPEC-ID docstrings/comments. Scans `specs/` for defined SPEC-IDs. Fails if any rogue nodes or orphaned claims. |
| `RELEASE_NOTES_v4.3.0.md` | Last reference release before current v4.7.1. 31 tests passing. Trixie/Bookworm compatible. |
| `TURNOVER_2026-05-30_NodeBridge_HDF5_Dashboard.md` | Most recent turnover. Node bridging + HDF5 multi-node aggregation + dashboard finalisation completed. Pixel 9 Pro XL integrated at 10.128.24.165 (note: README says 10.42.0.x PiRepo subnet). |

---

## 2. Baseline Test / Orphan / Timing State

### Test Suite
```
pytest tests/ -v
============================= 47 passed in 23.03s ==============================
```
**Status:** GREEN. No pre-existing test failures.

### Orphan Checker
```
Nodes missing SPEC-ID: 27 total
  -> node_receiver.py: 7 functions (create_app, ingest_node, ingest_radoneye, health, _update_node_registry, _get_writer, main)
  -> pps_listener.py: 8 functions/class (PpsListener, __init__, start, stop, wait_for_edge, snapshot, _run, _fetch_kernel_ts, _recompute_jitter)
  -> nmea_stream.py: 8 functions/class (NmeaStream, __init__, start, stop, latest, _run, _reader_loop, _empty_fix, parse_gga)
  -> hal_hardware.py: 1 function (_pyhackrf_device_list_safe)
```
**Status:** RED (pre-existing). These 27 gaps must be fixed before any Phase 2B commit can pass orphan_checker.

### Timing Health
```
[*] /dev/pps0 detected.
[*] PPS Offset: 4221447945.00ns
[!] FAILURE: Jitter 4221447945.00ns exceeds 1000ns threshold.
[NOT READY] Hardware timing violations detected.
```
**Status:** RED (expected). GPSDO is not locked (no antenna / indoor lab). This is a known hardware state, not a code regression.

---

## 3. Known Gaps Flagged for Phase 2B

1. **Coherence pinned at r1.00 / R1.00** — The dashboard shows `Coh r1.00 R1.00` which suggests a degenerate null distribution in the Kuramoto coherence engine. **I will NOT depend on this for the BCI.** The BCI will compute its own cross-correlation independently.
2. **GPS `fix=?` (unlocked)** — LBE-1421 not reporting a fix. I will add degraded-mode indicators and ensure the radon session orchestrator stamps timing-health into the manifest.
3. **Chrony RMS wandering** — Timing discipline is loose. I will surface timing health in the session manifest and dashboard.
4. **LBE-1420 vs LBE-1421 doc mismatch** — The `V3_DSLV-ZPDI_LIVING_MASTER.md` still references LBE-1420 in some places. The README correctly says LBE-1421. I will correct the living master.
5. **SPEC-014 is a placeholder stub** — Needed for node_receiver.py compliance.

---

## 4. Pre-existing Failures Blocking Phase 2B

**None.** The 47 test suite is green. The orphan checker red state is fixable by adding docstrings + spec files. The timing red state is a hardware/antenna issue, not code.

---

## 5. Build Order Plan

1. Fix orphan_checker gaps (add SPEC-IDs to existing code + create missing spec files)
2. 3.1 — RadonEye Pro telemetry ingestor (`radoneye_ingestor.py`)
3. 3.2 — Pixel 9 Pro XL mobile node bridge (`pixel_node_bridge.py`)
4. 3.3 — Network / uplink manager (`uplink_manager.py`)
5. 3.4 — HDF5 schema extension (additive only)
6. 3.5 — BCI engine (`barometric_coherence.py`)
7. 3.6 — 48-hour session orchestrator (`radon_session.py`)
8. 3.7 — Dashboard surfacing (RADON, MOBILE, BCI panels)
9. Reporting deliverables (SESSION_REPORT, CHANGELOG, TURNOVER)

---

## 6. Simulator-First Pledge

Every new ingestor will have a `--simulator` / mock path. No hardware dependency without a mock. Target: 100% of new modules unit-testable without physical devices.
