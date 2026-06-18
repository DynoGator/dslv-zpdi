## Proposed Changes

**SPEC-ID Mapping:**
List the SPEC-IDs this change implements or modifies. 

**Summary:**
Briefly describe the intent of the change.

**Type of Change:**
- [ ] feat: New feature (mapped to SPEC)
- [ ] fix: Bug fix (restoring spec-parity)
- [ ] docs: Documentation update
- [ ] ci: Tooling/CI improvement
- [ ] security: Security or evidence-integrity improvement

## Pre-Flight Checklist
- [ ] `python tools/check_version_sync.py` passes.
- [ ] `python tools/orphan_checker.py` passes.
- [ ] `python tools/repo_guard.py` passes.
- [ ] `python -m ruff check src/ tools/ tests/` passes.
- [ ] `python -m mypy src/dslv_zpdi/layer2_core` passes when Layer 2 is touched.
- [ ] `DEV_SIMULATOR=1 python -m pytest tests/ -q --cov` passes.
- [ ] Changelog updated when behavior, CI, security, or release automation changes.
- [ ] Hardware claims are backed by actual hardware command output or marked not run.
- [ ] Security issues are handled privately, not in public issue or PR comments.

---
Autonomous review requested.
