#!/bin/bash

# Configuration
SERVICE_NAME="zentra"
SERVICE_FILE="scripts/linux/service/zentra.service"
TARGET_DIR="/etc/systemd/user"
SERVICE_DEST="$TARGET_DIR/$SERVICE_NAME.service"

echo ""
echo " +--------------------------------------------------+"
echo " |                                                  |"
echo " |      ZENTRA CORE - LINUX SERVICE INSTALLER       |"
echo " |                                                  |"
echo " +--------------------------------------------------+"
echo ""

# Ensure directory exists
mkdir -p "$TARGET_DIR"

# Copy service file
echo " [*] Installing systemd user service..."
cp "$SERVICE_FILE" "$SERVICE_DEST"

# Replace placeholders with current path
CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)
sed -i "s|WorkingDirectory=.*|WorkingDirectory=$CURRENT_DIR|g" "$SERVICE_DEST"
sed -i "s|ExecStart=.*|ExecStart=$CURRENT_DIR/venv/bin/python zentra/monitor.py --script zentra.modules.web_ui.server|g" "$SERVICE_DEST"
sed -i "s|User=.*|User=$CURRENT_USER|g" "$SERVICE_DEST"

# Reload and enable
echo " [*] Reloading systemd daemon..."
systemctl --user daemon-reload

echo " [*] Enabling $SERVICE_NAME service..."
systemctl --user enable "$SERVICE_NAME"

echo " [*] Starting $SERVICE_NAME service..."
systemctl --user start "$SERVICE_NAME"

echo ""
echo " [+] Zentra service installed and started successfully!"
echo " [+] You can check status with: systemctl --user status $SERVICE_NAME"
echo ""
