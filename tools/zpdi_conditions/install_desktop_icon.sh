#!/usr/bin/env bash
# Install the ZPDI_CONDITIONS desktop icon for the current user.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="${HOME}/Desktop"

echo "Installing ZPDI_CONDITIONS desktop icon to ${DESKTOP_DIR}..."
mkdir -p "${DESKTOP_DIR}"
cp -f "${SCRIPT_DIR}/ZPDI_CONDITIONS.desktop" "${DESKTOP_DIR}/"
chmod +x "${DESKTOP_DIR}/ZPDI_CONDITIONS.desktop"

# Attempt to mark the desktop file as trusted so it is clickable without a
# right-click prompt on GNOME-based desktops.
if command -v gio >/dev/null 2>&1; then
    gio set "${DESKTOP_DIR}/ZPDI_CONDITIONS.desktop" metadata::trusted true 2>/dev/null || true
fi
if command -v gsettings >/dev/null 2>&1; then
    gsettings set org.gnome.shell.extensions.ding show-trash true 2>/dev/null || true
fi

echo "Done. Look for the ZPDI_CONDITIONS icon on your desktop."
