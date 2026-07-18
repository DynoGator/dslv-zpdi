# AGENTS.md — Universal Agent Handoff

## 1. DOCTRINE
- The meter is the master. Claims are hypotheses until independent meters agree.
- The guillotine is sharp, but the engineering is sharper.
- Negative results are valid results. Honest scars stay on the permanent record.
- Do-no-harm on working hardware paths. Revert the change, never the test.
- Quorum or it didn't happen — no single node, and no single agent, declares truth.

## 2. STARTUP GATE COMMANDS
Run these before any work:
```bash
git fetch --all --prune
pytest tests/ -q
gh run list --branch main --limit 3
```

## 3. TEST COUNTS & TAGS (2026-07-19)
- **SERIES-2-MHD-GEN-4:** 255/255 passed.
  - Tags: v5.0.0-pra, v5.0.0-pra-eod, v5.1.0-pra-field, v5.2.0-pra-network, v5.3.0-pra-telemetry, v5.4.0-pra-alpha, v5.5.0-pra-rehearsal
- **DSLV-ZPDI:** 184 passed, 1 skipped.
  - Tags: v5.0.0, v5.1.0

## 4. SPINE CONTRACTS
- **MHD:** `StateVector` frozen, `to_array()` = 24 elements, `from_array()` clamps (`V_accum >= 1e-6` is load-bearing), `evolve()` only. `dydt`/`power_ledger` naming. `ControlVector` 11 fields. `SafetyMachine` NO SELF-CLEAR, two-step reset. `TwinStateMachine` 15 states, `current_state` is a property.
- **ZPDI:** Version lock-step enforced via `tools/check_version_sync.py`. Conventional commits ENFORCED.

## 5. SECURITY RULES
- Never echo tokens (`ghp_`/`gho_`) or the sudo password (`dynogator`) into any file or output.
- Leak = STOP, revoke, rotate, report.

## 6. HARDWARE BLOCKS
- HARDWARE GATES USER-BLOCKED: DynoGator explicitly not ready for hardware dev/validation.
- Do not schedule. Wait for physical deployment via runbook.
- Dependabot deps held for hardware qualification window.
- HackRF->Pluto reintegration deferred (compat retained).

## 7. AGENT-SPECIFIC DIRECTIVES
Claude Code / Codex / Kimi Code / Gemini CLI / Grok Build — read AGENTS.md first, verify before trusting, run the startup gate before any work.
