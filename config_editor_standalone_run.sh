#!/bin/bash
# ZENTRA Config Editor (Standalone Logger)

cd "$(dirname "$0")"

echo "Starting Configuration Editor..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

python3 config_tool.py

echo "Editor terminated. Press ENTER to exit..."
read
