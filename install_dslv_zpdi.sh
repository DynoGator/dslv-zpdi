#!/usr/bin/env bash
# DSLV-ZPDI installer / validator
# Revision: 4.0.2.4-CORRECTED
# Validated against: https://github.com/DynoGator/dslv-zpdi (Rev 4.0.2.4)
# Date: 2026-04-09

set -Eeuo pipefail

SCRIPT_REV="Rev 4.0.2.4"
REPO_URL="${DSLV_REPO_URL:-https://github.com/DynoGator/dslv-zpdi.git}"
INSTALL_DIR="${DSLV_INSTALL_DIR:-$(pwd)}"
RUN_TIER1_AUDIT=0
SKIP_TESTS=0
SKIP_APT=0
SIMULATOR_MODE=0

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
NC='\033[0m'

log_info()    { echo -e "${YELLOW}[DSLV-INFO] $*${NC}"; }
log_ok()      { echo -e "${GREEN}[DSLV-OK] $*${NC}"; }
log_warn()    { echo -e "${BLUE}[DSLV-WARN] $*${NC}"; }
log_fail()    { echo -e "${RED}[DSLV-ERR] $*${NC}"; exit 1; }

usage() {
    cat <<USAGE
Usage: sudo ./install_dslv_zpdi.sh [options]

Options:
  --tier1        Run strict Tier 1 hardware audit after install
  --simulator    Run Tier 1 audit in simulation mode (skip hardware checks)
  --skip-tests   Skip pytest / pipeline / SPEC validation
  --skip-apt     Skip apt-get package installation
  --dir PATH     Install or update repo at PATH
  --repo URL     Clone from alternate git URL
  -h, --help     Show this help

Environment overrides:
  DSLV_INSTALL_DIR
  DSLV_REPO_URL
  DEV_SIMULATOR=1 (also enables simulator mode)
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tier1)
            RUN_TIER1_AUDIT=1
            ;;
        --simulator)
            SIMULATOR_MODE=1
            export DEV_SIMULATOR=1
            ;;
        --skip-tests)
            SKIP_TESTS=1
            ;;
        --skip-apt)
            SKIP_APT=1
            ;;
        --dir)
            shift
            [[ $# -gt 0 ]] || log_fail "--dir requires a path"
            INSTALL_DIR="$1"
            ;;
        --repo)
            shift
            [[ $# -gt 0 ]] || log_fail "--repo requires a URL"
            REPO_URL="$1"
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_fail "Unknown option: $1"
            ;;
    esac
    shift
done

if [[ "$EUID" -ne 0 ]]; then
    log_fail "Please run this script with sudo."
fi

# Python version check (pyproject.toml requires >=3.9)
PYTHON_CMD=$(command -v python3 || true)
if [[ -z "$PYTHON_CMD" ]]; then
    log_fail "python3 not found. Required: >=3.9"
fi

PY_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [[ "$PY_MAJOR" -lt 3 ]] || [[ "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 9 ]]; then
    log_fail "Python 3.9+ required (found $PY_VERSION). Upgrade Python before continuing."
fi

log_ok "Python version check passed: $PY_VERSION"

REAL_USER="${SUDO_USER:-${USER:-root}}"
REAL_HOME="$(getent passwd "$REAL_USER" | cut -d: -f6 || true)"
[[ -n "$REAL_HOME" ]] || REAL_HOME="/root"

run_as_real_user() {
    if [[ "$REAL_USER" == "root" ]]; then
        bash -lc "$*"
    else
        sudo -H -u "$REAL_USER" bash -lc "$*"
    fi
}

run_as_root() {
    bash -lc "$*"
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || log_fail "Required command not found: $1"
}

BASE_PACKAGES=(
    git
    python3
    python3-pip
    python3-venv
    python3-dev
    build-essential
    libhdf5-dev
    libusb-1.0-0-dev
    rtl-sdr
    librtlsdr0
)

TIER1_PACKAGES=(
    chrony
    linuxptp
    ethtool
    pciutils
)

log_info "Starting DSLV-ZPDI install (${SCRIPT_REV})"
log_info "Repo URL: ${REPO_URL}"
log_info "Install dir: ${INSTALL_DIR}"
log_info "Owning user: ${REAL_USER}"
if [[ "$SIMULATOR_MODE" -eq 1 ]]; then
    log_warn "SIMULATOR MODE: Hardware checks will be skipped"
fi

if [[ "$SKIP_APT" -eq 0 ]]; then
    export DEBIAN_FRONTEND=noninteractive
    log_info "Installing base OS dependencies"
    apt-get update -y || log_fail "apt-get update failed"
    apt-get install -y "${BASE_PACKAGES[@]}" || log_fail "Failed to install base packages"

    if [[ "$RUN_TIER1_AUDIT" -eq 1 ]]; then
        log_info "Installing Tier 1 timing/audit packages"
        apt-get install -y "${TIER1_PACKAGES[@]}" || log_fail "Failed to install Tier 1 packages"
    fi
else
    log_warn "Skipping apt package installation by request"
fi

require_cmd git
require_cmd python3

# Git clone / pull logic safely refactored
if [[ -d "$INSTALL_DIR/.git" ]]; then
    log_info "Repository exists; fetching latest changes"
    # Configure safe.directory to avoid "dubious ownership" errors in newer git
    git config --global --add safe.directory "$INSTALL_DIR" 2>/dev/null || true
    run_as_real_user "git -C '$INSTALL_DIR' fetch --all --prune && git -C '$INSTALL_DIR' pull --ff-only" \
        || log_warn "Git pull failed in $INSTALL_DIR (continuing with local files)"
else
    if [[ -d "$INSTALL_DIR" ]] && [[ -n "$(ls -A "$INSTALL_DIR" 2>/dev/null)" ]] && [[ ! -e "$INSTALL_DIR/pyproject.toml" ]]; then
        log_fail "Install target exists, is not a git repo, and is not empty: $INSTALL_DIR"
    fi
    
    if [[ ! -e "$INSTALL_DIR/pyproject.toml" ]]; then
        log_info "Cloning repository"
        mkdir -p "$INSTALL_DIR"
        chown "$REAL_USER":"$REAL_USER" "$INSTALL_DIR"
        
        run_as_real_user "git clone '$REPO_URL' '$INSTALL_DIR'" \
            || log_fail "Git clone failed"
    fi
fi

# Validation: Check for required repository structure
required_paths=(
    "README.md"
    "pyproject.toml"
    "src"
    "specs"
    "tests/test_pipeline.py"
    "tools/orphan_checker.py"
    "tools/check_version_sync.py"
    "tools/repo_guard.py"
    "repo_manifest.yaml"
)

# Conditional validation for Tier 1 tools
if [[ "$RUN_TIER1_AUDIT" -eq 1 ]]; then
    required_paths+=("tools/provision_tier1.py")
    required_paths+=("tools/check_ptp.py")
fi

missing_paths=0
for rel in "${required_paths[@]}"; do
    if [[ ! -e "$INSTALL_DIR/$rel" ]]; then
        log_warn "Repository validation failed; missing: $rel"
        missing_paths=1
    fi
done

if [[ "$missing_paths" -eq 1 ]]; then
    log_fail "Repository structure validation failed. Repository may be incomplete or --tier1 tools missing."
fi

log_ok "Repository structure validated"

VENV_DIR="$INSTALL_DIR/venv"
log_info "Creating virtual environment at $VENV_DIR"
run_as_real_user "python3 -m venv '$VENV_DIR'" || log_fail "venv creation failed"

log_info "Upgrading pip tooling"
run_as_real_user "'$VENV_DIR/bin/python' -m pip install --upgrade pip setuptools wheel" \
    || log_fail "Failed to upgrade pip/setuptools/wheel"

log_info "Installing package metadata and dev extras from pyproject.toml"
if ! run_as_real_user "cd '$INSTALL_DIR' && '$VENV_DIR/bin/python' -m pip install -e '.[dev]'"; then
    log_warn "Editable install with dev extras failed; retrying runtime editable install"
    run_as_real_user "cd '$INSTALL_DIR' && '$VENV_DIR/bin/python' -m pip install -e ." \
        || log_fail "Editable install failed"
fi

log_info "Running pip consistency check"
run_as_real_user "'$VENV_DIR/bin/python' -m pip check" || log_fail "pip check reported dependency problems"
log_ok "Python environment ready"

if [[ "$SKIP_TESTS" -eq 0 ]]; then
    if [[ -x "$VENV_DIR/bin/pytest" ]]; then
        log_info "Running full pytest suite"
        run_as_real_user "cd '$INSTALL_DIR' && '$VENV_DIR/bin/pytest' -q tests" \
            || log_fail "pytest suite failed"
    else
        log_warn "pytest not available; falling back to pipeline smoke test"
        run_as_real_user "cd '$INSTALL_DIR' && '$VENV_DIR/bin/python' tests/test_pipeline.py" \
            || log_fail "Pipeline smoke test failed"
    fi

    log_info "Running SPEC orphan checker"
    run_as_real_user "cd '$INSTALL_DIR' && '$VENV_DIR/bin/python' tools/orphan_checker.py" \
        || log_fail "SPEC orphan checker failed"

    log_info "Running version synchronization check"
    run_as_real_user "cd '$INSTALL_DIR' && '$VENV_DIR/bin/python' tools/check_version_sync.py" \
        || log_fail "Version sync check failed"

    log_info "Running repository guard"
    run_as_real_user "cd '$INSTALL_DIR' && '$VENV_DIR/bin/python' tools/repo_guard.py" \
        || log_fail "Repo guard failed"

    log_ok "Validation suite passed"
else
    log_warn "Skipping repo tests and SPEC validation by request"
fi

if [[ "$RUN_TIER1_AUDIT" -eq 1 ]]; then
    # Hardware validation: CM4 OR CM5 are valid Tier 1 anchors per PHASE_2A_HARDWARE_BUILD_LIST.md
    if [[ -r /proc/device-tree/model ]]; then
        if ! grep -aqE 'Compute Module 4|Compute Module 5|Raspberry Pi 4|Raspberry Pi 5' /proc/device-tree/model; then
            log_warn "Tier 1 audit: Host does not identify as CM4/CM5 or Pi 4/5"
            log_warn "Expected: Compute Module 4 or 5 (per PHASE_2A_HARDWARE_BUILD_LIST.md)"
        else
            log_ok "Hardware identifies as compatible Tier 1 platform"
        fi
    else
        log_warn "Cannot determine hardware model (no /proc/device-tree/model)"
    fi

    [[ -f "$INSTALL_DIR/tools/provision_tier1.py" ]] || log_fail "Tier 1 audit requested but tools/provision_tier1.py is missing"
    [[ -f "$INSTALL_DIR/tools/check_ptp.py" ]] || log_fail "Tier 1 audit requested but tools/check_ptp.py is missing"

    log_info "Running Tier 1 hardware audit"
    
    # Export simulator mode for the Python tools
    if [[ "$SIMULATOR_MODE" -eq 1 ]]; then
        export DEV_SIMULATOR=1
        log_warn "DEV_SIMULATOR=1: Skipping hardware-specific checks"
    fi
    
    # NOTE: Running as root (not run_as_real_user) because hardware audit checks:
    # - lsmod (readable by all, but PTP device access usually requires root)
    # - /dev/ptp0 permissions
    # - System-level PTP configuration
    if ! run_as_root "cd '$INSTALL_DIR' && '$VENV_DIR/bin/python' tools/provision_tier1.py"; then
        log_fail "Tier 1 hardware audit failed. Ensure Intel i210-T1 is installed and PTP is configured (see PHASE_2A_HARDWARE_BUILD_LIST.md)"
    fi

    log_ok "Tier 1 hardware audit passed"
else
    log_info "Tier 1 hardware audit skipped. Re-run with --tier1 on a CM4/CM5 + i210/PTP-equipped anchor node."
    log_info "Use --simulator with --tier1 to validate logic without hardware."
fi

# Final summary refactored to explicitly render ANSI color sequences
echo -e "\n${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              DSLV-ZPDI INSTALLATION COMPLETE                 ║${NC}"
echo -e "${GREEN}║                    ${SCRIPT_REV}                           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}\n"
echo -e "Repository : $INSTALL_DIR"
echo -e "Venv       : $VENV_DIR"
echo -e "Activate   : source '$VENV_DIR/bin/activate'\n"
echo -e "Suggested next commands:"
echo -e "  cd '$INSTALL_DIR'"
echo -e "  '$VENV_DIR/bin/pytest' -q tests"
echo -e "  '$VENV_DIR/bin/python' tools/orphan_checker.py"
echo -e "  sudo ./install_dslv_zpdi.sh --tier1     # CM4/CM5 + i210/PTP anchor node"
echo -e "  sudo ./install_dslv_zpdi.sh --tier1 --simulator  # Test audit logic only\n"

exit 0
