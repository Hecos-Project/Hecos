"""
MODULE: scripts/install_as_service.py
PURPOSE: Cross-platform installer that registers Zentra Core as a system background service.

USAGE:
  Install:   python scripts/install_as_service.py --install
  Uninstall: python scripts/install_as_service.py --uninstall
  Status:    python scripts/install_as_service.py --status
  Tray only: python scripts/install_as_service.py --tray

WHAT IT DOES:
  Windows → Registers a pywin32 Windows Service (services.msc) OR fallback Task Scheduler.
            Also adds the tray app to the Registry startup (HKCU Run).
  Linux   → Copies zentra.service to systemd user directory and enables it.
            Also adds tray_app.py to XDG autostart.

REQUIRES: pip install pystray pillow (for tray icon on both platforms)
          pip install pywin32 (Windows service, Windows only)
"""

import sys
import os
import subprocess
import argparse

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(_ROOT, "scripts")
SYSTEMD_SERVICE_SRC = os.path.join(SCRIPTS_DIR, "zentra.service")
TRAY_CMD = f'"{sys.executable}" -m zentra.tray.tray_app'
SERVICE_MODULE = "zentra.service.windows_service"


# ─────────────────────────── WINDOWS ────────────────────────────────────────

def _win_install():
    print("[Windows] Installing Zentra Core as a system service...")

    # Try pywin32 first
    try:
        import win32serviceutil
        result = subprocess.run(
            [sys.executable, "-m", SERVICE_MODULE, "install"],
            cwd=_ROOT, check=True
        )
        result = subprocess.run(
            [sys.executable, "-m", SERVICE_MODULE, "start"],
            cwd=_ROOT
        )
        print("[+] Windows Service installed and started (services.msc → 'ZentraCore').")
    except ImportError:
        print("[!] pywin32 not found. Using Task Scheduler fallback...")
        _win_schtask_install()

    # Register tray icon at login via Registry
    _win_register_tray()


def _win_schtask_install():
    bat_path = os.path.join(_ROOT, "ZENTRA_WEB_RUN_WIN.bat")
    subprocess.run([
        "schtasks", "/Create", "/TN", "ZentraCore",
        "/TR", f'"{bat_path}"',
        "/SC", "ONLOGON", "/RL", "HIGHEST", "/F"
    ], check=True, shell=True)
    print("[+] Zentra registered in Task Scheduler (launches on next login).")


def _win_register_tray():
    """
    Adds tray icon to HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.

    NOTE FOR ADMINISTRATORS:
      The Windows Service itself runs as SYSTEM (full machine access).
      The tray icon runs as the currently logged-in user — it can still control
      the service via 'sc' because the installer grants the user that permission.
      HKCU does NOT require admin rights and is per-user, so the tray starts
      correctly at login regardless of UAC settings.
    """
    try:
        # Prefer pythonw.exe to avoid a black console window at login
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable  # fallback

        tray_cmd = f'"{pythonw}" -c "import os,sys; os.chdir(r\'{_ROOT}\'); sys.path.insert(0,r\'{_ROOT}\'); from zentra.tray.tray_app import run_tray; run_tray()"'

        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,  # HKCU — no admin needed, per-user
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "ZentraTray", 0, winreg.REG_SZ, tray_cmd)
        winreg.CloseKey(key)
        print("[+] Tray icon registered for login startup (Registry HKCU\\Run).")
    except Exception as e:
        print(f"[!] Could not register tray icon startup: {e}")


def _win_uninstall():
    print("[Windows] Removing Zentra Core service...")
    try:
        import win32serviceutil
        subprocess.run([sys.executable, "-m", SERVICE_MODULE, "stop"], cwd=_ROOT)
        subprocess.run([sys.executable, "-m", SERVICE_MODULE, "remove"], cwd=_ROOT)
    except ImportError:
        subprocess.run(["schtasks", "/Delete", "/TN", "ZentraCore", "/F"], shell=True)

    # Remove tray from HKCU (where it was registered)
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, "ZentraTray")
        winreg.CloseKey(key)
    except Exception:
        pass

    # Also remove tray settings file if present
    import os
    settings_file = os.path.join(_ROOT, "zentra_tray_settings.json")
    if os.path.exists(settings_file):
        try:
            os.remove(settings_file)
        except Exception:
            pass

    print("[+] Zentra Core service and tray startup removed.")


