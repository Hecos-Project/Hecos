import os
import sys
from flask import request, jsonify

def init_explorer_routes(app, logger):
    """
    Initializes the web-native file explorer endpoints.
    These are used by the 'Hecos File Picker' component.
    """

    @app.route("/api/system/explorer/drives", methods=["GET"])
    def explorer_drives():
        """Lists available Windows drives or root for Linux."""
        try:
            if sys.platform == "win32":
                import string
                from ctypes import windll
                drives = []
                bitmask = windll.kernel32.GetLogicalDrives()
                for letter in string.ascii_uppercase:
                    if bitmask & 1:
                        drives.append(f"{letter}:\\")
                    bitmask >>= 1
                return jsonify({"ok": True, "drives": drives})
            else:
                return jsonify({"ok": True, "drives": ["/"]})
        except Exception as e:
            logger.error(f"[EXPLORER] Error listing drives: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/system/explorer/ls", methods=["POST"])
    def explorer_ls():
        """Lists directory contents with unified path handling."""
        try:
            data = request.get_json(force=True) or {}
            path = data.get("path")
            
            if not path or not os.path.exists(path):
                return jsonify({"ok": False, "error": "Invalid path"}), 400
            
            path = os.path.abspath(path)
            
            # If path is a file, use its parent directory instead
            if os.path.isfile(path):
                path = os.path.dirname(path)

            # Ensure it ends with slash if it's a drive root (Windows)
            if sys.platform == "win32" and len(path) == 2 and path[1] == ":":
                path += "\\"

            entries = []
            try:
                with os.scandir(path) as it:
                    for entry in it:
                        try:
                            # Skip hidden files
                            if entry.name.startswith('.') and sys.platform != "win32":
                                continue
                            
                            entries.append({
                                "name": entry.name,
                                "path": entry.path,
                                "type": "dir" if entry.is_dir() else "file"
                            })
                        except Exception: continue
            except PermissionError:
                return jsonify({"ok": False, "error": "Access Denied"}), 403

            # Sort: dirs first, then files
            entries.sort(key=lambda x: (x["type"] != "dir", x["name"].lower()))
            
            parent = os.path.dirname(path)
            # Handle drive root parent (same as path in Windows)
            if parent == path:
                parent = None

            return jsonify({
                "ok": True,
                "current": path,
                "parent": parent,
                "entries": entries
            })
        except Exception as e:
            logger.error(f"[EXPLORER] Error listing path: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/system/explorer/pick-native", methods=["POST"])
    def explorer_pick_native():
        """Opens a native OS file/folder dialog and returns the selected path.
        - Windows: uses PowerShell System.Windows.Forms dialog (works from headless servers).
        - Linux/Mac: spawns a subprocess with tkinter (requires display).
        """
        try:
            import subprocess

            data        = request.get_json(force=True, silent=True) or {}
            d_title     = data.get("title", "Hecos — Select")
            d_initdir   = data.get("initialdir", "") or ""
            pick_dir    = data.get("pick_dir", False)
            d_filetypes = data.get("filetypes", [
                ["Image Files", "*.jpg *.jpeg *.png *.gif *.webp"],
                ["All Files",   "*.*"]
            ])

            if sys.platform == "win32":
                # ── Windows: PowerShell native dialog ─────────────────────────
                # Build the filter string: "WAV Audio (*.wav)|*.wav|All Files (*.*)|*.*"
                filter_parts = []
                for ft in d_filetypes:
                    label = ft[0] if len(ft) > 0 else "Files"
                    pattern = ft[1] if len(ft) > 1 else "*.*"
                    filter_parts.append(f"{label} ({pattern})|{pattern}")
                filter_str = "|".join(filter_parts) if filter_parts else "All Files (*.*)|*.*"

                if pick_dir:
                    ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = '{d_title.replace("'", "`'")}'
$dialog.ShowNewFolderButton = $true
if ('{d_initdir}') {{ $dialog.SelectedPath = '{d_initdir.replace("'", "`'")}' }}
$dialog.TopMost = $true
$result = $dialog.ShowDialog()
if ($result -eq 'OK') {{ Write-Host $dialog.SelectedPath -NoNewline }}
"""
                else:
                    ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = '{d_title.replace("'", "`'")}'
$dialog.Filter = '{filter_str}'
$dialog.Multiselect = $false
if ('{d_initdir}') {{ $dialog.InitialDirectory = '{d_initdir.replace("'", "`'")}' }}
[System.Windows.Forms.Application]::EnableVisualStyles()
$result = $dialog.ShowDialog()
if ($result -eq 'OK') {{ Write-Host $dialog.FileName -NoNewline }}
"""
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                    capture_output=True, text=True, timeout=300
                )
                path = result.stdout.strip()

            else:
                # ── Linux / Mac: tkinter subprocess ───────────────────────────
                filetypes_repr = repr([tuple(x) for x in d_filetypes])
                if pick_dir:
                    script = f"""
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)
path = filedialog.askdirectory(title={d_title!r}, initialdir={d_initdir!r} if {bool(d_initdir)!r} else None)
root.destroy()
print(path or '', end='')
"""
                else:
                    script = f"""
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)
ft = {filetypes_repr}
path = filedialog.askopenfilename(title={d_title!r}, filetypes=ft, initialdir={d_initdir!r} if {bool(d_initdir)!r} else None)
root.destroy()
print(path or '', end='')
"""
                result = subprocess.run(
                    [sys.executable, "-c", script],
                    capture_output=True, text=True, timeout=300
                )
                path = result.stdout.strip()

            logger.info(f"[EXPLORER] Native pick result: {path!r}")
            return jsonify({"ok": True, "path": path})

        except Exception as e:
            logger.error(f"[EXPLORER] Native Pick Error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500




    @app.route("/api/system/explorer/open-folder", methods=["POST"])

    def explorer_open_folder():
        """Opens a folder in the native OS explorer."""
        try:
            data = request.get_json(force=True) or {}
            path = data.get("path")
            if not path or not os.path.exists(path):
                return jsonify({"ok": False, "error": "Invalid path"}), 400
            
            # If path is a file, open its parent
            if os.path.isfile(path):
                path = os.path.dirname(path)

            if sys.platform == "win32":
                os.startfile(path)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", path])
                
            return jsonify({"ok": True})
        except Exception as e:
            logger.error(f"[EXPLORER] Open Folder Error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
