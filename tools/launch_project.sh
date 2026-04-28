#!/usr/bin/env bash
# DSLV-ZPDI clean-boot launcher
#
# Kills every DSLV-ZPDI process (dashboard, pipeline, SDR conflicts),
# stops the systemd unit chain, validates the venv + HackRF, restarts
# the chain in order (tuning → preflight → pipeline), then opens the
# Operations Dashboard in a new terminal.
#
# Safe to invoke repeatedly — this is the "nuke and pave" entry point
# used by the desktop icon.

set -Eeuo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO/venv"
LOG="$REPO/logs/launch.log"
DASH="$REPO/tools/dashboard/launch.sh"

# tee -a will fail (and silently kill the desktop launch) if the parent dir
# doesn't exist; ensure it exists before redirection.
mkdir -p "$REPO/logs" 2>/dev/null || true
exec > >(tee -a "$LOG") 2>&1

STAMP() { date -Iseconds; }
SAY()   { printf "\033[1;36m[launch %s]\033[0m %s\n" "$(STAMP)" "$*"; }
OK()    { printf "\033[1;32m[launch %s] OK:\033[0m %s\n"   "$(STAMP)" "$*"; }
WARN()  { printf "\033[1;33m[launch %s] WARN:\033[0m %s\n" "$(STAMP)" "$*" >&2; }
DIE()   { printf "\033[1;31m[launch %s] FAIL:\033[0m %s\n" "$(STAMP)" "$*" >&2; exit 1; }

SAY "================================================================"
SAY "DSLV-ZPDI clean launch starting"
SAY "================================================================"

