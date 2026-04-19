#!/usr/bin/env bash
# DSLV-ZPDI Unified Installer / Validator / Hardening
# Revision: 4.5.0-LBE1420-HARDENED
# OS Support: Raspberry Pi OS Bookworm (Deb 12) & Trixie (Deb 13)
# Date: 2026-04-19
#
# Mirrors the full work of the 2026-04-18 deployment and 2026-04-19
# hardening sessions: bootstraps package + venv + editable install
# (base), optionally applies Tier 1 timing provisioning, system hardening
# (kernel freeze, service disable, CPU/USB tuning, sysctl, modprobe
# blacklist), operations dashboard (rich TUI + desktop autostart),
# bloatware removal, and passwordless-sudo. Idempotent: safe to re-run.

set -Eeuo pipefail

SCRIPT_REV="Rev 4.5.0"
REPO_URL="${DSLV_REPO_URL:-https://github.com/DynoGator/dslv-zpdi.git}"
INSTALL_DIR="${DSLV_INSTALL_DIR:-$(pwd)}"
RUN_TIER1_AUDIT=0
FIELD_MODE=0
SKIP_TESTS=0
SKIP_APT=0
SIMULATOR_MODE=0
HARDEN_MODE=0
DASHBOARD_MODE=0
BLOATWARE_MODE=0
PASSWORDLESS_SUDO=0

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
NC='\033[0m'

log_info()    { echo -e "${YELLOW}[DSLV-INFO] $*${NC}"; }
log_ok()      { echo -e "${GREEN}[DSLV-OK] $*${NC}"; }
log_warn()    { echo -e "${BLUE}[DSLV-WARN] $*${NC}"; }
log_fail()    { echo -e "${RED}[DSLV-ERR] $*${NC}"; exit 1; }

# 1. OS Detection Logic (Bookworm vs. Trixie compliance)
OS_ID=$(grep '^ID=' /etc/os-release | cut -d= -f2 | tr -d '"')
OS_VERSION=$(grep '^VERSION_ID=' /etc/os-release | cut -d= -f2 | tr -d '"')
OS_CODENAME=$(grep '^VERSION_CODENAME=' /etc/os-release | cut -d= -f2 | tr -d '"')

usage() {
    cat <<USAGE
Usage: sudo ./install_dslv_zpdi.sh [options]

Core install:
  --tier1             Run strict Tier 1 hardware audit after install
  --field             Auto-launch 72 h baseline capture (implies --tier1)
  --simulator         Run Tier 1 audit / pipeline in simulation mode
  --skip-tests        Skip pytest / SPEC validation
  --skip-apt          Skip apt-get package installation
  --dir PATH          Install or update repo at PATH
  --repo URL          Clone from alternate git URL

System hardening (2026-04-19 session):
  --harden            Install tuning+preflight+main systemd services,
                      freeze kernel/firmware/hackrf packages, apply
                      sysctl tuning, modprobe blacklist, CPU governor
                      lock, USB power-mgmt defeat.
  --dashboard         Install rich+textual+pyfiglet, enable desktop
                      autostart of the operations TUI.
  --bloatware         Remove firefox, libreoffice, nodejs, realvnc,
                      thonny, rpi-connect, mkvtoolnix, pocketsphinx,
                      vlc-l10n, rpi-imager, rpi-userguide, sonic-pi,
                      scratch3, wolfram-engine, claws-mail (keeps
                      desktop, wifi, bluetooth, accessibility, ssh).
  --passwordless-sudo Configure NOPASSWD sudo for the invoking user
                      (\$SUDO_USER). File: /etc/sudoers.d/dslv-zpdi
  --all               Equivalent to --tier1 --harden --dashboard
                      --bloatware --passwordless-sudo

  -h, --help          Show this help

Environment overrides:
  DSLV_INSTALL_DIR
  DSLV_REPO_URL
  DEV_SIMULATOR=1 (also enables simulator mode)

Examples:
  # First-boot full deployment (clone already present or curl|bash bootstrap)
  sudo ./install_dslv_zpdi.sh --all --simulator

  # Just add dashboard to an existing deployment
  sudo ./install_dslv_zpdi.sh --dashboard --skip-tests --skip-apt

  # Production hardware activation (after GPSDO arrives)
  sudo ./install_dslv_zpdi.sh --tier1
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tier1)
            RUN_TIER1_AUDIT=1
            ;;
        --field)
            RUN_TIER1_AUDIT=1
            FIELD_MODE=1
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
        --harden)
            HARDEN_MODE=1
            ;;
        --dashboard)
            DASHBOARD_MODE=1
            ;;
        --bloatware)
            BLOATWARE_MODE=1
            ;;
        --passwordless-sudo)
            PASSWORDLESS_SUDO=1
            ;;
        --all)
            RUN_TIER1_AUDIT=1
            HARDEN_MODE=1
            DASHBOARD_MODE=1
            BLOATWARE_MODE=1
            PASSWORDLESS_SUDO=1
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

