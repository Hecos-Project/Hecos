import os
import platform
import subprocess
from hecos.core.logging import logger

class OSAdapter:
    """
    Translates abstract system commands into OS-specific execution commands.
    Supports Windows, Linux, and MacOS (Darwin).
    """
    
    @staticmethod
    def get_os():
        """Returns the current OS string in lowercase ('windows', 'linux', 'darwin')."""
        return platform.system().lower()

    @staticmethod
    def open_path_detailed(path: str) -> dict:
        """
        Opens a file or folder using the native OS file explorer or default application.
        Returns a dict with execution details and diagnostics.
        """
        norm = os.path.normpath(os.path.abspath(path))
        if not os.path.exists(norm):
            try:
                os.makedirs(norm, exist_ok=True)
            except Exception:
                pass

        current_os = OSAdapter.get_os()
        try:
            if current_os == 'windows':
                # 1. Primary mechanism on Windows: direct explorer.exe via shell.
                # This is the proven method used across Hecos (audio config, models).
                cmd1 = f'explorer.exe "{norm}"'
                try:
                    subprocess.Popen(cmd1, shell=True)
                    logger.info(f"[OS_ADAPTER] Launched native explorer: {cmd1}")
                    return {"ok": True, "os": "windows", "method": cmd1, "path": norm}
                except Exception as e1:
                    logger.warning(f"[OS_ADAPTER] explorer.exe shell=True failed: {e1}")

                # 2. Fallback: PowerShell Start-Process explorer.exe
                cmd2 = f"Start-Process explorer.exe -ArgumentList '\"{norm}\"'"
                try:
                    subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", cmd2])
                    logger.info(f"[OS_ADAPTER] Launched explorer via PowerShell: {cmd2}")
                    return {"ok": True, "os": "windows", "method": f"powershell: {cmd2}", "path": norm}
                except Exception as e2:
                    logger.warning(f"[OS_ADAPTER] PowerShell Start-Process failed: {e2}")

                # 3. Fallback: cmd start ""
                cmd3 = f'start "" "{norm}"'
                try:
                    subprocess.Popen(cmd3, shell=True)
                    logger.info(f"[OS_ADAPTER] Launched via start command: {cmd3}")
                    return {"ok": True, "os": "windows", "method": cmd3, "path": norm}
                except Exception as e3:
                    logger.warning(f"[OS_ADAPTER] cmd start failed: {e3}")

                # 4. Fallback: os.startfile
                try:
                    os.startfile(norm)
                    logger.info(f"[OS_ADAPTER] Opened via os.startfile: {norm}")
                    return {"ok": True, "os": "windows", "method": f"os.startfile({norm})", "path": norm}
                except Exception as e4:
                    logger.error(f"[OS_ADAPTER] All Windows opening methods failed for {norm}: {e4}")
                    return {"ok": False, "os": "windows", "error": str(e4), "path": norm}

            elif current_os == 'darwin':
                cmd = f"open {norm}"
                try:
                    subprocess.Popen(["open", norm])
                    logger.info(f"[OS_ADAPTER] Opened on macOS: {cmd}")
                    return {"ok": True, "os": "darwin", "method": cmd, "path": norm}
                except Exception as e:
                    logger.error(f"[OS_ADAPTER] macOS open failed: {e}")
                    return {"ok": False, "os": "darwin", "error": str(e), "path": norm}

            else:  # Linux / Unix
                linux_tools = [
                    ["xdg-open", norm],
                    ["gio", "open", norm],
                    ["nautilus", norm],
                    ["dolphin", norm],
                    ["nemo", norm],
                    ["thunar", norm],
                    ["pcmanfm", norm],
                    ["caja", norm]
                ]
                for cmd in linux_tools:
                    try:
                        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        cmd_str = " ".join(cmd)
                        logger.info(f"[OS_ADAPTER] Launched Linux file manager: {cmd_str}")
                        return {"ok": True, "os": "linux", "method": cmd_str, "path": norm}
                    except (FileNotFoundError, OSError):
                        continue
                logger.warning(f"[OS_ADAPTER] No desktop file manager tool found to open {norm}")
                return {"ok": False, "os": "linux", "error": "No desktop file manager tool found (tried xdg-open, gio, nautilus, dolphin, nemo, thunar, pcmanfm, caja)", "path": norm}

        except Exception as e:
            logger.error(f"[OS_ADAPTER] Failed to open path {norm}: {e}")
            return {"ok": False, "os": current_os, "error": str(e), "path": norm}

    @staticmethod
    def open_path(path: str) -> bool:
        """Opens a file or folder using the native OS file explorer or default application."""
        return OSAdapter.open_path_detailed(path).get("ok", False)

    @staticmethod
    def open_terminal():
        """Opens the default OS terminal emulator in an independent process."""
        current_os = OSAdapter.get_os()
        try:
            if current_os == 'windows':
                subprocess.Popen("start cmd.exe", shell=True)
            elif current_os == 'darwin':
                subprocess.Popen(["open", "-a", "Terminal"])
            else:
                # Linux: try common terminal emulators
                terminals = ['gnome-terminal', 'konsole', 'xfce4-terminal', 'x-terminal-emulator', 'xterm']
                for term in terminals:
                    if subprocess.call(["which", term], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                        subprocess.Popen([term])
                        return
                logger.warning("[OS_ADAPTER] No supported terminal emulator found on Linux.")
        except Exception as e:
            logger.error(f"[OS_ADAPTER] Failed to open terminal: {e}")

    @staticmethod
    def get_network_info_cmd() -> str:
        """Returns the appropriate shell command to retrieve network interfaces info."""
        current_os = OSAdapter.get_os()
        if current_os == 'windows':
            return "ipconfig /all"
        else:
            return "ip a"

    @staticmethod
    def get_ping_cmd(target: str, count: int = 4) -> str:
        """Returns the appropriate shell command to ping a target."""
        current_os = OSAdapter.get_os()
        if current_os == 'windows':
            return f"ping -n {count} {target}"
        elif current_os == 'darwin':
            return f"ping -c {count} {target}"
        else:
            return f"ping -c {count} {target}"

    @staticmethod
    def get_arp_cmd() -> str:
        """Returns the appropriate shell command to retrieve ARP table."""
        # Both Windows and Linux systems typically support arp -a
        return "arp -a"
        
    @staticmethod
    def get_interfaces_cmd() -> str:
        """Returns the appropriate shell command to retrieve interface statistics/status."""
        current_os = OSAdapter.get_os()
        if current_os == 'windows':
            # Fast way to show status on Windows
            return "netsh interface show interface"
        else:
            # On Linux 'ip link' is standard
            return "ip link show"
            
    @staticmethod
    def is_process_running_cmd(process_name: str) -> str:
        """Returns the appropriate command to check if a process is running."""
        current_os = OSAdapter.get_os()
        if current_os == 'windows':
            return f'tasklist | findstr /I "{process_name}"'
        else:
            return f'pgrep -i "{process_name}"'

    @staticmethod
    def kill_process_cmd(process_name: str) -> str:
        """Returns the command to force kill a process by name."""
        current_os = OSAdapter.get_os()
        if current_os == 'windows':
            return f'taskkill /F /IM "{process_name}"'
        else:
            return f'pkill -9 -f "{process_name}"'

    @staticmethod
    def expand_user_folder(folder_name: str) -> str:
        """
        Takes a localized folder name (Desktop, Downloads, Documenti) 
        and normalizes it to the absolute OS path securely via os.path.
        """
        # We assume standard OS folders map to ~/{Name}
        base_path = os.path.expanduser("~")
        
        # Mappings for common generic names
        mappings = {
            "desktop": "Desktop",
            "download": "Downloads",
            "documenti": "Documents",
            "documents": "Documents",
            "musica": "Music",
            "music": "Music",
            "video": "Videos",
            "videos": "Videos"
        }
        
        key = folder_name.lower().strip()
        actual_name = mappings.get(key, folder_name.capitalize())
        
        # We rely on system expansion. Desktop can also be obtained with os.path.join
        return os.path.join(base_path, actual_name)
