#!/usr/bin/env bash
# DSLV-ZPDI map launcher (desktop icon entry point).
#
# (Re)generates the satellite map HTML then opens it in the default
# browser. If map generation fails the existing file is opened anyway
# so the user still sees *something* rather than a blank click.
set -Eeuo pipefail

REPO="/home/dynogator/dslv-zpdi"
PY="$REPO/venv/bin/python"
OUT="$HOME/.local/share/dslv-zpdi/map.html"
LOG="$REPO/logs/map.log"

mkdir -p "$(dirname "$OUT")" "$REPO/logs"
export PYTHONIOENCODING=utf-8
export LANG="${LANG:-en_US.UTF-8}"
export LC_ALL="${LC_ALL:-en_US.UTF-8}"

{
    echo "====================================================="
    echo "[map $(date -Iseconds)] open_map starting"
    echo "====================================================="
    cd "$REPO"
    if ! "$PY" tools/mapping/render_map.py --out "$OUT" \
            --max-primary 2000 --max-secondary 2000; then
        echo "[map] WARN: render failed — opening previous map if present"
    fi
    if [ -f "$OUT" ]; then
        if command -v xdg-open >/dev/null 2>&1; then
            xdg-open "file://$OUT" >/dev/null 2>&1 &
        else
            "$PY" -m webbrowser "file://$OUT"
        fi
        echo "[map] opened $OUT"
    else
        echo "[map] FAIL: no map file to open"
        exit 1
    fi
} 2>&1 | tee -a "$LOG"
