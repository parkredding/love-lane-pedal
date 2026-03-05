#!/usr/bin/env bash
# StemStomp Raspberry Pi provisioning script.
# Run as root on a fresh Raspberry Pi OS (Bookworm) installation.
#
# Usage:  sudo bash scripts/provision.sh
set -euo pipefail

INSTALL_DIR="/opt/stemstomp"
SERVICE_USER="stemstomp"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== StemStomp Provisioning ==="

# 1. Create system user
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "Creating system user: $SERVICE_USER"
    useradd --system --shell /usr/sbin/nologin "$SERVICE_USER"
fi

# 2. Add user to hardware groups
for group in gpio i2c audio spi; do
    if getent group "$group" &>/dev/null; then
        usermod -aG "$group" "$SERVICE_USER" 2>/dev/null || true
    fi
done

# 3. Install system packages
echo "Installing system packages..."
apt-get update -qq
apt-get install -y -qq python3-venv python3-dev libasound2-dev libportaudio2 i2c-tools

# 4. Create install directory
echo "Setting up $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR/stems"
cp -r "$REPO_DIR/src" "$INSTALL_DIR/"
cp "$REPO_DIR/main.py" "$INSTALL_DIR/"
cp "$REPO_DIR/requirements.txt" "$INSTALL_DIR/"
cp "$REPO_DIR/version.txt" "$INSTALL_DIR/"

# 5. Create virtualenv and install deps
if [ ! -d "$INSTALL_DIR/venv" ]; then
    python3 -m venv "$INSTALL_DIR/venv"
fi
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q

# 6. Copy .env template if .env doesn't exist
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$REPO_DIR/.env.template" "$INSTALL_DIR/.env"
    echo ""
    echo "** IMPORTANT: Edit $INSTALL_DIR/.env to set your S3 bucket **"
    echo ""
fi
chmod 600 "$INSTALL_DIR/.env"
chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/.env"

# 7. Set ownership
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

# 8. Install systemd services
echo "Installing systemd services..."
cp "$REPO_DIR/systemd/stemstomp.service" /etc/systemd/system/
cp "$REPO_DIR/systemd/stemstomp-ota.service" /etc/systemd/system/
systemctl daemon-reload

# 9. Enable services
systemctl enable stemstomp.service stemstomp-ota.service

# 10. Enable I2C if not already enabled
if command -v raspi-config &>/dev/null; then
    raspi-config nonint do_i2c 0 2>/dev/null || true
    raspi-config nonint do_spi 0 2>/dev/null || true
fi

echo ""
echo "=== Provisioning complete ==="
echo "Edit $INSTALL_DIR/.env, then run: sudo systemctl start stemstomp"
