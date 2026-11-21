#!/bin/bash
set -u
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR" || exit 1

if [ -x "$ROOT_DIR/python_env/bin/python3" ]; then
    PYTHON_CMD="$ROOT_DIR/python_env/bin/python3"
elif [ -x "$ROOT_DIR/venv/bin/python3" ]; then
    PYTHON_CMD="$ROOT_DIR/venv/bin/python3"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="$(command -v python3)"
else
    PYTHON_CMD="python"
fi

export CUDA_VISIBLE_DEVICES=0
export HECOS_BOOT_MODE="console"
exec "$PYTHON_CMD" hecos/monitor.py
