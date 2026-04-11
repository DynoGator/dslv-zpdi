# DSLV-ZPDI Contributing Guidelines

**Role:** Autonomous Co-Pilot & Systems Engineer
**Status:** Rev 4.2.0 Canonical (Phase 2A Hardware Transition — LBE-1420)

---

## 1. MISSION ALIGNMENT
All contributions must align with the mission defined in `V3_DSLV-ZPDI_LIVING_MASTER.md`. We build airtight, institutional-grade machines. Theoretical speculation must be isolated from the data pipeline.

## 2. CANONICAL GUARDRAILS (NO ROGUE CODE)
DSLV-ZPDI is a SPEC-driven project. 
- **Every** class, method, and architectural decision **MUST** map to a formal `SPEC-ID` in the docstrings.
- If your code lacks a SPEC-ID, the `tools/orphan_checker.py` will reject the commit.
- Refer to `MASTER_SPEC.md` for the canonical law layer.

## 3. DEVELOPMENT WORKFLOW
- **Hardware Abstraction:** Utilize the `BaseHAL` (`src/layer1_ingestion/hal_base.py`) for any new sensor modalities.
- **Simulation:** Implement a `SimulatedHAL` for CI/CD and virtual validation before physical deployment.
- **Testing:** Add regression tests to the `tests/` suite. Ensure they pass with `DEV_SIMULATOR=1`.

## 4. GIT PROTOCOL
- **Commits:** Use conventional commit messages: `<type>(<scope>): <Active_Revision> — <description>`.
- **Pre-Commit:** Run `python tools/orphan_checker.py` and `python tests/test_pipeline.py` before pushing.

---
*For institutional credibility, we do not compromise on technical integrity.*