log_ok "OS Detected: $OS_ID ($OS_CODENAME) — Python $PY_VERSION"

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
)

TIER1_PACKAGES=(
    chrony
    pps-tools
    ethtool
    pciutils
    hackrf
    libhackrf-dev
    soapysdr-module-hackrf
    python3-soapysdr
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
        
        # Configure chrony for PPS priority (ARCH-PHASE-2A-PIVOT §4.3)
        log_info "Configuring chrony for PPS priority over NTP"
        if ! grep -q "refclock PPS /dev/pps0" /etc/chrony/chrony.conf 2>/dev/null; then
            cat >> /etc/chrony/chrony.conf << 'EOF'

# DSLV-ZPDI RF Metrology Configuration (Rev 4.1+)
# Absolute UTC via Hardware PPS - prioritizes GPSDO over network
refclock PPS /dev/pps0 lock NMEA poll 4 prefer trust
EOF
            log_ok "Chrony configured for PPS priority"
        fi
        
        # Configure PPS GPIO overlay for Pi 5 RP1 (ARCH-PHASE-2A-PIVOT §4.2)
        log_info "Configuring PPS-GPIO overlay for Pi 5 RP1"
        # Pi OS Bookworm/Trixie firmware path
        FIRMWARE_CONFIG="/boot/firmware/config.txt"
        if [[ ! -f "$FIRMWARE_CONFIG" ]]; then
            FIRMWARE_CONFIG="/boot/config.txt" # Legacy path
        fi

        if [[ -f "$FIRMWARE_CONFIG" ]]; then
            if ! grep -q "dtoverlay=pps-gpio" "$FIRMWARE_CONFIG"; then
                cat >> "$FIRMWARE_CONFIG" << 'EOF'

# DSLV-ZPDI PPS Configuration (Rev 4.1+)
# WARNING: Pi 5 RP1 uses 3.3V logic. Verify GPSDO output voltage before connecting.
dtoverlay=pps-gpio,gpiopin=18,assert_falling_edge=0
EOF
                log_warn "PPS overlay added to $FIRMWARE_CONFIG"
                log_warn "REBOOT REQUIRED for PPS to take effect"
                log_warn "CRITICAL: Verify GPSDO PPS output is 3.3V logic level before reboot!"
            fi
        fi
        
        # Ensure pps-gpio module loads on boot
        if ! grep -q "pps-gpio" /etc/modules 2>/dev/null; then
            echo "pps-gpio" >> /etc/modules
            log_ok "pps-gpio module added to /etc/modules"
        fi
    fi
else
    log_warn "Skipping apt package installation by request"
fi

require_cmd git
require_cmd python3

# Git clone / pull logic safely refactored
if [[ -d "$INSTALL_DIR/.git" ]]; then
    log_info "Repository exists; fetching latest changes"
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

if [[ "$RUN_TIER1_AUDIT" -eq 1 ]]; then
    required_paths+=("tools/provision_tier1.py")
    required_paths+=("tools/check_timing.py")
fi

missing_paths=0
for rel in "${required_paths[@]}"; do
    if [[ ! -e "$INSTALL_DIR/$rel" ]]; then
        log_warn "Repository validation failed; missing: $rel"
        missing_paths=1
    fi
done

if [[ "$missing_paths" -eq 1 ]]; then
    log_fail "Repository structure validation failed. Repository may be incomplete."
fi

log_ok "Repository structure validated"

VENV_DIR="$INSTALL_DIR/venv"
log_info "Creating virtual environment at $VENV_DIR"
run_as_real_user "python3 -m venv '$VENV_DIR'" || log_fail "venv creation failed"

# 2. SoapySDR Venv Linkage Logic (Rev 4.3 feature)
# Trixie/Bookworm Python packages are managed; we link them to venv for tier1.
if [[ "$RUN_TIER1_AUDIT" -eq 1 ]]; then
    log_info "Linking system SoapySDR to virtual environment"
    VENV_SITE_PACKAGES=$(run_as_real_user "'$VENV_DIR/bin/python' -c 'import site; print(site.getsitepackages()[0])'")
    SYS_DIST_PACKAGES="/usr/lib/python3/dist-packages"
    
    if [[ -d "$SYS_DIST_PACKAGES" ]]; then
        # Use find to locate SoapySDR related files in system dist-packages
        mapfile -t SOAPY_FILES < <(find "$SYS_DIST_PACKAGES" -maxdepth 1 -name "SoapySDR*" -o -name "_SoapySDR*")
        for f in "${SOAPY_FILES[@]}"; do
            target="$VENV_SITE_PACKAGES/$(basename "$f")"
            if [[ ! -e "$target" ]]; then
                log_info "Linking $(basename "$f") → venv"
                ln -s "$f" "$target"
            fi
        done
    fi
fi

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
fi

if [[ "$RUN_TIER1_AUDIT" -eq 1 ]]; then
    if [[ -r /proc/device-tree/model ]]; then
        if ! grep -aqE 'Compute Module 4|Compute Module 5|Raspberry Pi 4|Raspberry Pi 5' /proc/device-tree/model; then
            log_warn "Tier 1 audit: Host does not identify as Pi 5 (check model info)"
        else
            log_ok "Hardware identifies as compatible Tier 1 platform"
        fi
    fi

    log_info "Running Tier 1 hardware audit"
    if [[ "$SIMULATOR_MODE" -eq 1 ]]; then
        export DEV_SIMULATOR=1
    fi
    
    field_flag=""
    if [[ "$FIELD_MODE" -eq 1 ]]; then
        field_flag="--field"
    fi
    if ! run_as_root "cd '$INSTALL_DIR' && '$VENV_DIR/bin/python' tools/provision_tier1.py $field_flag"; then
        log_fail "Tier 1 hardware audit failed."
    fi

    log_ok "Tier 1 hardware audit passed"
fi

# ============================================================================
# SESSION-2026-04-19 HARDENING: bloatware, kernel freeze, systemd orchestration
# ============================================================================

if [[ "$BLOATWARE_MODE" -eq 1 ]]; then
    log_info "Removing bloatware (keeps desktop/wifi/bluetooth/accessibility/ssh)"
    # Never purge anything critical to desktop, networking, bluetooth, or the
    # dslv_zpdi runtime.  This list is additive — safe to run multiple times.
    BLOAT_PKGS=(
        firefox
        nodejs libnode109
        libreoffice-core libreoffice-common libreoffice-base-core
        libreoffice-impress libreoffice-writer libreoffice-calc
        libreoffice-draw libreoffice-math
        wolfram-engine sonic-pi scratch3
        claws-mail thonny rpi-connect
        mkvtoolnix mkvtoolnix-gui pocketsphinx-en-us
        vlc-l10n
        realvnc-vnc-server realvnc-vnc-viewer
        rpi-userguide rpi-imager
    )
    apt-get -y remove --purge "${BLOAT_PKGS[@]}" 2>&1 | tail -5 || true
    apt-get -y autoremove --purge 2>&1 | tail -3 || true
    log_ok "Bloatware purged"

    log_info "Disabling services not required by the pipeline"
    for unit in cloud-init cloud-init-local cloud-init-main cloud-init-network \
                cloud-config cloud-final cloud-init-hotplugd.socket \
                cups cups.socket cups.path \
                wayvnc-control \
                nfs-blkmap \
                rpcbind rpcbind.socket; do
        systemctl disable --now "$unit" 2>/dev/null || true
    done
    log_ok "Non-essential services disabled"
fi

if [[ "$HARDEN_MODE" -eq 1 ]]; then
    log_info "Applying system hardening"

    # 1. Kernel & firmware & timing-stack freeze — so unattended upgrades
    #    never break PPS/HackRF/chrony timing.
    HOLD_PKGS=(
        linux-image-rpi-2712 linux-image-rpi-v8
        linux-headers-rpi-2712 linux-headers-rpi-v8
        firmware-brcm80211 firmware-atheros firmware-mediatek
        bluez bluez-firmware
        hackrf libhackrf0 libhackrf-dev
        pps-tools chrony
    )
    # Discover any versioned kernel/header packages installed and hold those too
    mapfile -t KERN_PKGS < <(dpkg-query -W -f='${Package}\n' 2>/dev/null | \
        grep -E '^(linux-image|linux-headers|linux-kbuild)-.*(rpt|rpi)')
    for p in "${HOLD_PKGS[@]}" "${KERN_PKGS[@]}"; do
        # only hold if installed — silences noise on minimal images
        if dpkg -s "$p" >/dev/null 2>&1; then
            apt-mark hold "$p" >/dev/null 2>&1 || true
        fi
    done
    log_ok "apt-mark hold applied to kernel/firmware/timing-stack ($(apt-mark showhold | wc -l) packages)"

    # 2. Persistent CPU governor + USB power-mgmt service
    log_info "Installing dslv-zpdi-tuning.service"
    cat > /etc/systemd/system/dslv-zpdi-tuning.service <<'UNIT'
[Unit]
Description=DSLV-ZPDI System Tuning (CPU governor, USB power)
DefaultDependencies=no
After=sysinit.target local-fs.target
Before=dslv-zpdi-preflight.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash -c 'for c in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > $c; done'
ExecStart=/bin/bash -c 'for d in /sys/bus/usb/devices/*/power/control; do [ -e "$d" ] && echo on > $d 2>/dev/null || true; done'
ExecStart=/bin/bash -c 'for d in /sys/bus/usb/devices/*/power/autosuspend; do [ -e "$d" ] && echo -1 > $d 2>/dev/null || true; done'

[Install]
WantedBy=multi-user.target
UNIT

    # 3. Hardware preflight service — wraps tools/preflight.sh
    log_info "Installing dslv-zpdi-preflight.service"
    cat > /etc/systemd/system/dslv-zpdi-preflight.service <<UNIT
[Unit]
Description=DSLV-ZPDI Hardware Preflight
After=network.target chrony.service dslv-zpdi-tuning.service
Wants=chrony.service dslv-zpdi-tuning.service
Before=dslv-zpdi.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=${INSTALL_DIR}/tools/preflight.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT
    chmod +x "${INSTALL_DIR}/tools/preflight.sh" 2>/dev/null || true

    # 4. Main pipeline service with preflight dependency + RT priority
    log_info "Installing dslv-zpdi.service (main pipeline)"
    PIPE_EXEC="${INSTALL_DIR}/venv/bin/python -m dslv_zpdi.main_pipeline"
    PIPE_ENV=""
    if [[ "$SIMULATOR_MODE" -eq 1 ]] || [[ -z "${GPSDO_PRESENT:-}" ]]; then
        # Default to simulator mode until GPSDO delivery is confirmed
        PIPE_EXEC="${PIPE_EXEC} --simulator"
        PIPE_ENV="Environment=DEV_SIMULATOR=1"
    fi
    cat > /etc/systemd/system/dslv-zpdi.service <<UNIT
[Unit]
Description=DSLV-ZPDI Production Pipeline (SPEC-011)
After=network.target chrony.service dslv-zpdi-preflight.service
Wants=chrony.service
Requires=dslv-zpdi-preflight.service

[Service]
Type=simple
User=${REAL_USER}
Group=${REAL_USER}
WorkingDirectory=${INSTALL_DIR}
ExecStart=${PIPE_EXEC}
${PIPE_ENV}
Environment=PYTHONUNBUFFERED=1
Restart=on-failure
RestartSec=15
Nice=-5
IOSchedulingClass=realtime
IOSchedulingPriority=4
StandardOutput=journal
StandardError=journal
SyslogIdentifier=dslv-zpdi

[Install]
WantedBy=multi-user.target
UNIT

    # 5. Sysctl tuning — lower swap pressure, larger network buffers, fs hardening
    log_info "Installing sysctl tuning /etc/sysctl.d/99-dslv-zpdi.conf"
    cat > /etc/sysctl.d/99-dslv-zpdi.conf <<'SYSCTL'
# DSLV-ZPDI Kernel Tuning for RF Metrology Pipeline
vm.swappiness = 10
net.core.rmem_max = 26214400
net.core.wmem_max = 26214400
kernel.printk = 4 4 1 7
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
fs.protected_fifos = 2
fs.protected_regular = 2
SYSCTL
    sysctl --system >/dev/null 2>&1 || true

    # 6. Blacklist DVB-USB kernel drivers so Tier-2 RTL-SDR dongles (future)
    #    don't get grabbed by the kernel — leaves them free for SoapySDR.
    log_info "Installing DVB-USB kernel blacklist"
    cat > /etc/modprobe.d/dslv-zpdi-rtl-blacklist.conf <<'BLK'
# DSLV-ZPDI: blacklist DVB driver auto-load so RTL-SDR dongles are free for SoapySDR
blacklist dvb_usb_rtl28xxu
blacklist rtl2832
blacklist rtl2830
BLK

    # 7. Pipeline state dir (baseline.json target)
    install -d -o "$REAL_USER" -g "$REAL_USER" /var/lib/dslv_zpdi

    # 8. Reload + enable + start the chain
    systemctl daemon-reload
    systemctl enable dslv-zpdi-tuning.service dslv-zpdi-preflight.service dslv-zpdi.service >/dev/null
    systemctl restart dslv-zpdi-tuning.service dslv-zpdi-preflight.service dslv-zpdi.service || true
    log_ok "Systemd hardening chain installed and started"
fi

if [[ "$DASHBOARD_MODE" -eq 1 ]]; then
    log_info "Installing operations dashboard dependencies"
    run_as_real_user "'$VENV_DIR/bin/python' -m pip install --quiet rich textual pyfiglet" \
        || log_warn "Failed to install dashboard deps (rich/textual/pyfiglet)"

    log_info "Installing desktop autostart for dashboard"
    AUTOSTART_DIR="${REAL_HOME}/.config/autostart"
    install -d -o "$REAL_USER" -g "$REAL_USER" "$AUTOSTART_DIR"
    cat > "$AUTOSTART_DIR/dslv-zpdi-dashboard.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=DSLV-ZPDI Operations Center
Comment=DynoGatorLabs Operations Dashboard
Exec=lxterminal --title="DSLV-ZPDI :: DynoGatorLabs" --geometry=180x50 -e ${INSTALL_DIR}/tools/dashboard/launch.sh
Terminal=false
Categories=Science;Network;
X-GNOME-Autostart-enabled=true
StartupNotify=false
DESK
    chown "$REAL_USER:$REAL_USER" "$AUTOSTART_DIR/dslv-zpdi-dashboard.desktop"
    chmod +x "${INSTALL_DIR}/tools/dashboard/launch.sh" 2>/dev/null || true
    log_ok "Dashboard installed. Launch: ${INSTALL_DIR}/tools/dashboard/launch.sh"
fi

if [[ "$PASSWORDLESS_SUDO" -eq 1 ]]; then
    if [[ "$REAL_USER" == "root" ]]; then
        log_warn "--passwordless-sudo requested but SUDO_USER is root; skipping"
    else
        log_info "Configuring passwordless sudo for ${REAL_USER}"
        echo "${REAL_USER} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/dslv-zpdi
        chmod 440 /etc/sudoers.d/dslv-zpdi
        visudo -c -f /etc/sudoers.d/dslv-zpdi >/dev/null || log_fail "sudoers drop-in failed visudo check"
        log_ok "Passwordless sudo configured for ${REAL_USER}"
    fi
fi

echo -e "\n${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              DSLV-ZPDI INSTALLATION COMPLETE                 ║${NC}"
echo -e "${GREEN}║                    ${SCRIPT_REV}                           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}\n"
echo -e "OS Info    : $OS_ID ($OS_CODENAME) — Python $PY_VERSION"
echo -e "Repository : $INSTALL_DIR"
echo -e "Activate   : source '$VENV_DIR/bin/activate'"
if [[ "$HARDEN_MODE" -eq 1 ]]; then
    echo -e "Pipeline   : sudo systemctl status dslv-zpdi"
    echo -e "Live log   : sudo journalctl -u dslv-zpdi -f"
fi
if [[ "$DASHBOARD_MODE" -eq 1 ]]; then
    echo -e "Dashboard  : ${INSTALL_DIR}/tools/dashboard/launch.sh"
fi
echo

exit 0
