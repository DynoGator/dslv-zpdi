#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Joseph R. Fross

"""repo_guard.py - Git hygiene and repo validation stub (for CI).
Run as: python tools/repo_guard.py
"""
import sys
import subprocess
from pathlib import Path

def main():
    print('[repo_guard] Checking git hygiene and structure...')
    errors = []
    # Check no agent homes tracked
    result = subprocess.run(['git', 'ls-files', '--', 'CLAUDE-HOME', 'GEM-HOME', '*HOME/'], capture_output=True, text=True)
    if result.stdout.strip():
        errors.append('Agent home dirs still tracked in git.')
    # Check pyproject present
    if not Path('pyproject.toml').exists():
        errors.append('pyproject.toml missing.')
    # Check no requirements.txt (deprecated)
    if Path('requirements.txt').exists():
        errors.append('Stale requirements.txt present (use pyproject).')
    if errors:
        print('ERRORS:', errors)
        sys.exit(1)
    print('[repo_guard] OK')
    sys.exit(0)

if __name__ == '__main__':
    main()
