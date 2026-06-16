#!/data/data/com.termux/files/usr/bin/bash
# dslv-zpdi Termux:Boot auto-start script
#
# INSTALLATION
#   Copy or symlink this file into ~/.termux/boot/ on the Android device:
#
#     mkdir -p ~/.termux/boot
#     cp /root/dslv-zpdi/termux-boot/99-start-zpdi.sh ~/.termux/boot/
#     chmod +x ~/.termux/boot/99-start-zpdi.sh
#
#   Then enable Termux:Boot in Android settings so Termux:Boot is allowed
#   to run on device startup (battery optimisation must be disabled for the
#   Termux:Boot app).
#
# HOW IT WORKS
#   Termux:Boot executes scripts in ~/.termux/boot/ after the device boots.
#   This script runs in the Termux environment (NOT inside proot).
#
#   1. Acquires an Android wake-lock so the CPU stays alive during collection.
#   2. Launches supervisor.sh in an INDEPENDENT proot-distro session.
#      supervisor.sh is the foreground process of that proot session,
#      so proot (--kill-on-exit) will not kill the daemon when this script
#      exits.  nohup + & puts the whole proot in the background so
#      Termux:Boot can finish its own boot sequence.
#   3. Logs the boot event to ~/.termux/boot/zpdi-boot.log.
#
# TROUBLESHOOTING
#   - If the daemon is not running after boot, check:
#       ~/.termux/boot/zpdi-boot.log
#       /root/dslv-zpdi/logs/supervisor.log
#       /root/dslv-zpdi/logs/daemon.log
#   - Run `proot-distro login debian -- pgrep -a python3` to verify.
#   - Ensure Termux:Boot has "unrestricted battery usage" in Android settings.

set -euo pipefail

BOOT_LOG="$HOME/.termux/boot/zpdi-boot.log"
PROOT_DISTRO="/data/data/com.termux/files/usr/bin/proot-distro"
PROJECT_DIR="/root/dslv-zpdi"
SUPERVISOR="$PROJECT_DIR/supervisor.sh"

_log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [zpdi-boot] $*" >> "$BOOT_LOG"
}

# Rotate boot log at 1 MB to prevent unbounded growth
if [ -f "$BOOT_LOG" ] && [ "$(stat -c %s "$BOOT_LOG" 2>/dev/null || echo 0)" -gt 1048576 ]; then
    mv "$BOOT_LOG" "${BOOT_LOG}.old"
fi

_log "Boot event received"

# --- 1. Acquire wake-lock ---
# Prevents Android from suspending the CPU and killing Termux while the
# daemon is collecting sensor data.
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
    _log "wake-lock acquired"
else
    _log "WARNING: termux-wake-lock not found — install Termux:API"
fi

# --- 2. Stop any stale processes from before the reboot ---
pkill -SIGTERM -f "supervisor.sh" 2>/dev/null || true
pkill -SIGTERM -f "zpdi_mobile_node.py" 2>/dev/null || true
sleep 1
pkill -SIGKILL -f "zpdi_mobile_node.py" 2>/dev/null || true

# --- 3. Clear any stale HDF5 SWMR lock ---
if [ -f "$PROJECT_DIR/data/zpdi_stream.h5" ]; then
    h5clear -s "$PROJECT_DIR/data/zpdi_stream.h5" 2>/dev/null || true
    _log "HDF5 SWMR lock cleared"
fi

# --- 4. Verify proot-distro is available ---
if [ ! -x "$PROOT_DISTRO" ]; then
    _log "ERROR: proot-distro not found at $PROOT_DISTRO — cannot start"
    exit 1
fi

# --- 5. Launch supervisor in an independent proot session ---
# supervisor.sh runs FOREGROUND inside proot; nohup + & puts the proot itself
# in the background so this script can exit without orphaning the daemon.
nohup "$PROOT_DISTRO" login debian -- bash "$SUPERVISOR" \
    >> "$BOOT_LOG" 2>&1 &
SPID=$!

_log "supervisor launched (proot PID=$SPID)"
_log "supervisor log: $PROJECT_DIR/logs/supervisor.log"
_log "daemon log:     $PROJECT_DIR/logs/daemon.log"
