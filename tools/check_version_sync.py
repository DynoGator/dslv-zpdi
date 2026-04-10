#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)
    raise SystemExit(1)

def read_text(path: Path) -> str:
    if not path.is_file():
        fail(f"Missing file: {path}")
    return path.read_text(encoding="utf-8", errors="ignore")

pyproject = ROOT / "pyproject.toml"
readme = ROOT / "README.md"
changelog = ROOT / "CHANGELOG.md"

pyproject_text = read_text(pyproject)
readme_text = read_text(readme)
changelog_text = read_text(changelog)

m = re.search(r'^\s*version\s*=\s*"([^"]+)"', pyproject_text, re.M)
if not m:
    fail("Could not find version in pyproject.toml")
project_version = m.group(1)

# Check README revision
rm = re.search(r"Revision:\s*\*?\*?Rev\s*([0-9][0-9A-Za-z.\-_]+)", readme_text)
if not rm:
    # Try another common pattern
    rm = re.search(r"Rev\s*([0-9][0-9A-Za-z.\-_]+)", readme_text)
if not rm:
    fail("Could not find README revision line")
readme_version = rm.group(1)

# Check RELEASE_NOTES
release_notes = sorted(ROOT.glob("RELEASE_NOTES_v*.md"))
if not release_notes:
    fail("No RELEASE_NOTES_v*.md file found")

release_note_versions = []
for p in release_notes:
    mm = re.search(r"RELEASE_NOTES_v([0-9][0-9A-Za-z.\-_]+)\.md$", p.name)
    if mm:
        release_note_versions.append(mm.group(1))

if project_version not in release_note_versions:
    fail(f"No release note found matching pyproject version {project_version}. Found: {release_note_versions}")

if readme_version != project_version:
    fail(f"README revision {readme_version} does not match pyproject version {project_version}")

if project_version not in changelog_text:
    fail(f"CHANGELOG.md does not mention current version {project_version}")

print(f"[OK] Version sync clean: {project_version}")
