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

echo "Starting zpdi supervisor (independent proot session)..."
nohup "$PROOT_DISTRO" login debian -- bash "$PROJECT_DIR/supervisor.sh" > /dev/null 2>&1 &
SPID=$!

echo "====================================================="
echo "ZPDI SUPERVISOR LAUNCHED (PID: $SPID)"
echo "  Supervisor log: $PROJECT_DIR/logs/supervisor.log"
echo "  Daemon log:     $PROJECT_DIR/logs/daemon.log"
echo "====================================================="
