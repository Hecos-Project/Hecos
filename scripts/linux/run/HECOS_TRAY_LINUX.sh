#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../../.."

# Starts the Hecos System Tray Orchestrator quietly
python3 -m hecos.tray.tray_app &
disown
