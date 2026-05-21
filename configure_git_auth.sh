#!/bin/bash
# dslv-zpdi: Configure git authentication using GITHUB_PAT from .env
set -e

# Change to project root if script is run from elsewhere
cd "$(dirname "$0")"

# Load .env if it exists
if [ -f .env ]; then
    # Use a robust way to load .env that handles spaces/quotes if necessary
    set -a
    source .env
    set +a
fi

if [ -z "$GITHUB_PAT" ]; then
    echo "ERROR: GITHUB_PAT environment variable is not set."
    echo "Ensure it is defined in .env or the current shell."
    exit 1
fi

# 1. Configure credential helper to use the PAT.
# We use a custom helper that echoes the password from the environment.
# 'username=token' is the standard for GitHub PATs.
git config credential.helper '!f() { echo "username=token"; echo "password=$GITHUB_PAT"; }; f'

# 2. Set remote origin
REMOTE_URL=${GITHUB_REMOTE_URL:-"https://github.com/DynoGator/dslv-zpdi.git"}
if git remote | grep -q "^origin$"; then
    git remote set-url origin "$REMOTE_URL"
else
    git remote add origin "$REMOTE_URL"
fi

# 3. Set local author config for this repo
git config user.name "${GIT_AUTHOR_NAME:-dslv-zpdi-node}"
git config user.email "${GIT_AUTHOR_EMAIL:-node@dslv-zpdi.local}"

echo "SUCCESS: Git authentication configured for $REMOTE_URL"
echo "Credential helper is now using GITHUB_PAT from environment."