# Warm-up pause: only the slow auto-start path (boot) needs a long settle.
# When the user double-clicks the desktop launcher the desktop is already up,
# so a 15 s wait makes it look like the launcher is broken. Detect that case
# via DSLV_LAUNCH_QUICK=1 (set by the desktop entry) or an existing display.
if [ "${DSLV_LAUNCH_QUICK:-0}" = "1" ] \
   || { [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; }; then
    SAY "warm-up :: 3 s quick-launch settle (desktop session already up)"
    sleep 3
else
    SAY "warm-up :: 15 s settle pause (boot autostart path)"
    sleep 15
fi

# --- 1. Kill every user-space DSLV process ------------------------------
SAY "step 1/7 :: killing stale DSLV and SDR processes"

pkill -u "$USER" -f 'python -m dashboard'  2>/dev/null || true
pkill -u "$USER" -f 'dashboard/launch.sh'  2>/dev/null || true
pkill -u "$USER" -f 'dashboard/app.py'     2>/dev/null || true

pkill -u "$USER" -f 'dslv_zpdi.main_pipeline'    2>/dev/null || true
pkill -u "$USER" -f 'dslv_zpdi.capture_baseline' 2>/dev/null || true

SDR_PROCS=(gqrx SoapySDRUtil sdrangel rtl_tcp rtl_fm openwebrx
           airspy_rx hackrf_transfer hackrf_sweep hackrf_spectrum)
for proc in "${SDR_PROCS[@]}"; do
    if pgrep -x "$proc" >/dev/null 2>&1; then
        SAY "  - killing $proc"
        pkill -TERM -x "$proc" 2>/dev/null || true
    fi
done
sleep 2
for proc in "${SDR_PROCS[@]}"; do
    pkill -KILL -x "$proc" 2>/dev/null || true
done

# --- 2. Stop systemd service chain -------------------------------------
SAY "step 2/7 :: stopping dslv-zpdi systemd chain"
SUDO=""
if sudo -n true 2>/dev/null; then
    SUDO="sudo -n"
else
    WARN "passwordless sudo unavailable; systemd steps will be skipped"
fi
if [ -n "$SUDO" ]; then
    $SUDO systemctl stop dslv-zpdi.service           2>/dev/null || true
    sleep 3
    $SUDO systemctl stop dslv-zpdi-preflight.service 2>/dev/null || true
    sleep 3
    $SUDO systemctl stop dslv-zpdi-tuning.service    2>/dev/null || true
    sleep 3
    $SUDO systemctl stop dslv-zpdi-baseline.service  2>/dev/null || true
    sleep 5
fi

# --- 3. Validate venv --------------------------------------------------
SAY "step 3/7 :: validating venv"
[ -x "$VENV/bin/python" ] || DIE "venv missing at $VENV (run bootstrap.sh to rebuild)"
PYVER="$("$VENV/bin/python" --version 2>&1)"
OK "venv python: $PYVER"
"$VENV/bin/python" -c "import dslv_zpdi" 2>/dev/null && OK "dslv_zpdi importable" \
    || WARN "dslv_zpdi not importable (editable install may be broken)"
"$VENV/bin/python" -c "import dashboard" 2>/dev/null \
    && OK "dashboard package importable" \
    || ( cd "$REPO/tools" && "$VENV/bin/python" -c "import dashboard" 2>/dev/null \
         && OK "dashboard importable (from tools/)" \
         || WARN "dashboard package not importable" )
sleep 2

# --- 4. HackRF + driver sanity check -----------------------------------
SAY "step 4/7 :: HackRF and driver sanity"
if ! command -v hackrf_info >/dev/null 2>&1; then
    WARN "hackrf-tools not installed (apt install hackrf)"
else
    if HRF_OUT="$(hackrf_info 2>&1)"; then
        if echo "$HRF_OUT" | grep -q 'Found HackRF'; then
            SERIAL=$(echo "$HRF_OUT" | awk -F': *' '/Serial number/{print $2; exit}')
            REV=$(echo   "$HRF_OUT" | awk -F': *' '/Hardware Revision/{print $2; exit}')
            FW=$(echo    "$HRF_OUT" | awk -F': *' '/Firmware Version/{print $2; exit}')
            OK "HackRF detected: $REV  fw=$FW  s/n=${SERIAL: -12}"
        else
            WARN "hackrf_info succeeded but no device found — check USB cable / power"
        fi
    else
        WARN "hackrf_info failed:"
        echo "$HRF_OUT" | sed 's/^/    /'
    fi
fi

if ! groups "$USER" | grep -qw plugdev; then
    WARN "user $USER not in 'plugdev' group — HackRF may require sudo"
else
    OK "user in 'plugdev' — HackRF usable without sudo"
fi

sleep 3

if [ -e /lib/udev/rules.d/60-libhackrf0.rules ] \
   || [ -e /etc/udev/rules.d/53-hackrf.rules ]; then
    OK "HackRF udev rules present"
else
    WARN "no HackRF udev rules found (device may need sudo to open)"
fi
sleep 3

# --- 5. Reload + start chain in order ---------------------------------
if [ -n "$SUDO" ]; then
    SAY "step 5/7 :: starting dslv-zpdi chain (tuning → preflight → pipeline)"
    $SUDO systemctl daemon-reload
    sleep 3
    for unit in dslv-zpdi-tuning.service dslv-zpdi-preflight.service dslv-zpdi.service; do
        SAY "  - start $unit"
        $SUDO systemctl start "$unit" || WARN "failed to start $unit"
        # generous pause between dependent unit starts so each finishes init
        # before the next one is asked to come up
        sleep 5
    done
    sleep 5
else
    SAY "step 5/7 :: skipping systemd chain start (no sudo)"
fi

# --- 6. Verify chain health -------------------------------------------
SAY "step 6/7 :: verifying service health"
FAILED=0
for unit in dslv-zpdi-tuning dslv-zpdi-preflight dslv-zpdi; do
    STATE="$(systemctl is-active "$unit" 2>/dev/null || true)"
    case "$STATE" in
        active)   OK "$unit: active" ;;
        inactive) WARN "$unit: inactive"; FAILED=$((FAILED+1)) ;;
        *)        WARN "$unit: $STATE"; FAILED=$((FAILED+1)) ;;
    esac
done

if [ "$FAILED" -gt 0 ]; then
    WARN "$FAILED unit(s) not active — showing last 20 lines of dslv-zpdi journal"
    journalctl -u dslv-zpdi -n 20 --no-pager 2>/dev/null || true
fi
sleep 3

# --- 7. Launch dashboard + waterfall second window --------------------
SAY "step 7/7 :: launching operations dashboard and waterfall window"

TITLE_MAIN="DSLV-ZPDI :: DynoGatorLabs"
TITLE_WF="DSLV-ZPDI :: WATERFALL"

# Wait for display server to be ready before attempting to spawn terminals.
# On boot autostart the WM/X11 may not be fully up yet.
SAY "waiting for display server readiness..."
for _ds_wait in {1..30}; do
    if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
        if command -v xrandr >/dev/null 2>&1 && xrandr --current >/dev/null 2>&1; then
            OK "display server ready"
            break
        fi
    fi
    sleep 2
done
sleep 3

# Screen-aware geometry.
# - 5" DSI (800x480): compact terminals that actually fit the screen.
# - anything larger: the original wide layout.
SCREEN_W=0
SCREEN_H=0
if command -v xrandr >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
    read SCREEN_W SCREEN_H < <(xrandr --current 2>/dev/null \
        | awk '/\*/{print $1; exit}' | tr 'x' ' ' || true)
