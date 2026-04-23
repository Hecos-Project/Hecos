"""
MODULE: zentra/service/windows_service.py
PURPOSE: Registers Zentra Core as a native Windows Service (visible in services.msc).
REQUIREMENTS: pywin32 (pip install pywin32)

USAGE:
  Install:   python -m zentra.service.windows_service install
  Start:     python -m zentra.service.windows_service start
  Stop:      python -m zentra.service.windows_service stop
  Remove:    python -m zentra.service.windows_service remove
"""

import sys
import os
import subprocess
import time

try:
    import win32service
    import win32serviceutil
    import win32event
    import servicemanager
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MONITOR_PATH = os.path.join(_ROOT, "zentra", "monitor.py")
SERVICE_NAME = "ZentraCore"
SERVICE_DISPLAY = "Zentra Core — Agentic OS"
SERVICE_DESC = "Native Modular AI Operating System background service. Manages the AI kernel, WebUI, and all cognitive subsystems."


if WIN32_AVAILABLE:
    class ZentraService(win32serviceutil.ServiceFramework):
        _svc_name_ = SERVICE_NAME
        _svc_display_name_ = SERVICE_DISPLAY
        _svc_description_ = SERVICE_DESC
        _svc_startType_ = win32service.SERVICE_AUTO_START

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.process = None

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except Exception:
                    self.process.kill()
            win32event.SetEvent(self.stop_event)

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, "")
            )
            self._run()

        def _run(self):
            env = os.environ.copy()
            env["PYTHONPATH"] = _ROOT + os.pathsep + env.get("PYTHONPATH", "")
            env["ZENTRA_SERVICE_MODE"] = "1"

            # Ensure logs directory exists
            log_dir = os.path.join(_ROOT, "zentra", "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file_path = os.path.join(log_dir, "zentra_service.log")

            # In a pywin32 service, sys.executable is usually 'pythonservice.exe'.
            # We need the real 'python.exe' to execute our monitor.
            python_exe = os.path.join(sys.prefix, "python.exe")
            if not os.path.exists(python_exe):
                python_exe = sys.executable.lower().replace("pythonservice.exe", "python.exe")
            if not os.path.exists(python_exe):
                python_exe = "python"  # ultimate fallback

            while True:
                with open(log_file_path, "a", encoding="utf-8") as f:
                    try:
                        f.write(f"\n--- Starting Zentra Service {time.ctime()} ---\n")
                        f.flush()
                        self.process = subprocess.Popen(
                            [python_exe, MONITOR_PATH, "--script", "zentra.modules.web_ui.server"],
                            cwd=_ROOT,
                            env=env,
                            stdout=f,
                            stderr=subprocess.STDOUT
                        )
                    except Exception as e:
                        f.write(f"Failed to start process: {e}\n")

                # Wait until the process exits or stop is signaled
                while self.process.poll() is None:
                    rc = win32event.WaitForSingleObject(self.stop_event, 2000)
                    if rc == win32event.WAIT_OBJECT_0:
                        # Service stop was requested
                        self.SvcStop()
                        return

                # If monitor exited naturally without stop signal, restart it
                rc = win32event.WaitForSingleObject(self.stop_event, 0)
                if rc == win32event.WAIT_OBJECT_0:
                    return  # Stop requested
                
                time.sleep(3)  # Brief pause before restart


def _fallback_install():
    """Fallback: create a simple startup task via schtasks if pywin32 is not available."""
    python_exe = sys.executable
    bat_path = os.path.join(_ROOT, "ZENTRA_WEB_RUN_WIN.bat")
    task_args = [
        "schtasks", "/Create", "/TN", "ZentraCore",
        "/TR", f'"{bat_path}"',
        "/SC", "ONLOGON",
        "/RL", "HIGHEST",
        "/F"
    ]
    result = subprocess.run(task_args, capture_output=True, text=True, shell=True)
    if result.returncode == 0:
        print("[+] Zentra startup task registered via Task Scheduler (pywin32 fallback).")
    else:
        print(f"[-] Task Scheduler registration failed: {result.stderr}")


def main():
    if not WIN32_AVAILABLE:
        print("[!] pywin32 not found. Falling back to Task Scheduler registration.")
        if "--install" in sys.argv or "install" in sys.argv:
            _fallback_install()
        return

    if len(sys.argv) == 1:
        # Running from Service Control Manager (SCM)
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(ZentraService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(ZentraService)


if __name__ == "__main__":
    main()
