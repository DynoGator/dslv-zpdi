#!/bin/bash
cd /root/dslv-zpdi
source .venv/bin/activate
echo "Starting dslv-zpdi daemon..."
python3 zpdi_mobile_node.py
echo ""
echo "========================================"
echo ">>> DAEMON EXITED OR CRASHED (Code $?) <<<"
echo "Keeping window open for 60 seconds..."
echo "========================================"
sleep 60
