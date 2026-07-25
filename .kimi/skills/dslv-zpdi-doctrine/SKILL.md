# DSLV-ZPDI Agent Doctrine

## Description

Binding project doctrine for the DSLV-ZPDI Pixel 9 Pro XL Tier-2 C2 Control Node feature. This skill must be loaded and followed for every task in `/root/dslv-zpdi`.

## Instructions

Before any action, read:
1. `/root/dslv-zpdi/CREW_MEMORY.md`
2. `/root/dslv-zpdi/AGENTS.md`
3. `/root/dslv-zpdi/MASTER_SPEC.md`
4. `/root/dslv-zpdi/COLLABORATION_GUIDE.md`
5. `/data/data/com.termux/files/home/PIXEL_DEV_PLAN.md`
6. `/root/dslv-zpdi/SECURITY.md`

## Doctrine

- The Raspberry Pi 5 remains the canonical Tier-1 timing, SDR, and HDF5 authority.
- The Pixel is the DEFAULT control plane but NEVER required for the swarm.
- Existing Layer-1/2/3 metrology semantics must NOT change.
- All new behavior must be additive and feature-flagged.
- Local Pixel overlays live in `/root/dslv-zpdi-local/`, not the main repo.
- NEVER commit secrets. GitHub PAT lives in `/root/.config/dslv-zpdi/github_pat` (mode 600).
- NEVER expose arbitrary command execution or remote shell endpoints.
- C2 commands require Bearer auth, capability authorization, expiry, idempotency, and audit logging.
- HDF5 UI access is read-only through a bounded query adapter.
- The APK never receives GitHub tokens, agent credentials, or shell access.

## Workflow

1. Inspect before editing. State exact files you will change.
2. Produce a written design + test plan before writing code.
3. Work only in your assigned branch/worktree.
4. Source `/root/dslv-zpdi-local/scripts/start_dev_session.sh` before working.
5. Run `bash /root/dslv-zpdi-local/scripts/validate.sh` before and after changes.
6. Add tests for every new command and failure path.
7. Never merge, force-push, reset, or delete data without explicit approval.
8. Record unresolved assumptions instead of fabricating implementations.
9. Commit small, reviewable changes with Conventional Commits.
10. End each session with a turnover note.

## Forbidden Actions

- Do not modify `/root/dslv-zpdi/.env` to add secrets.
- Do not run `git reset --hard`.
- Do not force-push to `main`.
- Do not disable tests or reduce coverage floors.
- Do not add new dependencies without explicit approval.
- Do not expose services on `0.0.0.0` without security review.
- Do not write arbitrary shell execution into C2 endpoints.
- Do not make the Pixel the Tier-1 authority.
