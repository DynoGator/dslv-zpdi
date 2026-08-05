#!/bin/bash
if [ -f "$(dirname "${BASH_SOURCE[0]}")/.debug_mode" ]; then
    set -x
fi

echo "Initiating 2-second ramp-up pause before directory resolution..."
sleep 2

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$REPO" ]; then
    echo "CRITICAL: REPO directory not found!"
    exit 1
fi
cd "$REPO" || exit 1

echo "Directory resolved. Buffering for 2 seconds..."
sleep 2

if [ ! -f ".venv/bin/activate" ]; then
    echo "CRITICAL: .venv/bin/activate not found. Is environment setup?"
    exit 1
fi
source .venv/bin/activate

echo "Venv activated. Buffering for 2 seconds..."
sleep 2

# Mirror GitHub master package layout (src/dslv_zpdi) + mobile overlays
export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"
if [ -f ".debug_mode" ]; then
    export ZPDI_LOG_LEVEL="DEBUG"
else
    export ZPDI_LOG_LEVEL="INFO"
fi
echo "PYTHONPATH and LOG_LEVEL set. Buffering for 2 seconds before daemon start..."
sleep 2

echo "Starting dslv-zpdi daemon (package layout)..."
python3 zpdi_mobile_node.py
echo ""
echo "========================================"
echo ">>> DAEMON EXITED OR CRASHED (Code $?) <<<"
echo "Keeping window open for 60 seconds..."
echo "========================================"
sleep 60
