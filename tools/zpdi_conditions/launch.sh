#!/usr/bin/env bash
# Launch the ZPDI_CONDITIONS local dashboard.
#
# This script is intentionally independent from the DSLV-ZPDI pipeline. It does
# not open SDR hardware, libiio, or any radio interface; it only makes HTTP
# requests to public weather and space-weather services.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV="${REPO_ROOT}/.venv"

# Prefer the project venv, fall back to system python if the venv is missing.
if [[ -x "${VENV}/bin/python" ]]; then
    PYTHON="${VENV}/bin/python"
else
    PYTHON="python3"
fi

# Terminal geometry friendly to a 10" 1280x800 touchscreen with a readable font.
export LINES=40
export COLUMNS=120

# Force UTF-8 so Rich borders and arrows render correctly on Raspberry Pi OS.
export PYTHONIOENCODING=utf-8
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# Make sure the local package is importable.
export PYTHONPATH="${REPO_ROOT}/tools:${PYTHONPATH:-}"

cd "${REPO_ROOT}"
exec "${PYTHON}" -m zpdi_conditions "$@"
