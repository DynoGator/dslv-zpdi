#!/bin/bash
# dslv-zpdi: Start (or restart) the zpdi supervisor in an independent proot session.
#
# WHY independent proot session: proot uses --kill-on-exit, so any daemon
# started inside a proot that subsequently exits will be killed. The supervisor
# must be the foreground process of a persistent proot instance.
#
# This script can be called from inside the current proot OR from Termux.

PROOT_DISTRO=/data/data/com.termux/files/usr/bin/proot-distro
PROJECT_DIR=/root/dslv-zpdi

echo "Stopping any existing zpdi supervisor and daemon..."
pkill -SIGTERM -f "supervisor.sh" 2>/dev/null || true
pkill -SIGTERM -f "zpdi_mobile_node.py" 2>/dev/null || true
sleep 2

# Belt-and-suspenders kill for anything that ignored SIGTERM
pkill -SIGKILL -f "zpdi_mobile_node.py" 2>/dev/null || true

# Clear any SWMR lock left by a crash
if [ -f "$PROJECT_DIR/data/zpdi_stream.h5" ]; then
    h5clear -s "$PROJECT_DIR/data/zpdi_stream.h5" 2>/dev/null || true
fi

echo "[*] Starting zpdi supervisor (independent proot session)..."
if nohup "$PROOT_DISTRO" login debian -- bash "$PROJECT_DIR/supervisor.sh" > /dev/null 2>&1 &
then
  SPID=$!
  echo "[SUCCEEDED] Launch independent proot supervisor (PID $SPID)"
  echo "  (New layout: PYTHONPATH=src or editable install assumed inside)"
else
  echo "[FAILED] Launch independent proot supervisor"
  echo "  Recommended corrective action: Check proot-distro is installed in Termux. Run 'proot-distro login debian -- bash -c \"cd /root/dslv-zpdi && source .venv/bin/activate && export PYTHONPATH=src && ./supervisor.sh\"' manually for debug. Ensure no previous daemon holding locks (h5clear)."
fi

echo "====================================================="
echo "ZPDI SUPERVISOR LAUNCHED (PID: $SPID)"
echo "  Supervisor log: $PROJECT_DIR/logs/supervisor.log"
echo "  Daemon log:     $PROJECT_DIR/logs/daemon.log"
echo "  (All new changes: pyproject deps + src/dslv_zpdi layout incorporated)"
echo "====================================================="
