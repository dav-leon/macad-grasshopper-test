#!/usr/bin/env bash
#
# redeploy.sh — pull latest code and restart backend + frontend on the EC2 server.
#
# What it does:
#   1. git pull (fast-forward) in the app root
#   2. backend: install deps into the venv, restart the gunicorn systemd service
#   3. frontend: npm install + npm run build (nginx serves the new dist/)
#   4. fix dist/ permissions so nginx (www-data) can read it, then reload nginx
#
# Data files (backend/data/*.json) are never touched by this script.
#
# Usage (on the server):
#   ~/macad-grasshopper-test/redeploy.sh
# or, if installed as a command (see deploy_ec2.md Part 13):
#   redeploy

set -euo pipefail

# App root = the directory this script lives in, so it works no matter where it's called from.
# readlink -f resolves the /usr/local/bin/redeploy symlink back to the real script path.
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
APP_ROOT="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
BACKEND="$APP_ROOT/backend"
FRONTEND="$APP_ROOT/frontend"
SERVICE="quiz-backend"

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$1"; }

log "Pulling latest code in $APP_ROOT"
cd "$APP_ROOT"
git pull --ff-only

log "Updating backend dependencies"
cd "$BACKEND"
# shellcheck disable=SC1091
source venv/bin/activate
pip install -r requirements.txt gunicorn -q
deactivate

log "Restarting backend service ($SERVICE)"
sudo systemctl restart "$SERVICE"
sudo systemctl --no-pager --lines=0 status "$SERVICE"

log "Rebuilding frontend"
cd "$FRONTEND"
npm install --no-audit --no-fund
npm run build

log "Fixing dist/ permissions and reloading nginx"
sudo chmod -R o+rX "$FRONTEND/dist"
sudo nginx -t
sudo systemctl reload nginx

log "Done. App redeployed."
