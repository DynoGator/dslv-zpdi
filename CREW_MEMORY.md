# DynoGatorLabs Crew - Unified Memory State

**LAST UPDATED:** 2026-07-25T20:30:00+00:00
**SYSTEM STATUS:** OPERATIONAL — C2 CONTROL PLANE ACTIVE — Phase 4 COMPLETE

## 1. Current Codebase State
- **Branch:** `main` @ `c0af49f` — untracked Phase 4 artifacts pending commit
- **Tests:** 233 passed, 1 skipped — verified on Pixel 9 Pro XL (proot Debian)
- **Merged Features (v5.0.0 baseline):**
  - `PlutoSDR+ Tier1` hardware abstraction layer (IIO / libiio)
  - `Mobile-Node` architecture (Pixel 9 Pro XL GrapheneOS / PRoot)
  - `Radon-Eye Pro` telemetry fusion
  - CLI: `preflight`, `probe`, `verify` commands
  - Key provider chain (dev / file / env / production)
  - Tier-1 ingestion server with AES-256-GCM + HMAC + SHA256 integrity
  - Frequency translation / calibration subpackage
  - Timing subpackage (PPS, NMEA, Chrony, LBE-1421, attestations)
  - Complete CI matrix (GitHub Actions + Docker + security scan)
- **Phase 4 — NEW (untracked, to be committed):**
  - `specs/SPEC-C2-001.md` — C2 protocol spec (SPEC-022)
  - `docs/security/C2_THREAT_MODEL.md` — C2 threat model
  - `src/dslv_zpdi/control/` — canonical C2 package (protocol, authorization, audit)
  - `src/dslv_zpdi/control/adapters/` — real adapters (pipeline, sdr, hdf5_query)
  - `tests/test_control_protocol.py` — 23 test cases
  - `tests/test_control_adapters.py` — 26 test cases (adapters)
- **TEST COMMAND:** `DEV_SIMULATOR=1 .venv/bin/python -m pytest tests/ -v`

## 2. Hardware Configuration
- **Tier 1 Primary Node:**
  - Hardware: HamGeek Pluto+ (Zynq-7020, 1GB RAM)
  - Network: Gigabit Ethernet at `192.168.3.80`
  - SDR Connection: IIO network context (`ip:192.168.3.80`)
  - Firmware: Custom Tezuka-Libre hybrid (required for Zynq-7020 RAM mapping)
  - See: `docs/PLUTO_SDR_FIRMWARE_GUIDE.md`, `docs/PlutoSDR/`
- **GPSDO Metrology Clock:**
  - Hardware: Leo Bodnar LBE-1421
  - Out 1 (1 PPS) → Pi 5 GPIO 18 (UTC anchoring)
  - Out 2 (10 MHz) → PlutoSDR+ CLKIN (Hardware phase lock)
  - See: `docs/hardware/LBE1421_PLUTO_WIRING.md`
- **Mobile Tier-2 C2 Node:**
  - Hardware: Pixel 9 Pro XL / GrapheneOS / PRoot Debian
  - Main pipeline: `zpdi_mobile_node.py` via `supervisor.sh`
  - C2 overlay: `/root/dslv-zpdi-local/` (outside main repo)
  - Boot scripts (Termux): `98-dslv-c2-services.sh`, `99-start-zpdi.sh`
  - Running services: C2 `:8444`, HDF5 adapter `:8445`, PWA `:8085`, main pipeline `:8443`/`:8080`

## 3. Active Development Track — PIXEL_DEV_PLAN.md

**Canonical plan:** `/data/data/com.termux/files/home/PIXEL_DEV_PLAN.md`
**Current plan step:** Section 6 — Immediate Next Steps

| # | Task | Status |
|---|------|--------|
| 1 | Apply Phase 1 manual GrapheneOS settings on device | Manual — device action required |
| **2** | **Reboot + confirm services auto-start from boot logs** | **CURRENT — services running; boot-c2.log absent (reboot test pending)** |
| 3 | 30-minute screen-off soak test | Pending step 2 reboot |
| **4** | **Implement control adapters (`src/dslv_zpdi/control/adapters/`)** | **DONE 2026-07-25 — pipeline, sdr, hdf5_query adapters live** |
| 5 | Build native APK Phase 6B (Kotlin + LocalOnlyHotspot) | Future |
| 6 | Complete Phase 8 one-shot installer | Future |

**boot-c2.log status:** Absent — services were manually started, boot script auto-run unverified.
To verify step 2: reboot device, then `tail -f /root/dslv-zpdi-local/logs/boot-c2.log`

## 4. Operational Directives
- **NO DESTRUCTIVE MERGES:** `main` is stable. All new work branches from `main` and must pass the 207-item test suite before merging.
- **HARDWARE PRIORITY:** SDR unreachable → degrade to SIMULATOR, do not crash.
- **C2 SECURITY:** Bearer token auth at `127.0.0.1` only. No LAN exposure until mTLS implemented.
- **SPEC-ID DISCIPLINE:** Every new `src/dslv_zpdi/` module must cite a SPEC-ID.
- **VALIDATE:** `bash /root/dslv-zpdi-local/scripts/validate.sh` before and after any code change.

## 5. Pending Commits (main repo)
These files are untracked and need to be committed:
- `specs/SPEC-C2-001.md`
- `docs/security/C2_THREAT_MODEL.md`
- `src/dslv_zpdi/control/__init__.py`
- `src/dslv_zpdi/control/protocol.py`
- `src/dslv_zpdi/control/authorization.py`
- `src/dslv_zpdi/control/audit.py`
- `src/dslv_zpdi/control/adapters/__init__.py`
- `src/dslv_zpdi/control/adapters/pipeline.py`
- `src/dslv_zpdi/control/adapters/sdr.py`
- `src/dslv_zpdi/control/adapters/hdf5_query.py`
- `tests/test_control_protocol.py`
- `tests/test_control_adapters.py`
- `SESSION_REPORT_2026-07-25_C2_PROTOCOL.md`
- `CREW_MEMORY.md` (updated)

## 6. Open Risks
- `CapabilityStore` grants full capabilities to all localhost callers → must change before LAN exposure
- `hdf5.segment.export` declared but returns staged ack; actual export not implemented
- `sensor_alive: false` in health log (pre-existing, investigate separately)
- Gemini CLI OAuth free tier ended June 2026 — verify subscription
- Legacy normalization shim in `c2_server.py` should be removed after all clients confirmed spec-compliant
