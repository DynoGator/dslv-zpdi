#!/bin/bash
# dslv-zpdi daemon supervisor.
#
# Manages three services inside a proot session (foreground process):
#   1. tier1_ingestion_server.py       — WSS receiver on ZPDI_SERVER_PORT (default 8443)
#   2. tools/dashboard/web_server.py   — Flask status dashboard on DSLV_WEBDASH_PORT (default 8080)
#   3. zpdi_mobile_node.py             — Tier-2 mobile daemon (health-monitored, auto-restart)
#
# Runs in the FOREGROUND inside a proot session so the proot process stays
# alive (required — proot --kill-on-exit kills all tracees on exit, so the
# daemon must run under a persistent proot session, not an orphaned one).
#
# Called by termux-boot/99-start-zpdi.sh and by launch_daemon.sh.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

source .venv/bin/activate

# Export all .env vars to child processes.
set -a
[ -f .env ] && source .env
set +a

mkdir -p logs data output/primary output/secondary

DAEMONPID=.zpdi_daemon.pid
TIER1PID=.zpdi_tier1.pid
WEBDASHPID=.zpdi_webdash.pid
LOG=logs/supervisor.log

_log() { echo "$(date '+%Y-%m-%d %H:%M:%S') [zpdi-supervisor] $*" >> "$LOG"; }

_stop() {
    _log "stop signal received"
    if [ -f "$DAEMONPID" ]; then
        kill -SIGTERM "$(cat "$DAEMONPID")" 2>/dev/null || true
        sleep 1
        kill -SIGKILL "$(cat "$DAEMONPID")" 2>/dev/null || true
        rm -f "$DAEMONPID"
    fi
    if [ -f "$TIER1PID" ]; then
        kill -SIGTERM "$(cat "$TIER1PID")" 2>/dev/null || true
        rm -f "$TIER1PID"
    fi
    if [ -f "$WEBDASHPID" ]; then
        kill -SIGTERM "$(cat "$WEBDASHPID")" 2>/dev/null || true
        rm -f "$WEBDASHPID"
    fi
    _log "supervisor exiting"
    exit 0
}
trap _stop SIGTERM SIGINT

_log "supervisor started (pid=$$)"

# ---------------------------------------------------------------------------
# Start ancillary services (one-time at supervisor startup).
# ---------------------------------------------------------------------------

_start_tier1() {
    python3 tier1_ingestion_server.py >> logs/tier1_server.log 2>&1 &
    local pid=$!
    echo "$pid" > "$TIER1PID"
    _log "tier1 server started (pid=$pid) on :${ZPDI_SERVER_PORT:-8443}"
}

_start_webdash() {
    DSLV_WEBDASH_HOST="${DSLV_WEBDASH_HOST:-0.0.0.0}" \
    DSLV_WEBDASH_PORT="${DSLV_WEBDASH_PORT:-8080}" \
    DSLV_PRIMARY_OUTPUT_DIR="${DSLV_PRIMARY_OUTPUT_DIR:-./output/primary}" \
    DSLV_SECONDARY_OUTPUT_DIR="${DSLV_SECONDARY_OUTPUT_DIR:-./output/secondary}" \
    python3 -m tools.dashboard.web_server >> logs/web_server.log 2>&1 &
    local pid=$!
    echo "$pid" > "$WEBDASHPID"
    _log "web dashboard started (pid=$pid) on :${DSLV_WEBDASH_PORT:-8080}"
}

_start_tier1
_start_webdash

# ---------------------------------------------------------------------------
# Main loop: manage zpdi_mobile_node.py with health monitoring.
# Also monitors and restarts ancillary services if they die.
# ---------------------------------------------------------------------------
backoff=2

while true; do
    # Restart ancillary services if they exited unexpectedly.
    if [ -f "$TIER1PID" ] && ! kill -0 "$(cat "$TIER1PID")" 2>/dev/null; then
        _log "tier1 server exited unexpectedly — restarting"
        _start_tier1
    fi
    if [ -f "$WEBDASHPID" ] && ! kill -0 "$(cat "$WEBDASHPID")" 2>/dev/null; then
        _log "web dashboard exited unexpectedly — restarting"
        _start_webdash
    fi

    # Clear any SWMR lock left by a prior crash before reopening the HDF5 file.
    [ -f data/zpdi_stream.h5 ] && h5clear -s data/zpdi_stream.h5 2>/dev/null || true

    # Truncate old health log so the age check starts fresh for this daemon
    # instance. A stale health.jsonl from a previous run would trigger an
    # immediate watchdog kill before the new daemon writes its first heartbeat.
    : > logs/health.jsonl 2>/dev/null || true

    python3 zpdi_mobile_node.py >> logs/daemon.log 2>&1 &
    dpid=$!
    echo "$dpid" > "$DAEMONPID"
    _log "daemon started (pid=$dpid)"

    # Grace period: the first health heartbeat is written at t≈30s.
    # Give it 35s before enforcing staleness checks.
    sleep 35

    # Poll while daemon is alive; check health log age every 5s.
    while kill -0 "$dpid" 2>/dev/null; do
        # Check ancillary services inside the inner loop too.
        if [ -f "$TIER1PID" ] && ! kill -0 "$(cat "$TIER1PID")" 2>/dev/null; then
            _log "tier1 server exited (inner) — restarting"
            _start_tier1
        fi
        if [ -f "$WEBDASHPID" ] && ! kill -0 "$(cat "$WEBDASHPID")" 2>/dev/null; then
            _log "web dashboard exited (inner) — restarting"
            _start_webdash
        fi

        if [ -f logs/health.jsonl ]; then
            health_age=$(( $(date +%s) - $(stat -c %Y logs/health.jsonl 2>/dev/null || echo 0) ))
            if [ "$health_age" -gt 90 ]; then
                _log "health stale ${health_age}s > 90s — killing daemon (pid=$dpid)"
                kill -SIGTERM "$dpid" 2>/dev/null || true
                sleep 2
                kill -SIGKILL "$dpid" 2>/dev/null || true
                break
            fi
        else
            _log "health log missing — killing daemon (pid=$dpid)"
            kill -SIGTERM "$dpid" 2>/dev/null || true
            sleep 2
            kill -SIGKILL "$dpid" 2>/dev/null || true
            break
        fi
        sleep 5
    done

    wait "$dpid" 2>/dev/null
    rc=$?
    rm -f "$DAEMONPID"
    _log "daemon exited rc=$rc"

    # SIGTERM (143) or SIGINT (130) from our own _stop handler — exit cleanly.
    if [ "$rc" -eq 143 ] || [ "$rc" -eq 130 ]; then
        _log "clean shutdown — supervisor exiting"
        exit 0
    fi

    _log "restarting daemon in ${backoff}s"
    sleep "$backoff"
    backoff=$(( backoff < 60 ? backoff * 2 : 60 ))
done
