# Agent: .kimi — project doctrine is binding
# DSLV-ZPDI Agent Doctrine — Binding Rules for Autonomous Agents

> **READ THIS FILE FIRST.**
> Violations risk hardware damage, data corruption, or security compromise.

## MANDATORY READING BEFORE ANY ACTION

Read these files in order and confirm you have read them:

1. `/root/dslv-zpdi/CREW_MEMORY.md` — live crew state, current branch, next step
2. `/root/dslv-zpdi/AGENTS.md` — project conventions
3. `/root/dslv-zpdi/MASTER_SPEC.md` — canonical architecture specification
4. `/root/dslv-zpdi/COLLABORATION_GUIDE.md` — branch/merge/commit rules
5. `/data/data/com.termux/files/home/PIXEL_DEV_PLAN.md` — current Pixel C2 node trajectory
6. `/root/dslv-zpdi/SECURITY.md` — security policy

## CURRENT MISSION

The active development track is the **Pixel 9 Pro XL Tier-2 C2 Control Node** feature:

- Native Android command dashboard (PWA now, APK later)
- Secure C2 control-plane backend
- Read-only HDF5 telemetry query adapter
- Local cluster network anchor via LocalOnlyHotspot
- Tier-2 metrology contribution continues in background

## SCOPE BOUNDARIES — NON-NEGOTIABLE

1. The Raspberry Pi 5 remains the canonical Tier-1 timing, SDR, and HDF5 authority.
2. The Pixel is the DEFAULT control plane but is NEVER required for the swarm to function.
3. Existing Layer-1, Layer-2, and Layer-3 metrology semantics must NOT change.
4. All new behavior must be additive and feature-flagged.
5. Main repo code changes must be minimal, reviewable, and justified.
6. Local Pixel-specific overlays live in `/root/dslv-zpdi-local/`, not in the main repo.

## SECURITY — ZERO EXCEPTIONS

1. NEVER commit secrets, credentials, tokens, or private keys.
2. NEVER store the GitHub PAT in `.env`. It lives in `/root/.config/dslv-zpdi/github_pat` (mode 600).
3. NEVER expose arbitrary command execution or remote shell endpoints.
4. C2 commands require Bearer auth, capability authorization, expiry, idempotency, and audit logging.
5. HDF5 access from the UI is read-only through a bounded query adapter.
6. The Android APK never receives GitHub tokens, agent credentials, or shell access.
7. Prefer Unix sockets / localhost over network ports when possible.

## WORKFLOW — FOLLOW EXACTLY

1. INSPECT before editing. State exact files you will change.
2. Produce a written design + test plan before writing code.
3. Work only in your assigned branch/worktree.
4. Source `/root/dslv-zpdi-local/scripts/start_dev_session.sh` before working.
5. Run `bash /root/dslv-zpdi-local/scripts/validate.sh` before and after changes.
6. Add tests for every new command and failure path.
7. Never merge, force-push, reset, or delete data without explicit approval.
8. Record unresolved assumptions instead of fabricating implementations.
9. Commit small, reviewable changes with Conventional Commits.
10. End each session with a turnover note: changed files, test results, known failures, security implications, next action.

## VALIDATION PIPELINE

```bash
source /root/dslv-zpdi-local/scripts/start_dev_session.sh
bash /root/dslv-zpdi-local/scripts/validate.sh
```

## AGENT ROLES

- **Claude Code**: Lead architect / security reviewer. Owns multi-file design and threat modeling.
- **Codex CLI**: Terminal executor / engineer. Owns implementation and validation.
- **Kimi Code**: High-output craftsman. Owns boilerplate, refactors, and SPEC compliance.
- **Grok Build**: Edge-case analyst / prototyping. Owns failure-mode analysis and performance review.
- **Gemini CLI**: QA / test engineer. Owns test plans and final validation.

## FORBIDDEN ACTIONS

- Do not modify `/root/dslv-zpdi/.env` to add secrets.
- Do not run `git reset --hard`.
- Do not force-push to `main` or shared branches.
- Do not disable tests or reduce coverage floors.
- Do not add new dependencies without explicit approval.
- Do not expose services on `0.0.0.0` without security review.
- Do not write arbitrary shell execution into C2 endpoints.
- Do not make the Pixel the Tier-1 authority.

## COMMUNICATION

- Be concise. State what you did, what passed, and what is blocked.
- If a requirement conflicts with this doctrine, STOP and ask for clarification.
- Never claim hardware validation passed unless you ran the command and captured output.
