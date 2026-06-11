# DSLV-ZPDI Documentation Index

This is the map of project documentation. The **source of truth** for current
development is the repository root (see `AGENTS.md`, `CONTRIBUTING.md`,
`MASTER_SPEC.md`, `V3_DSLV-ZPDI_LIVING_MASTER.md`, `repo_manifest.yaml`).

## Canonical law layer (repo root)

| File | Purpose |
| --- | --- |
| `../MASTER_SPEC.md` | Canonical specification law layer. |
| `../V3_DSLV-ZPDI_LIVING_MASTER.md` | Living master architecture/spec document. |
| `../repo_manifest.yaml` | Validation contract and repository guardrails. |
| `../AGENTS.md` | Agent behavior and operating directives. |
| `../CONTRIBUTING.md` | SPEC-ID, testing, and commit protocol. |
| `../CHANGELOG.md` | Release history (Keep a Changelog format). |

## Collaboration & process

| Path | Purpose |
| --- | --- |
| [collaboration/README.md](collaboration/README.md) | Shared operating procedure for all agents. |
| [collaboration/NEXT_STEPS.md](collaboration/NEXT_STEPS.md) | Active forward development plan. |
| [collaboration/TURNOVER_TEMPLATE.md](collaboration/TURNOVER_TEMPLATE.md) | Template for root-level turnover notes. |

Per protocol, **current** turnover notes live at the repo root as
`TURNOVER_YYYY-MM-DD_<topic>.md` and are **not** moved into `docs/`.

## Architecture & hardware

| Path | Purpose |
| --- | --- |
| [ARCH-PHASE-2A-PIVOT.md](ARCH-PHASE-2A-PIVOT.md) | Phase 2A architecture pivot. |
| [HARDWARE_CHANGE_JUSTIFICATION.md](HARDWARE_CHANGE_JUSTIFICATION.md) | Rationale for hardware changes. |
| [LBE-1421_WIRING.md](LBE-1421_WIRING.md) | GPSDO dual-output wiring (PPS + 10 MHz). |
| [RF_MAGNETIC_SHIELDING.md](RF_MAGNETIC_SHIELDING.md) | RF/magnetic shielding notes. |
| [RADONEYE_GATT_MAP.md](RADONEYE_GATT_MAP.md) | RadonEye RD200P BLE GATT map (SPEC-015). |
| [PIXEL_NODE_SETUP.md](PIXEL_NODE_SETUP.md) | Pixel 9 Pro XL Tier 2 node setup (SPEC-016). |

## Specifications

`../specs/` holds the formal `SPEC-*.md` files (57 documents). Every class,
method, and architectural decision maps to one of these via docstrings, enforced
by `tools/orphan_checker.py`.

## Build guides

| Path | Purpose |
| --- | --- |
| [build-guides/README.md](build-guides/README.md) | Build-guide index. Markdown is canonical; PDFs are generated derivatives. |

## Audits

| Path | Purpose |
| --- | --- |
| `audits/` | Repository audit and hardening reports. |

## Validation evidence

| Path | Purpose |
| --- | --- |
| [validation-logs/](validation-logs/) | Committed validation evidence snapshots (must be secret-free). |

## Archived / historical

| Path | Purpose |
| --- | --- |
| [archive/](archive/) | Superseded session reports kept for history. |
| `KIMI_*.md`, `KIMI_CLOSEOUT_*.txt` | Phase 2B intake/closeout working notes from the Kimi agent session. Historical; not source of truth. |
