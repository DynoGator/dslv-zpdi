#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Joseph R. Fross

"""check_version_sync.py - Verify __version__ matches pyproject.toml (stub for CI)."""
import sys
import tomllib
from pathlib import Path
import re

def main():
    pyproject = Path('pyproject.toml')
    if not pyproject.exists():
        print('pyproject.toml not found')
        sys.exit(1)
    data = tomllib.loads(pyproject.read_text())
    proj_ver = data.get('project', {}).get('version')
    # Look for __version__ in src/dslv_zpdi/__init__.py or similar
    init_files = list(Path('src').rglob('__init__.py'))
    found_ver = None
    for f in init_files:
        txt = f.read_text()
        m = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", txt)
        if m:
            found_ver = m.group(1)
            break
    if proj_ver and found_ver:
        if proj_ver != found_ver:
            print(f'Version mismatch: pyproject {proj_ver} vs code {found_ver}')
            sys.exit(1)
        print(f'[check_version_sync] Versions match: {proj_ver}')
    else:
        print('[check_version_sync] Version check skipped (no __version__ or pyproject version)')
    sys.exit(0)

if __name__ == '__main__':
    main()
