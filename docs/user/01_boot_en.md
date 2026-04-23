# 🚀 1. Boot & Initial Checks

Upon launching the executable or Python script, Zentra begins its **Synchronized Boot** sequence.

### Pre-Flight Diagnostics
By default, the system checks:
- Essential folder integrity (`core/`, `plugins/`, `memory/`, etc.).
- Hardware status (CPU and RAM within limits).
- Audio and Voice status.
- AI Backend responsiveness.
- Active/Disabled Plugin scan.

### ⚡ One-Click Bootstrap
The recommended way to start Zentra is using the universal bootstrap scripts in the root directory:
- **Windows:** `START_SETUP_HERE_WIN.bat`
- **Linux:** `START_SETUP_HERE_LINUX.sh`

These scripts automatically handle environment checks, dependencies, and launch the **Setup Wizard**.

### 🧩 Individual Component Launch
For advanced users, components can be started individually:
- **Web Interface:** `ZENTRA_WEB_RUN_WIN.bat` (Win) / `zentra_web_run.sh` (Linux)
- **Terminal Console:** `ZENTRA_CONSOLE_RUN_WIN.bat` (Win) / `ZENTRA_CONSOLE_RUN.sh` (Linux)
- **Full Bundle:** `main.py` (Launches Tray + Backend)

### 🏎️ Fast Boot
You can enable **Fast Boot** in the **F7** Control Panel under `SYSTEM` to skip diagnostics and reduce startup time to **~0.5 seconds**.
