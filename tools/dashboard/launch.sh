#!/usr/bin/env bash
# DSLV-ZPDI Dashboard launcher
set -Eeuo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO/tools"

# Rich/Unicode output (waterfall glyphs, banners) crashes on startup
# when stdout reports a latin-1 codec — which happens inside lxterminal
# -e spawned from a detached session. Force UTF-8 + a sane LANG/LC_ALL.
export PYTHONIOENCODING=utf-8
export LANG="${LANG:-en_US.UTF-8}"
export LC_ALL="${LC_ALL:-en_US.UTF-8}"

# Settle pause: terminal emulator may need a moment to finish initialising
# before the Python TUI takes over the pty.
sleep 3

exec "$REPO/venv/bin/python" -m dashboard "$@"
