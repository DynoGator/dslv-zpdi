#!/bin/bash
# DSLV-ZPDI Launch Supervisor
# A robust, professional orchestrator for the DSLV-ZPDI Tier 1 pipeline.
set -e

# ==============================================================================
# 0. CONFIGURATION & LOGGING
# ==============================================================================
export DSLV_DASHBOARD_REAL_SDR=1  # Force real SDR data ingestion on boot

CYAN='\033[0;36m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m'

log_head() { echo -e "\n${CYAN}=== $1 ===${NC}"; }
log_ok()   { echo -e "  ${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "  ${YELLOW}[!]${NC} $1"; }
log_err()  { echo -e "  ${RED}[✗]${NC} $1"; }
die()      { log_err "$1"; exit 1; }

SUDO=""
if [ "$EUID" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    else
        log_warn "Not running as root and sudo not found. Systemd operations may fail."
    fi
fi

# Prevent duplicate launches (LXDE session restore bug)
if pgrep -f "dashboard.app" > /dev/null; then
    log_warn "Dashboard is already running (detected dashboard.app process)."
    log_warn "Aborting supervisor to prevent duplicate instances."
    sleep 5
    exit 0
fi

# Optional: Warm-up pause for cold boot
if [ -z "$DSLV_LAUNCH_QUICK" ]; then
    log_head "SYSTEM WARM-UP"
    echo "  Pausing 10s to allow desktop environment to settle..."
    sleep 10
fi

# ==============================================================================
# 1. ENVIRONMENT VERIFICATION
# ==============================================================================
log_head "ENVIRONMENT VERIFICATION"

PROJ_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${PROJ_DIR}/.venv"

if [ -f "${VENV_DIR}/bin/python" ]; then
    log_ok "Python Virtual Environment found at ${VENV_DIR}"
else
    die "Python venv not found! Ensure the installer has been run."
fi

if "${VENV_DIR}/bin/python" -c "import dslv_zpdi" 2>/dev/null; then
    log_ok "Core dslv_zpdi package is importable."
else
    die "Core dslv_zpdi package is broken or not installed in the venv."
fi

# ==============================================================================
# 2. HARDWARE & UDEV VERIFICATION
# ==============================================================================
log_head "HARDWARE & SDR VERIFICATION"

if [ -f "/etc/udev/rules.d/53-adi-plutosdr-usb.rules" ] || [ -f "/lib/udev/rules.d/53-adi-plutosdr-usb.rules" ]; then
    log_ok "PlutoSDR udev rules are present."
else
    log_warn "PlutoSDR udev rules (53-adi-plutosdr-usb.rules) are missing. Non-root SDR access may fail."
fi

if "${VENV_DIR}/bin/python" -c "import iio" 2>/dev/null; then
    log_ok "libiio python bindings verified in venv."
else
    die "libiio python bindings missing from venv! SDR discovery will crash."
fi

# ==============================================================================
# 3. PIPELINE ORCHESTRATION
# ==============================================================================
log_head "PIPELINE ORCHESTRATION"

SERVICES=("dslv-zpdi-tuning" "dslv-zpdi-preflight" "dslv-zpdi" "dslv-zpdi-webdash")

# Stop existing pipeline to ensure a clean state
echo "  Tearing down existing pipeline..."
for unit in "${SERVICES[@]}"; do
    $SUDO systemctl stop "${unit}.service" 2>/dev/null || true
done
$SUDO systemctl daemon-reload
sleep 2

# Start sequentially with verification
for unit in "${SERVICES[@]}"; do
    echo "  -> Starting ${unit}.service..."
    $SUDO systemctl start "${unit}.service"
    
    # Wait for active state (up to 30 seconds)
    VERIFIED=0
    for i in {1..15}; do
        STATE=$(systemctl is-active "${unit}.service" 2>/dev/null || true)
        if [ "$STATE" = "active" ]; then
            log_ok "${unit} is ACTIVE and STABLE."
            VERIFIED=1
            break
        elif [ "$STATE" = "failed" ]; then
            log_err "${unit} FAILED to start!"
            break
        fi
        sleep 2
    done

    if [ $VERIFIED -eq 0 ]; then
        log_err "Timeout or failure waiting for ${unit}.service to stabilize."
        log_warn "Tail of logs:"
        $SUDO journalctl -u "${unit}.service" -n 15 --no-pager
        die "Pipeline orchestration aborted."
    fi
done

# ==============================================================================
# 4. MOBILE NODE / WEBDASH BRIDGE
# ==============================================================================
log_head "MOBILE NODE BRIDGE"
# Verify webdash is listening on 8000/8080 or process is up
if pgrep -f "dashboard.web_server" > /dev/null; then
    log_ok "Mobile Node Bridge (WebDash API) is actively running."
else
    log_warn "WebDash process not detected in process list, mobile node may fail to connect."
fi

# ==============================================================================
# 5. TUI DASHBOARD LAUNCH
# ==============================================================================
log_head "TUI DASHBOARD LAUNCH"

# Wait for display server
for _ in {1..10}; do
    if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
        if command -v xrandr >/dev/null 2>&1 && xrandr --current >/dev/null 2>&1; then
            log_ok "Display server ready."
            break
        fi
    fi
    sleep 2
done

export DSLV_DASHBOARD_COMPACT=0
export DSLV_DASHBOARD_10IN=0

# Detect screen geometry
if command -v xrandr >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
    read SCREEN_W SCREEN_H < <(xrandr --current 2>/dev/null | awk '/\*/{print $1; exit}' | tr 'x' ' ' || echo "0 0")
    if [ "$SCREEN_W" -le 1024 ] && [ "$SCREEN_W" -gt 0 ]; then
        export DSLV_DASHBOARD_COMPACT=1
        log_ok "Detected compact display layout ($SCREEN_W x $SCREEN_H)."
    elif [ "$SCREEN_W" -le 1280 ] && [ "$SCREEN_W" -gt 0 ]; then
        export DSLV_DASHBOARD_10IN=1
        log_ok "Detected 10-inch display layout ($SCREEN_W x $SCREEN_H)."
    else
        log_ok "Detected standard display layout ($SCREEN_W x $SCREEN_H)."
    fi
fi

# Launch
DASH_SCRIPT="${PROJ_DIR}/tools/dashboard/launch.sh"
if [ ! -f "$DASH_SCRIPT" ]; then
    die "Dashboard launch script not found: $DASH_SCRIPT"
fi

log_ok "Spawning Dashboard UI..."
sleep 2

# We use exec so the supervisor process is replaced by the TUI, keeping process tree clean.
exec "$DASH_SCRIPT"
