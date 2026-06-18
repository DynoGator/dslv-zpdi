# DSLV-ZPDI Contributing Guidelines

**Status:** Rev 5.0.0 development policy

---

## 1. MISSION ALIGNMENT
All contributions must align with the mission defined in `V3_DSLV-ZPDI_LIVING_MASTER.md`. We build airtight, institutional-grade machines. Theoretical speculation must be isolated from the data pipeline.

## 2. CANONICAL GUARDRAILS (NO ROGUE CODE)
DSLV-ZPDI is a SPEC-driven project. 
- **Every** class, method, and architectural decision **MUST** map to a formal `SPEC-ID` in the docstrings.
- If your code lacks a SPEC-ID, the `tools/orphan_checker.py` will reject the commit.
- Refer to `MASTER_SPEC.md` for the canonical law layer.

## 3. DEVELOPMENT WORKFLOW
- **Python policy:** support Python 3.10 through 3.14. Use Python 3.13 for local editable installs and requirements regeneration unless testing a matrix-specific issue.
- **Hardware Abstraction:** Use the composed HAL interfaces under `src/dslv_zpdi/layer1_ingestion/` for new hardware.
- **Simulation:** Simulator mode must not touch physical SDR, PPS, NMEA, or GPSDO devices. CI must remain hardware-independent.
- **Testing:** Add regression tests to the `tests/` suite. Ensure they pass with `DEV_SIMULATOR=1`.

## 4. GIT PROTOCOL
- **Commits:** Use Conventional Commits: `type(optional-scope)!: summary`.
- **Allowed types:** `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`, `chore`, `revert`, `security`.
- **Local hooks:** run `git config core.hooksPath .githooks` so the committed hooks are active.
- **Pre-push validation:** run `python tools/orphan_checker.py`, `python tools/repo_guard.py`, `python -m ruff check src/ tools/ tests/`, and `DEV_SIMULATOR=1 python -m pytest tests/ -q`.

---
*For institutional credibility, we do not compromise on technical integrity.*
