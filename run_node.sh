#!/bin/bash
cd /root/dslv-zpdi
source .venv/bin/activate
# Mirror GitHub master package layout (src/dslv_zpdi) + mobile overlays
export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"
echo "Starting dslv-zpdi daemon (package layout)..."
python3 zpdi_mobile_node.py
echo ""
echo "========================================"
echo ">>> DAEMON EXITED OR CRASHED (Code $?) <<<"
echo "Keeping window open for 60 seconds..."
echo "========================================"
sleep 60
