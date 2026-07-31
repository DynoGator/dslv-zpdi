#!/bin/bash
# dslv-zpdi: Configure git authentication using GITHUB_PAT from secure storage.
#
# The PAT is NEVER stored in .env. It lives in /root/.config/dslv-zpdi/github_pat
# with mode 600. This script loads it from there and configures a git credential
# helper that reads it at runtime.

set -euo pipefail

# Change to project root if script is run from elsewhere
cd "$(dirname "$0")"

SECRETS_DIR="${HOME}/.config/dslv-zpdi"
PAT_FILE="${SECRETS_DIR}/github_pat"

# 1. Load PAT from secure storage
if [ -z "${GITHUB_PAT:-}" ]; then
    if [ -f "$PAT_FILE" ]; then
        chmod 600 "$PAT_FILE" 2>/dev/null || true
        GITHUB_PAT=$(tr -d '[:space:]' < "$PAT_FILE")
        export GITHUB_PAT
    fi
fi

if [ -z "${GITHUB_PAT:-}" ]; then
    echo "ERROR: GITHUB_PAT not set and no token found at ${PAT_FILE}."
    echo "Store one with: bash /root/dslv-zpdi-local/scripts/set_github_pat.sh"
    exit 1
fi

# 2. Load non-secret config from .env if present
if [ -f .env ]; then
    set -a
    # shellcheck source=/dev/null
    source .env
    set +a
fi

# 3. Configure credential helper to read the PAT from secure storage at runtime.
#    This avoids persisting the secret in .git/config.
git config credential.helper '!f() {
    PAT_FILE="'"${PAT_FILE}"'"
    if [ -f "$PAT_FILE" ]; then
        PAT=$(tr -d "[:space:]" < "$PAT_FILE")
        if [ -n "$PAT" ]; then
            echo "username=token"
            echo "password=$PAT"
        fi
    fi
}; f'

# 4. Set remote origin
REMOTE_URL=${GITHUB_REMOTE_URL:-"https://github.com/DynoGator/dslv-zpdi.git"}
if git remote | grep -q "^origin$"; then
    git remote set-url origin "$REMOTE_URL"
else
    git remote add origin "$REMOTE_URL"
fi

# 5. Set local author config for this repo
git config user.name "${GIT_AUTHOR_NAME:-dslv-zpdi-node}"
git config user.email "${GIT_AUTHOR_EMAIL:-node@dslv-zpdi.local}"

# 6. Ensure hooks are active
if [ -d .githooks ]; then
    git config core.hooksPath .githooks
    echo "[✓] Git hooks path set to .githooks"
fi

echo "SUCCESS: Git authentication configured for $REMOTE_URL"
echo "Credential helper reads GITHUB_PAT from ${PAT_FILE} at runtime."
