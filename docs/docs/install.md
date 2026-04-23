# Installation Guide

Follow these steps to set up Zentra Core on your machine from scratch.

## Prerequisites

1. **Python**: Version 3.10 or higher.
2. **Backends**: Ollama or KoboldCpp (optional but recommended for local LLM).

## Installation Methods

### 🔹 Method A: One-Click Setup (Recommended)
The easiest way to set up Zentra from scratch. This script automatically checks Python, installs dependencies, and launches the browser-based **Setup Wizard**.

1. **Windows:** Run `.\START_SETUP_HERE_WIN.bat`
2. **Linux:** Run `bash START_SETUP_HERE_LINUX.sh`

### 🔹 Method B: Manual Components (Advanced)
If you need to run specific parts of Zentra or manage the system manually:

1. **Install Dependencies:** `pip install -r requirements.txt`
2. **Launch Components:**
   - **Full Bundle (Tray + Backend):** `python main.py`
   - **Web Interface Only:** `ZENTRA_WEB_RUN_WIN.bat` (Win) or `zentra_web_run.sh` (Linux)
   - **Terminal Console Only:** `ZENTRA_CONSOLE_RUN_WIN.bat` (Win) or `ZENTRA_CONSOLE_RUN.sh` (Linux)
3. **Service Management:**
   - **Install:** `INSTALL_SERVICE_WIN.bat` (Win) or `INSTALL_SERVICE_LINUX.sh` (Linux)
   - **Uninstall:** `UNINSTALL_SERVICE_WIN.bat` (Win) or `UNINSTALL_SERVICE_LINUX.sh` (Linux)

## Configuration
- On first launch, Zentra generates default config files in `zentra/config/data/`.
- Access the **Control Panel** via the tray icon or by navigating to `http://localhost:7070/zentra/config/ui`.

## Common Troubleshooting
- **Hardware telemetry error**: Run `pip install gputil`.
- **Module not found**: Ensure all dependencies are installed via `pip`.
- **Backend not ready**: Start Ollama or KoboldCPP before launching Zentra.