fi
SCREEN_W=${SCREEN_W:-0}
SCREEN_H=${SCREEN_H:-0}
if [ "${SCREEN_W:-0}" -le 1024 ] && [ "${SCREEN_H:-0}" -le 600 ] \
   && [ "${SCREEN_W:-0}" -gt 0 ]; then
    # 5" DSI: single fullscreen window, compact layout, no second terminal.
    # 92x28 keeps the waterfall visible at 800x480 with default lxterminal
    # font (dense enough to hit ~28-30 rows on most Pi OS installs).
    GEO_MAIN="92x28"
    GEO_WF="92x28"
    COMPACT_MODE=1
    SAY "detected small display (${SCREEN_W}x${SCREEN_H}) - compact layout enabled"
else
    GEO_MAIN="180x50"
    GEO_WF="140x34"
    COMPACT_MODE=0
fi
export DSLV_DASHBOARD_COMPACT="$COMPACT_MODE"

# Pick a GUI terminal emulator once; both windows use the same one.
TERMCMD=""
if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
    if command -v lxterminal >/dev/null 2>&1; then
        TERMCMD="lxterminal"
    elif command -v x-terminal-emulator >/dev/null 2>&1; then
        TERMCMD="x-terminal-emulator"
    elif command -v xterm >/dev/null 2>&1; then
        TERMCMD="xterm"
    fi
fi

spawn_terminal() {
    # $1 = title, $2 = geometry, $3..$N = command
    local title="$1"; shift
    local geo="$1"; shift
    case "$TERMCMD" in
        lxterminal)
            # --no-remote keeps each window as its own process, otherwise
            # lxterminal's single-instance daemon swallows the -e of
            # subsequent invocations and only one window actually opens.
            nohup lxterminal --no-remote --title="$title" --geometry="$geo" -e "$*" \
                >/dev/null 2>&1 & disown ;;
        x-terminal-emulator)
            nohup x-terminal-emulator -T "$title" -e "$@" \
                >/dev/null 2>&1 & disown ;;
        xterm)
            nohup xterm -T "$title" -geometry "$geo" -e "$@" \
                >/dev/null 2>&1 & disown ;;
    esac
}

if [ -z "$TERMCMD" ]; then
    SAY "  - no GUI terminal detected; running dashboard inline (no second window)"
    exec "$DASH"
fi

if [ "$COMPACT_MODE" = "1" ]; then
    # 5" DSI: spawn waterfall first, then dashboard. Both are full-screen
    # under the compositor and the user alt-tabs (or workspace-switches)
    # between them. Skipping the waterfall window here was the original
    # "waterfall doesn't start" bug.
    SAY "  - opening waterfall window in compact mode ($TERMCMD)"
    spawn_terminal "$TITLE_WF" "$GEO_WF" \
        "$DASH" --waterfall-only --no-boot
    sleep 5

    SAY "  - opening operations dashboard in compact mode ($TERMCMD)"
    case "$TERMCMD" in
        lxterminal)
            nohup lxterminal --no-remote --title="$TITLE_MAIN" --geometry="$GEO_MAIN" -e "$DASH" \
                >/dev/null 2>&1 & disown ;;
        x-terminal-emulator)
            nohup x-terminal-emulator -T "$TITLE_MAIN" -e "$DASH" \
                >/dev/null 2>&1 & disown ;;
        xterm)
            nohup xterm -T "$TITLE_MAIN" -geometry "$GEO_MAIN" -fa 'Monospace' -fs 9 -e "$DASH" \
                >/dev/null 2>&1 & disown ;;
    esac
    sleep 3
    OK "launch complete — compact: waterfall + dashboard dispatched"
else
    # 7a — waterfall second window FIRST so it's visible under the dashboard
    SAY "  - opening waterfall window ($TERMCMD)"
    spawn_terminal "$TITLE_WF" "$GEO_WF" \
        "$DASH" --waterfall-only --no-boot
    # generous pause so the first window registers on the display server
    # before we fire the second one
    sleep 5

    # 7b — main dashboard (spawned the same way so both survive under
    # lxterminal's single-instance behavior)
    SAY "  - opening operations dashboard ($TERMCMD)"
    case "$TERMCMD" in
        lxterminal)
            nohup lxterminal --no-remote --title="$TITLE_MAIN" --geometry="$GEO_MAIN" -e "$DASH" \
                >/dev/null 2>&1 & disown ;;
        x-terminal-emulator)
            nohup x-terminal-emulator -T "$TITLE_MAIN" -e "$DASH" \
                >/dev/null 2>&1 & disown ;;
        xterm)
            nohup xterm -T "$TITLE_MAIN" -geometry "$GEO_MAIN" -e "$DASH" \
                >/dev/null 2>&1 & disown ;;
    esac
    sleep 3
    OK "launch complete — dashboard + waterfall windows dispatched"
fi
