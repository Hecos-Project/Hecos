# 🚀 1. Boot & Initial Checks

Upon launching the executable or Python script, Hecos begins its **Synchronized Boot** sequence.

### Pre-Flight Diagnostics
By default, the system checks:
- Essential folder integrity (`core/`, `plugins/`, `memory/`, etc.).
- Hardware status (CPU and RAM within limits).
- Audio and Voice status.
- AI Backend responsiveness.
- Active/Disabled Plugin scan.

### ⚡ One-Click Bootstrap

> [!IMPORTANT]
> **Installation Path**: We strongly recommend extracting and installing Hecos in a root directory like `C:\Hecos`. Avoid installing it in `Downloads`, `Desktop`, or deep folders, as long paths or special characters/spaces in the path can cause startup issues or broken functionalities.

> [!WARNING]
> **System Dependencies**: Before running the setup, ensure you have installed the required redistributables (like `VC_redist`) located in the **`dependencies`** folder. If these are missing, core components like the AI models and the Text-To-Speech engine will fail to start.

The recommended way to start Hecos is using the universal bootstrap scripts in the root directory:
- **Windows:** `START_SETUP_HERE_WIN.bat`
- **Linux:** `START_SETUP_HERE_LINUX.sh`

These scripts automatically handle environment checks, dependencies, and launch the **Setup Wizard**.

> [!TIP]
> **Subsequent Boots**: After completing the initial setup, the fastest and most convenient way to start Hecos for daily use is using `START_HECOS_TRAY_WIN.bat` (Windows) or `START_HECOS_TRAY_LINUX.sh` (Linux). This will start the system silently in the background with the System Tray icon.

### 🧩 Individual Component Launch
For advanced users, components can be started individually:
- **Web Interface:** `HECOS_WEB_RUN_WIN.bat` (Win) / `hecos_web_run.sh` (Linux)
- **Terminal Console:** `HECOS_CONSOLE_RUN_WIN.bat` (Win) / `HECOS_CONSOLE_RUN.sh` (Linux)
- **Full Bundle:** `main.py` (Launches Tray + Backend)

### 🏎️ Fast Boot
You can enable **Fast Boot** in the **F7** Control Panel under `SYSTEM` to skip diagnostics and reduce startup time to **~0.5 seconds**.
