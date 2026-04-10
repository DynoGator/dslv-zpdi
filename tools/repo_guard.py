#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)
    raise SystemExit(1)

def warn(msg: str) -> None:
    print(f"[WARN] {msg}")

def ok(msg: str) -> None:
    print(f"[OK] {msg}")

def read_text(path: Path) -> str:
    if not path.is_file():
        fail(f"Missing file: {path}")
    return path.read_text(encoding="utf-8", errors="ignore")

required = [
    ROOT / "repo_manifest.yaml",
    ROOT / "pyproject.toml",
    ROOT / "Dockerfile",
    ROOT / "install_dslv_zpdi.sh",
    ROOT / "tools" / "orphan_checker.py",
    ROOT / "tools" / "check_version_sync.py",
    ROOT / "tests" / "test_pipeline.py",
]

for path in required:
    if not path.exists():
        fail(f"Required file missing: {path.relative_to(ROOT)}")

# 1) No sys.path hacks in tests
for path in (ROOT / "tests").rglob("test_*.py"):
    text = read_text(path)
    if "sys.path.insert" in text or "sys.path.append" in text:
        fail(f"Path injection found in test file: {path.relative_to(ROOT)}")
ok("No sys.path mutation found in tests")

# 2) Docker contract must mirror package-truth flow
docker = read_text(ROOT / "Dockerfile")
required_docker_bits = [
    "pip install --no-cache-dir -e '.[dev]'",
    "python -m pip check",
    "pytest -q tests",
    "python tools/orphan_checker.py",
    "python tools/check_version_sync.py",
    "python tools/repo_guard.py",
]
for needle in required_docker_bits:
    if needle not in docker:
        fail(f"Dockerfile missing required validation step: {needle}")
if "ENV PYTHONPATH=" in docker:
    fail("Dockerfile still sets PYTHONPATH")
ok("Docker validation contract looks sane")

# 3) Check for correct namespace
if not (ROOT / "src" / "dslv_zpdi").is_dir():
    fail("Project namespace dslv_zpdi missing in src/")
ok("Project namespace dslv_zpdi found")

# 4) Check for internal imports using new namespace
src_files = list((ROOT / "src" / "dslv_zpdi").rglob("*.py"))
for path in src_files:
    if path.name == "__init__.py":
        continue
    text = read_text(path)
    # Basic check for layer/watchdog imports without dslv_zpdi prefix
    if re.search(r"from (layer[1-3]_ingestion|layer[1-3]_core|layer[1-3]_telemetry|watchdog)", text):
         fail(f"Bare layer/watchdog import found in {path.relative_to(ROOT)}. Use dslv_zpdi namespace.")
ok("All internal imports use the dslv_zpdi namespace")

print("[OK] Repo guard passed")