def _win_status():
    try:
        import win32serviceutil
        status = win32serviceutil.QueryServiceStatus("ZentraCore")
        state = {1: "Stopped", 4: "Running", 2: "Starting", 3: "Stopping"}.get(status[1], "Unknown")
        print(f"[Status] Windows Service 'ZentraCore': {state}")
    except ImportError:
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", "ZentraCore"],
            capture_output=True, text=True, shell=True
        )
        print(result.stdout or "[!] Task not found.")
    except Exception as e:
        print(f"[!] Service query failed: {e}")


# ─────────────────────────── LINUX ──────────────────────────────────────────

def _linux_install():
    print("[Linux] Installing Zentra Core as a systemd user service...")
    systemd_dir = os.path.expanduser("~/.config/systemd/user")
    os.makedirs(systemd_dir, exist_ok=True)

    service_dst = os.path.join(systemd_dir, "zentra.service")

    # Patch the service file with the correct user and working dir
    with open(SYSTEMD_SERVICE_SRC, "r") as f:
        content = f.read()
    content = content.replace("/opt/zentra", _ROOT)
    content = content.replace(
        "/opt/zentra/venv/bin/python",
        sys.executable
    )

    with open(service_dst, "w") as f:
        f.write(content)

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "zentra"], check=True)
    subprocess.run(["systemctl", "--user", "start", "zentra"], check=True)
    subprocess.run(["loginctl", "enable-linger"], check=False)
    print(f"[+] Systemd user service enabled. Check with: systemctl --user status zentra")

    _linux_register_tray()


def _linux_register_tray():
    """Adds tray app to XDG autostart."""
    autostart_dir = os.path.expanduser("~/.config/autostart")
    os.makedirs(autostart_dir, exist_ok=True)
    desktop_file = os.path.join(autostart_dir, "zentra-tray.desktop")
    with open(desktop_file, "w") as f:
        f.write(f"""[Desktop Entry]
Type=Application
Name=Zentra Core Tray
Comment=Zentra Core Agentic OS system tray icon
Exec={sys.executable} -m zentra.tray.tray_app
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
""")
    print("[+] Tray icon registered for autostart (~/.config/autostart/zentra-tray.desktop).")


def _linux_uninstall():
    print("[Linux] Removing Zentra Core systemd service...")
    subprocess.run(["systemctl", "--user", "stop", "zentra"], check=False)
    subprocess.run(["systemctl", "--user", "disable", "zentra"], check=False)
    service_path = os.path.expanduser("~/.config/systemd/user/zentra.service")
    desktop_path = os.path.expanduser("~/.config/autostart/zentra-tray.desktop")
    for p in [service_path, desktop_path]:
        if os.path.exists(p):
            os.remove(p)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    print("[+] Zentra Core service and tray startup removed.")


def _linux_status():
    result = subprocess.run(
        ["systemctl", "--user", "status", "zentra"],
        capture_output=True, text=True
    )
    print(result.stdout or result.stderr)


# ─────────────────────────── MAIN ───────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Zentra Core — Service Installer",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--install", action="store_true", help="Install Zentra as a system service")
    parser.add_argument("--uninstall", action="store_true", help="Remove the system service")
    parser.add_argument("--status", action="store_true", help="Show service status")
    parser.add_argument("--tray", action="store_true", help="Launch the tray icon directly (no service)")

    args = parser.parse_args()

    if args.tray:
        os.chdir(_ROOT)
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tray_app",
            os.path.join(_ROOT, "zentra", "tray", "tray_app.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.run_tray()
        return

    if sys.platform == "win32":
        if args.install:
            _win_install()
        elif args.uninstall:
            _win_uninstall()
        elif args.status:
            _win_status()
        else:
            parser.print_help()
    else:
        if args.install:
            _linux_install()
        elif args.uninstall:
            _linux_uninstall()
        elif args.status:
            _linux_status()
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
