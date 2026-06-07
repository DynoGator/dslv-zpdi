#!/data/data/com.termux/files/usr/bin/bash
# dslv-zpdi Mobile Tier-2 Automated Deployment Script
# Execute natively in Termux to transform an Android device into a production node.

set -euo pipefail

LOG_FILE="$HOME/install_zpdi.log"
exec > >(tee -a "$LOG_FILE") 2>&1

# Robust operation tracking for required output format
declare -a SUCCEEDED_OPS=()
declare -a FAILED_OPS=()

record_success() {
  echo "[SUCCEEDED] $1"
  SUCCEEDED_OPS+=("$1")
}

record_failure() {
  local op="$1"
  local corrective="$2"
  echo "[FAILED] $op"
  echo "  Recommended corrective action: $corrective"
  FAILED_OPS+=("$op")
}

print_summary() {
  echo ""
  echo "======================================================="
  echo "   INSTALLATION OPERATION SUMMARY (all steps)          "
  echo "======================================================="
  echo "SUCCEEDED OPERATIONS:"
  if [ ${#SUCCEEDED_OPS[@]} -eq 0 ]; then
    echo "  (none)"
  else
    for op in "${SUCCEEDED_OPS[@]}"; do echo "  - $op"; done
  fi
  echo ""
  echo "FAILED OPERATIONS:"
  if [ ${#FAILED_OPS[@]} -eq 0 ]; then
    echo "  (none - all critical steps succeeded)"
  else
    for i in "${!FAILED_OPS[@]}"; do
      echo "  - ${FAILED_OPS[$i]}"
      # Note: corrective already printed at failure time
    done
  fi
  echo "======================================================="
}

trap 'print_summary' EXIT

echo "======================================================="
echo "   dslv-zpdi Mobile Node Automated Installer (Rev 5 - Robust) "
echo "   (pyproject.toml + src/dslv_zpdi layout + all new changes) "
echo "======================================================="
echo "[*] Starting deployment at $(date)"

# 1. System Preparation
echo "[*] Enforcing Termux Storage Setup..."
if termux-setup-storage; then
  record_success "termux-setup-storage"
else
  record_failure "termux-setup-storage" "Manually run 'termux-setup-storage' in Termux, grant storage permission in Android dialog, then re-run installer."
fi
sleep 2

echo "[*] Requesting Android Wake-Lock..."
if termux-wake-lock 2>/dev/null; then
  record_success "termux-wake-lock"
else
  record_failure "termux-wake-lock" "Install Termux:API addon from F-Droid or Play Store, then re-run. Or ignore for non-production (device may sleep)."
fi

# 2. Dependency Management
echo "[*] Updating Termux pkg repositories..."
if pkg update -y; then
  record_success "pkg update"
else
  record_failure "pkg update" "Check internet/Termux mirrors. Run 'pkg update' manually, or 'termux-change-repo' to switch mirrors."
fi

echo "[*] Installing Termux dependencies (proot-distro, termux-api, git, openssl)..."
if pkg install -y proot-distro termux-api git openssl; then
  record_success "pkg install proot-distro termux-api git openssl"
else
  record_failure "pkg install proot-distro termux-api git openssl" "Run 'pkg install -y proot-distro termux-api git openssl' manually. Ensure 'pkg update' succeeded first. For proot issues, 'proot-distro remove debian && proot-distro install debian'."
fi

# 3. PRoot Debian Configuration
echo "[*] Installing/Verifying Debian PRoot..."
if proot-distro install debian; then
  record_success "proot-distro install debian"
else
  record_failure "proot-distro install debian" "Run 'proot-distro remove debian' then retry, or 'proot-distro install debian --override-alias debian'. Check storage space and Termux version (>=0.118 recommended)."
fi

# 4. Constructing PRoot execution bridge (robust, status-reporting, new changes incorporated)
BOOTSTRAP_SCRIPT="$HOME/bootstrap_proot.sh"
cat << 'BOOTSTRAP_HEREDOC' > "$BOOTSTRAP_SCRIPT"
#!/bin/bash
# Self-contained robust bootstrap for Debian PRoot (mobile Tier-2)
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

declare -a SUCCEEDED_OPS=()
declare -a FAILED_OPS=()

record_success() { echo "[SUCCEEDED] [proot] $1"; SUCCEEDED_OPS+=("$1"); }
record_failure() { 
  local op="$1"; local rec="$2"
  echo "[FAILED] [proot] $op"
  echo "  Recommended corrective action: $rec"
  FAILED_OPS+=("$op")
}

print_summary() {
  echo ""
  echo "=== PRoot BOOTSTRAP OPERATION SUMMARY ==="
  echo "SUCCEEDED:"
  for o in "${SUCCEEDED_OPS[@]}"; do echo "  - $o"; done
  echo "FAILED:"
  if [ ${#FAILED_OPS[@]} -eq 0 ]; then echo "  (none)"; else for o in "${FAILED_OPS[@]}"; do echo "  - $o"; done; fi
  echo "========================================"
}
trap 'print_summary' EXIT

echo "[*] [Debian] Updating apt repositories..."
if apt-get update -y; then
  record_success "apt-get update"
else
  record_failure "apt-get update" "Check network inside proot (proot-distro login debian -- apt-get update). Or host Termux has no net."
fi

echo "[*] [Debian] Installing build dependencies..."
BUILD_DEPS="python3 python3-venv python3-dev git build-essential libhdf5-dev pkg-config cmake sqlite3 curl openssl ca-certificates"
if apt-get install -y $BUILD_DEPS; then
  record_success "apt-get install build deps ($BUILD_DEPS)"
else
  record_failure "apt-get install build deps" "Run inside proot: apt-get update && apt-get install -y $BUILD_DEPS . Check disk space (df -h). For hdf5: apt-get install -y libhdf5-dev may need universe or backports on some Debian."
fi

REPO_URL="https://github.com/DynoGator/dslv-zpdi.git"
if [ ! -d "/root/dslv-zpdi" ]; then
    echo "[*] [Debian] Cloning repository (real URL with all new changes)..."
    if git clone --depth 1 "$REPO_URL" /root/dslv-zpdi; then
      record_success "git clone $REPO_URL"
    else
      record_failure "git clone $REPO_URL" "Check git in proot, network, or disk. Manual: git clone $REPO_URL /root/dslv-zpdi . Then cd and continue."
    fi
else
    echo "[*] [Debian] Repository exists. Pulling latest (incorporating new changes)..."
    cd /root/dslv-zpdi
    if git fetch && git pull --ff-only; then
      record_success "git pull latest (new changes)"
    else
      record_failure "git pull latest" "cd /root/dslv-zpdi ; git fetch && git pull . Or rm -rf /root/dslv-zpdi and re-clone."
    fi
fi

cd /root/dslv-zpdi

echo "[*] [Debian] Setting up Python virtual environment..."
if python3 -m venv --clear .venv; then
  record_success "python3 -m venv --clear .venv"
else
  record_failure "python3 -m venv" "Ensure python3-venv installed. python3 -m venv --clear .venv . Check python3 --version >=3.9."
fi
source .venv/bin/activate

echo "[*] [Debian] Installing Python dependencies from pyproject.toml (new package layout + src/dslv_zpdi)..."
pip install --upgrade pip setuptools wheel
if pip install -e ".[dev]"; then
  record_success "pip install -e .[dev] (all new deps + src layout from pyproject.toml)"
else
  record_failure "pip install -e .[dev]" "Inside proot venv: pip install --upgrade pip ; pip install -e .[dev] . Common fixes: apt-get install -y python3-dev libhdf5-dev ; or for missing system: pip install numpy scipy h5py pydantic 'fastapi[standard]' uvicorn websockets cryptography python-dotenv . Then retry -e install. Check pyproject.toml syntax."
fi

echo "[*] [Debian] Generating secure .env (with keys for current mobile node crypto/WSS/web)..."
if [ ! -f ".env" ]; then
    AES_KEY=$(openssl rand -base64 32)
    HMAC_SECRET=$(openssl rand -hex 32)
    # Add common keys used by zpdi_mobile_node.py / tier1 server / web server
    cat <<ENV_EOF > .env
ZPDI_LOG_LEVEL=INFO
ZPDI_STREAM_DELAY_MS=250
ZPDI_NODE_ID=dslv-zpdi/mobile-tier2-autodeploy
ZPDI_AES_KEY=${AES_KEY}
ZPDI_HMAC_SECRET=${HMAC_SECRET}
ZPDI_WSS_URI=ws://127.0.0.1:8443/ingest
ZPDI_WSS_TOKEN=$(openssl rand -hex 16)
# Add more as needed from .env.example in repo
ENV_EOF
    record_success ".env generated with crypto + WSS keys"
else
    echo "[*] [Debian] .env already exists. Preserving (manual review recommended for new keys)."
    record_success ".env already present (preserved)"
fi

# Final smoke in proot
echo "[*] [Debian] Post-install smoke test (new layout)..."
if python -c "
import sys
sys.path.insert(0, 'src')
import dslv_zpdi
print('dslv_zpdi version:', getattr(dslv_zpdi, '__version__', 'ok'))
from dslv_zpdi.layer1_ingestion.payload import SensorModality
print('SensorModality (mobile extended): OK')
print('Package import smoke: SUCCEEDED')
" ; then
  record_success "python package import smoke (src layout + pyproject)"
else
  record_failure "python package import smoke" "source .venv/bin/activate ; PYTHONPATH=src python -c 'import dslv_zpdi' . Check previous pip install step. Re-run 'pip install -e .[dev]'."
fi
BOOTSTRAP_HEREDOC

chmod +x "$BOOTSTRAP_SCRIPT"

echo "[*] Bridging into Debian PRoot (executing robust bootstrap)..."
if proot-distro login debian -- bash "$BOOTSTRAP_SCRIPT"; then
  record_success "proot-distro login + bootstrap execution"
else
  record_failure "proot-distro login + bootstrap" "proot-distro login debian -- bash -x $BOOTSTRAP_SCRIPT for debug. Common: re-install proot-distro, check Termux storage permissions, or increase proot timeout."
fi

# 5. Configuration & Termux:Boot Hooks
echo "[*] Securing Termux:Boot persistence layer..."
mkdir -p "$HOME/.termux/boot"

# We must ensure the boot script exists in the repository, but since the
# repository is in PRoot (/root/dslv-zpdi), we can't easily symlink across PRoot
# boundaries safely for Termux:Boot. Instead, we extract the daemon launcher directly
# into the Termux boot folder.

cat << 'BOOT_EOF' > "$HOME/.termux/boot/99-start-zpdi.sh"
#!/data/data/com.termux/files/usr/bin/bash
# dslv-zpdi Termux:Boot auto-start script (Autogenerated)
set -euo pipefail

BOOT_LOG="$HOME/.termux/boot/zpdi-boot.log"
PROOT_DISTRO="/data/data/com.termux/files/usr/bin/proot-distro"
PROJECT_DIR="/root/dslv-zpdi"
SUPERVISOR="$PROJECT_DIR/supervisor.sh"

echo "$(date '+%Y-%m-%d %H:%M:%S') [zpdi-boot] Boot event received" >> "$BOOT_LOG"

if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
    echo "$(date '+%Y-%m-%d %H:%M:%S') [zpdi-boot] wake-lock acquired" >> "$BOOT_LOG"
fi

pkill -SIGTERM -f "supervisor.sh" 2>/dev/null || true
pkill -SIGTERM -f "zpdi_mobile_node.py" 2>/dev/null || true
sleep 1
pkill -SIGKILL -f "zpdi_mobile_node.py" 2>/dev/null || true

# Clear stale HDF5 lock in PRoot
$PROOT_DISTRO login debian -- h5clear -s "$PROJECT_DIR/data/zpdi_stream.h5" 2>/dev/null || true

nohup "$PROOT_DISTRO" login debian -- bash "$SUPERVISOR" >> "$BOOT_LOG" 2>&1 &
echo "$(date '+%Y-%m-%d %H:%M:%S') [zpdi-boot] supervisor launched (proot PID=$!)" >> "$BOOT_LOG"
BOOT_EOF

chmod +x "$HOME/.termux/boot/99-start-zpdi.sh"

echo "[*] Cleaning up temporary artifacts..."
rm -f "$BOOTSTRAP_SCRIPT"

# 6. Verification
echo "======================================================="
echo "   [SUCCESS] dslv-zpdi Mobile Node Deployed   "
echo "======================================================="
echo ""
echo "  Persistence configured via ~/.termux/boot/99-start-zpdi.sh"
echo "  Secure crypto payloads configured in PRoot ~/.env"
echo ""
echo "  ACTION REQUIRED: Reboot Android device to validate"
echo "  Termux:Boot daemon recovery."
echo "======================================================="
