#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/jqve/next.jqve.dev"
VENV_DIR="$APP_DIR/.venv"
LOG_FILE="$APP_DIR/logs/update.log"
SERVICE_NAME="dart-rankings"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

on_error() {
  log "ERROR: update failed (exit code $?). Check log at $LOG_FILE"
}
trap on_error ERR

log "Starting update"

cd "$APP_DIR"

if [ ! -d "$VENV_DIR" ]; then
  log "Creating virtual environment"
  python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null 2>&1
"$VENV_DIR/bin/python" -m pip install -r "$APP_DIR/requirements.txt" >/dev/null 2>&1

log "Restarting $SERVICE_NAME service"
sudo systemctl restart "$SERVICE_NAME" 2>&1 | tee -a "$LOG_FILE"

log "Update completed successfully"
