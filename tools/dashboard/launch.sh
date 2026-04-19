#!/usr/bin/env bash
# DSLV-ZPDI Dashboard launcher
set -Eeuo pipefail

REPO=/home/dynogator/dslv-zpdi
cd "$REPO/tools"

exec "$REPO/venv/bin/python" -m dashboard "$@"
