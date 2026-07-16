import os
import sys
import subprocess
import re
from .utils import CWD
from .i18n import T

class GlobalUninstaller:
    def __init__(self):
        self.toml_path = os.path.join(CWD, "pyproject.toml")

    def parse_core_dependencies(self):
        """Parse pyproject.toml to extract all dependencies for uninstallation."""
        packages = []
        if os.path.exists(self.toml_path):
            try:
                with open(self.toml_path, "r", encoding="utf-8") as f:
                    content = f.read()
                deps_match = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
                if deps_match:
                    packages.extend(re.findall(r'"([^"]+)"', deps_match.group(1)))
                
                service_match = re.search(r'service\s*=\s*\[(.*?)\]', content, re.DOTALL)
                if service_match:
                    packages.extend(re.findall(r'"([^"]+)"', service_match.group(1)))
            except Exception as e:
                print(f"[-] Warning: Failed to parse pyproject.toml for uninstall: {e}")

        # Clean constraints (e.g. "pydantic>=2.0" -> "pydantic")
        cleaned_packages = []
        for pkg in packages:
            pkg_name = re.split(r'[;>=<~]', pkg)[0].strip()
            if pkg_name:
                cleaned_packages.append(pkg_name)
                
        return cleaned_packages

    def remove_autostart(self):
        """Remove Hecos Tray from system autostart."""
        print("[*] Removing Hecos from system autostart...")
        if os.name == 'nt':
            script = os.path.join(CWD, "scripts", "windows", "setup", "DISABLE_TRAY_AUTOSTART.bat")
            if os.path.exists(script):
                try:
                    subprocess.run(["cmd", "/c", script, "--silent"], capture_output=True, text=True)
                    print("[+] Autostart removed (Windows batch).")
                except Exception as e:
                    print(f"[-] Error removing autostart: {e}")
            else:
                import winreg
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
                    winreg.DeleteValue(key, "HecosTray")
                    winreg.CloseKey(key)
                    print("[+] Autostart removed (Windows Registry).")
                except FileNotFoundError:
                    pass
                except Exception as e:
                    print(f"[-] Error removing autostart registry key: {e}")
        else:
            autostart_path = os.path.expanduser("~/.config/autostart/hecos-tray.desktop")
            if os.path.exists(autostart_path):
                try:
                    os.remove(autostart_path)
                    print("[+] Autostart removed (Linux).")
                except Exception as e:
                    print(f"[-] Error removing autostart: {e}")

    def uninstall_pip_packages(self, packages):
        """Uninstall pip packages in batches to avoid command line limits."""
        if not packages:
            return

        print(f"[*] Uninstalling {len(packages)} packages...")
        
        # Add hecos-core to uninstall list just in case it was installed via pip install -e .
        packages.append("hecos-core")
        
        # Batch by 10 to avoid too long commands
        batch_size = 10
        for i in range(0, len(packages), batch_size):
            batch = packages[i:i+batch_size]
            cmd = [sys.executable, "-m", "pip", "uninstall", "-y"] + batch
            try:
                subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                print(f"    - Uninstalled: {', '.join(batch)}")
            except Exception as e:
                print(f"[-] Warning: Error uninstalling batch {batch}: {e}")

    def parse_plugin_dependencies(self):
        """Parse HPM packages.db to extract pip requirements of all installed plugins."""
        plugin_packages = []
        db_path = os.path.join(CWD, "config", "data", "packages.db")
        if os.path.exists(db_path):
            try:
                import sqlite3
                import json
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT manifest_snapshot FROM packages")
                rows = cursor.fetchall()
                for row in rows:
                    try:
                        manifest = json.loads(row[0])
                        pip_reqs = manifest.get("pip_requirements") or []
                        for req in pip_reqs:
                            pkg_name = re.split(r'[;>=<~]', req)[0].strip()
                            if pkg_name and not pkg_name.startswith("#"):
                                plugin_packages.append(pkg_name)
                    except Exception:
                        pass
                conn.close()
            except Exception as e:
                print(f"[-] Warning: Failed to parse packages.db for uninstall: {e}")
        return plugin_packages

    def execute_full_uninstall(self):
        """Run the full uninstallation flow."""
        print("=" * 60)
        print("  HECOS SYSTEM UNINSTALLER")
        print("=" * 60)
        print()
        
        self.remove_autostart()
        
        core_packages = self.parse_core_dependencies()
        plugin_packages = self.parse_plugin_dependencies()
        all_packages = list(set(core_packages + plugin_packages))
        
        if all_packages:
            print(f"[*] Found {len(core_packages)} core dependencies and {len(plugin_packages)} plugin dependencies.")
            self.uninstall_pip_packages(all_packages)
        else:
            print("[-] No packages found to uninstall.")
            
        print("\n" + "=" * 60)
        print("  UNINSTALL COMPLETE!")
        print("=" * 60)
        print("[*] Hecos core and its dependencies have been uninstalled from Python.")
        print("[*] You can now safely close this window and delete the Hecos folder.")
        print("=" * 60 + "\n")
        return True

    def execute_wipe_all_packages(self):
        """Wipe ALL packages installed in the Python environment, excluding core tools."""
        print("=" * 60)
        print("  PYTHON ENVIRONMENT WIPER")
        print("=" * 60)
        print()
        
        self.remove_autostart()
        
        print("[*] Scanning Python environment for all installed packages...")
        try:
            output = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
            packages = []
            for line in output.splitlines():
                # Handling standard "pkg==1.0" or "pkg @ file://..."
                pkg_name = re.split(r'[=<>~@]', line)[0].strip()
                if pkg_name and pkg_name.lower() not in ["pip", "setuptools", "wheel"]:
                    packages.append(pkg_name)
                    
            if packages:
                print(f"[*] Found {len(packages)} packages to wipe.")
                self.uninstall_pip_packages(packages)
            else:
                print("[-] Python environment is already clean.")
        except Exception as e:
            print(f"[-] Error scanning environment: {e}")

        print("\n" + "=" * 60)
        print("  WIPE COMPLETE!")
        print("=" * 60)
        print("[*] All Python packages have been completely removed.")
        print("[*] You can now safely close this window.")
        print("=" * 60 + "\n")
        return True
