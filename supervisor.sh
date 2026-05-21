#!/bin/bash
# dslv-zpdi daemon supervisor.
#
# Runs in the FOREGROUND inside a proot session so the proot process stays
# alive (required — proot --kill-on-exit kills all tracees on exit, so the
# daemon must run under a persistent proot session, not an orphaned one).
#
# Called by 99-start-zpdi.sh (Termux:Boot) and by launch_daemon.sh.
# Do NOT call this directly from an interactive terminal unless you want
# the supervisor to occupy that terminal.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

source .venv/bin/activate
mkdir -p logs

DAEMONPID=.zpdi_daemon.pid
LOG=logs/supervisor.log

_log() { echo "$(date '+%Y-%m-%d %H:%M:%S') [zpdi-supervisor] $*" >> "$LOG"; }

_stop() {
    _log "stop signal received"
    if [ -f "$DAEMONPID" ]; then
        kill -SIGTERM "$(cat "$DAEMONPID")" 2>/dev/null || true
        sleep 1
        rm -f "$DAEMONPID"
    fi
    _log "supervisor exiting"
    exit 0
}
trap _stop SIGTERM SIGINT

backoff=2
_log "supervisor started (pid=$$)"

while true; do
    # Clear any SWMR lock left by a prior crash before reopening the file.
    [ -f data/zpdi_stream.h5 ] && h5clear -s data/zpdi_stream.h5 2>/dev/null || true

    python3 zpdi_mobile_node.py >> logs/daemon.log 2>&1 &
    dpid=$!
    echo "$dpid" > "$DAEMONPID"
    _log "daemon started (pid=$dpid)"

    wait "$dpid" 2>/dev/null
    rc=$?
    rm -f "$DAEMONPID"
    _log "daemon exited rc=$rc"

    # SIGTERM (143) or SIGINT (130) from our own _stop handler — exit cleanly.
    if [ "$rc" -eq 143 ] || [ "$rc" -eq 130 ]; then
        _log "clean shutdown — supervisor exiting"
        exit 0
    fi

    _log "restarting in ${backoff}s"
    sleep "$backoff"
    backoff=$(( backoff < 60 ? backoff * 2 : 60 ))
done
