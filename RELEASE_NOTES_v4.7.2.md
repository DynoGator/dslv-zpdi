# RELEASE_NOTES_v4.7.2.md

**DSLV-ZPDI v4.7.2** — Robustness, Reliability & Security Hardening (Phase 2A)

## Highlights
- Package version aligned to 4.7.2 in pyproject.toml and src/dslv_zpdi/__init__.py
- check_version_sync.py now matches canonical implementation from main (enforces README, CHANGELOG, RELEASE_NOTES, __version__)
- Mobile node (Rev 3.5 hardening on v4.7.2 base): full restructure to src/dslv_zpdi/ layout, pyproject-only deps
- All GitHub review issues addressed (type annotations, CI, docs, Docker, headers, etc.)
- Installers updated for new structure with detailed SUCCEEDED/FAILED reporting
- Added tool stubs and dedicated GitHub workflows (docker, security)

## Changes
- See CHANGELOG.md for detailed entries
- Version sync now strict across packaging, docs, and code

## Migration
- Use `pip install -e ".[dev]"` (no requirements.txt)
- Run `python tools/check_version_sync.py` to verify

For full details, see the re-evaluation fixes and REPORT.md.
