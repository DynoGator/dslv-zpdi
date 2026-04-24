#!/usr/bin/env bash
# DSLV-ZPDI email-send launcher (desktop icon entry point).
#
# Runs the Python sender with the user's saved config, regenerating the
# map first so the attachment is fresh. If the config is missing, opens
# the GUI configurator instead so the user lands in the right place.
set -Eeuo pipefail

REPO="/home/dynogator/dslv-zpdi"
PY="$REPO/venv/bin/python"
CFG="$HOME/.config/dslv-zpdi/email.yaml"
LOG="$REPO/logs/mailer.log"

mkdir -p "$REPO/logs"
export PYTHONIOENCODING=utf-8
export LANG="${LANG:-en_US.UTF-8}"
export LC_ALL="${LC_ALL:-en_US.UTF-8}"

{
    echo "====================================================="
    echo "[mailer $(date -Iseconds)] send_now starting"
    echo "====================================================="

    if [ ! -f "$CFG" ]; then
        echo "[mailer] no config at $CFG — opening configurator"
        exec "$PY" "$REPO/tools/mailer/configure.py"
    fi

    cd "$REPO"
    "$PY" tools/mailer/send_data.py --regen-map
    rc=$?
    echo "[mailer $(date -Iseconds)] send_now exit=$rc"
    exit $rc
} 2>&1 | tee -a "$LOG"
