import os
import platform
import subprocess
from zentra.core.logging import logger

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
    def open_path(path: str):
        """Opens a file or folder using the default OS application."""
        current_os = OSAdapter.get_os()
        try:
            if current_os == 'windows':
                os.startfile(path)
            elif current_os == 'darwin':
                subprocess.Popen(["open", path])
            else: # linux or others
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            logger.error(f"[OS_ADAPTER] Failed to open path {path}: {e}")

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
