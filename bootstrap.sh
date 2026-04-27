#!/usr/bin/env bash
# ============================================================================
# DSLV-ZPDI  ::  One-Shot Bootstrap
# ============================================================================
# Drop-into-terminal installer for Raspberry Pi OS Trixie (Pi 5 Tier-1 Node).
#
# Usage (pick ONE):
#
#   # A) Curl-pipe (recommended for fresh SD card):
#   curl -fsSL https://raw.githubusercontent.com/DynoGator/dslv-zpdi/main/bootstrap.sh | bash
#
#   # B) With options (hardening + dashboard + bloatware cull + passwordless sudo):
#   curl -fsSL https://raw.githubusercontent.com/DynoGator/dslv-zpdi/main/bootstrap.sh | bash -s -- --all
#
#   # C) Clone first, then run:
#   git clone https://github.com/DynoGator/dslv-zpdi.git ~/dslv-zpdi && \
#     cd ~/dslv-zpdi && sudo bash bootstrap.sh --all
#
# What it does:
#   1. Installs git + curl if missing (no-op if already present)
#   2. Clones/updates DynoGator/dslv-zpdi into $HOME/dslv-zpdi
#   3. Invokes install_dslv_zpdi.sh with the flags you pass (default: --all)
#
# Idempotent: safe to re-run; existing clone is refreshed via git pull.
# ============================================================================

set -euo pipefail

REPO_URL="https://github.com/DynoGator/dslv-zpdi.git"
BRANCH="${DSLV_BRANCH:-main}"
TARGET_DIR="${DSLV_TARGET_DIR:-$HOME/dslv-zpdi}"

# Pass-through flags to install_dslv_zpdi.sh. Default flips the big switch.
INSTALLER_FLAGS=("$@")
if [ ${#INSTALLER_FLAGS[@]} -eq 0 ]; then
    INSTALLER_FLAGS=("--all" "--simulator")
fi

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
if [ -t 1 ]; then
    C_GREEN=$'\e[32m' C_CYAN=$'\e[36m' C_YELLOW=$'\e[33m' C_RED=$'\e[31m'
    C_BOLD=$'\e[1m' C_RESET=$'\e[0m'
else
    C_GREEN="" C_CYAN="" C_YELLOW="" C_RED="" C_BOLD="" C_RESET=""
fi
log()  { printf '%s[BOOTSTRAP]%s %s\n' "$C_CYAN" "$C_RESET" "$*"; }
ok()   { printf '%s[OK]%s       %s\n' "$C_GREEN" "$C_RESET" "$*"; }
warn() { printf '%s[WARN]%s     %s\n' "$C_YELLOW" "$C_RESET" "$*"; }
die()  { printf '%s[FATAL]%s    %s\n' "$C_RED" "$C_RESET" "$*"; exit 1; }

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
cat <<BANNER
${C_CYAN}${C_BOLD}
 ===============================================================
   DSLV-ZPDI  ::  Bootstrap Installer (Pi 5 / Trixie)
   DynoGatorLabs  -  Tier-1 Field Node
 ===============================================================
${C_RESET}
BANNER

# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------
if [ "$(id -u)" -eq 0 ]; then
    die "Do NOT run bootstrap.sh as root. It will sudo itself when needed."
fi

if ! command -v sudo >/dev/null 2>&1; then
    die "sudo is required. Install it first: apt install sudo"
fi

# ---------------------------------------------------------------------------
# Step 1: prerequisites
# ---------------------------------------------------------------------------
log "Checking prerequisites (git, curl, ca-certificates)..."
MISSING=()
for bin in git curl; do
    command -v "$bin" >/dev/null 2>&1 || MISSING+=("$bin")
done
if [ ${#MISSING[@]} -gt 0 ]; then
    log "Installing: ${MISSING[*]}"
    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends ca-certificates "${MISSING[@]}"
fi
ok "Prereqs present."

# ---------------------------------------------------------------------------
# Step 2: clone or refresh repo
# ---------------------------------------------------------------------------
if [ -d "$TARGET_DIR/.git" ]; then
    log "Existing clone found at $TARGET_DIR — refreshing (branch: $BRANCH)..."
    git -C "$TARGET_DIR" fetch --all --prune
    git -C "$TARGET_DIR" checkout "$BRANCH"
    git -C "$TARGET_DIR" pull --ff-only
else
    log "Cloning $REPO_URL -> $TARGET_DIR (branch: $BRANCH)..."
    git clone --branch "$BRANCH" "$REPO_URL" "$TARGET_DIR"
fi
ok "Repo ready at $TARGET_DIR"

# ---------------------------------------------------------------------------
# Step 3: hand off to installer
# ---------------------------------------------------------------------------
INSTALLER="$TARGET_DIR/install_dslv_zpdi.sh"
[ -x "$INSTALLER" ] || chmod +x "$INSTALLER"
[ -f "$INSTALLER" ] || die "installer missing at $INSTALLER"

log "Launching installer: $INSTALLER ${INSTALLER_FLAGS[*]}"
echo
cd "$TARGET_DIR"
sudo -E bash "$INSTALLER" "${INSTALLER_FLAGS[@]}"

echo
ok "Bootstrap complete. Reboot recommended if kernel/sysctl/systemd changed."
echo
printf '%sNext steps:%s\n' "$C_BOLD" "$C_RESET"
printf '  1. %ssudo reboot%s\n' "$C_CYAN" "$C_RESET"
printf '  2. Dashboard auto-launches on desktop; or run: %s%s/tools/dashboard/launch.sh%s\n' "$C_CYAN" "$TARGET_DIR" "$C_RESET"
printf '  3. Watch pipeline: %sjournalctl -u dslv-zpdi -f%s\n' "$C_CYAN" "$C_RESET"
echo
