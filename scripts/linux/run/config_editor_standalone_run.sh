#!/bin/bash
# HECOS Config Editor (Standalone TUI)

# Spostati nella cartella root del progetto
cd "$(dirname "$0")/../../.."

echo "Starting Configuration Editor..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

python3 -c "from hecos.ui.config_editor.core import ConfigEditor; ConfigEditor().run()"

echo "Editor terminated. Press ENTER to exit..."
read
