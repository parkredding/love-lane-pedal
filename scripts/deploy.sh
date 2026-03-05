#!/usr/bin/env bash
# StemStomp deployment update script.
# Updates an existing installation with the latest code.
#
# Usage:  sudo bash scripts/deploy.sh
set -euo pipefail

INSTALL_DIR="/opt/stemstomp"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== StemStomp Deploy ==="

# Stop service
echo "Stopping stemstomp..."
systemctl stop stemstomp.service 2>/dev/null || true

# Update code
echo "Updating code..."
cp -r "$REPO_DIR/src" "$INSTALL_DIR/"
cp "$REPO_DIR/main.py" "$INSTALL_DIR/"
cp "$REPO_DIR/requirements.txt" "$INSTALL_DIR/"
cp "$REPO_DIR/version.txt" "$INSTALL_DIR/"

# Update deps
echo "Updating dependencies..."
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q

# Update systemd units
cp "$REPO_DIR/systemd/stemstomp.service" /etc/systemd/system/
cp "$REPO_DIR/systemd/stemstomp-ota.service" /etc/systemd/system/
systemctl daemon-reload

# Set ownership
chown -R stemstomp:stemstomp "$INSTALL_DIR"

# Restart
echo "Starting stemstomp..."
systemctl start stemstomp.service

echo "=== Deploy complete ==="
