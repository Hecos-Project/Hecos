import base64
import os
import subprocess
import sys
from flask import request, jsonify


def _build_win_filter_string(filetypes) -> str:
    """Build Windows Forms FileDialog filter string: 'Label (*.json)|*.json|All Files (*.*)|*.*'."""
    parts = []
    for ft in (filetypes or []):
        label = ft[0] if len(ft) > 0 else "Files"
        pattern = ft[1] if len(ft) > 1 else "*.*"
        tokens = str(pattern).split()
        if len(tokens) > 1 and all("*" in tok for tok in tokens):
            pattern = ";".join(tokens)
        clean_label = str(label).replace("'", "''").replace("|", "-")
        clean_pattern = str(pattern).replace("'", "''").replace("|", ";")
        parts.append(f"{clean_label} ({clean_pattern})|{clean_pattern}")
    return "|".join(parts) if parts else "All Files (*.*)|*.*"


def pick_native_os_path(
    *,
    mode: str = "open",
    title: str = "Hecos — Select",
    initialdir: str = "",
    pick_dir: bool = False,
    filetypes=None,
    default_name: str = "",
    default_ext: str = "",
) -> str:
    """
    Open a real native OS file/folder dialog (Open, Save, or Folder) and return the chosen path,
    or '' if the user cancelled.
    - Windows: PowerShell System.Windows.Forms dialog with TopMost owner form (UTF-8 output).
    - Linux/macOS: tkinter.filedialog subprocess.
    """
    eff_mode = str(mode or "open").strip().lower()
    if filetypes is None:
        filetypes = [
            ["Image Files", "*.jpg *.jpeg *.png *.gif *.webp"],
            ["All Files", "*.*"],
        ]

    if sys.platform == "win32":
        clean_title = (title or "").replace("'", "''")
        clean_initdir = (initialdir or "").rstrip("\\").replace("'", "''")
        clean_default_name = (default_name or "").replace("'", "''")
        clean_default_ext = (default_ext or "").lstrip(".").replace("'", "''")

        preamble = """
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$form = New-Object System.Windows.Forms.Form
$form.TopMost = $true
$form.StartPosition = [System.Windows.Forms.FormStartPosition]::Manual
$form.Location = New-Object System.Drawing.Point(-32000, -32000)
$form.Size = New-Object System.Drawing.Size(1, 1)
$form.ShowInTaskbar = $false
$form.Show()
$form.Activate()
$form.BringToFront()
"""
        if pick_dir:
            ps_script = preamble + f"""
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.AutoUpgradeEnabled = $true
$dialog.Description = '{clean_title}'
$dialog.ShowNewFolderButton = $true
if ('{clean_initdir}' -and (Test-Path '{clean_initdir}')) {{
    $dialog.SelectedPath = '{clean_initdir}'
}}
$result = $dialog.ShowDialog($form)
$form.Dispose()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {{
    [Console]::Out.Write($dialog.SelectedPath)
}}
"""
        elif eff_mode == "save":
            filter_str = _build_win_filter_string(filetypes)
            ps_script = preamble + f"""
$dialog = New-Object System.Windows.Forms.SaveFileDialog
$dialog.AutoUpgradeEnabled = $true
$dialog.OverwritePrompt = $true
$dialog.AddExtension = $true
$dialog.Title = '{clean_title}'
$dialog.Filter = '{filter_str}'
if ('{clean_default_name}') {{
    $dialog.FileName = '{clean_default_name}'
}}
if ('{clean_default_ext}') {{
    $dialog.DefaultExt = '{clean_default_ext}'
}}
if ('{clean_initdir}' -and (Test-Path '{clean_initdir}')) {{
    $dialog.InitialDirectory = '{clean_initdir}'
}}
$result = $dialog.ShowDialog($form)
$form.Dispose()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {{
    [Console]::Out.Write($dialog.FileName)
}}
"""
        else:
            filter_str = _build_win_filter_string(filetypes)
            ps_script = preamble + f"""
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.AutoUpgradeEnabled = $true
$dialog.Title = '{clean_title}'
$dialog.Filter = '{filter_str}'
$dialog.Multiselect = $false
if ('{clean_initdir}' -and (Test-Path '{clean_initdir}')) {{
    $dialog.InitialDirectory = '{clean_initdir}'
}}
$result = $dialog.ShowDialog($form)
$form.Dispose()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {{
    [Console]::Out.Write($dialog.FileName)
}}
"""
        b64_cmd = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")
        result = subprocess.run(
            ["powershell", "-NoProfile", "-STA", "-EncodedCommand", b64_cmd],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        return (result.stdout or "").strip()

    # Linux / macOS: tkinter subprocess
    filetypes_repr = repr([tuple(x) for x in filetypes])
    if pick_dir:
        script = f"""
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)
root.lift()
root.focus_force()
path = filedialog.askdirectory(title={title!r}, initialdir={initialdir!r} if {bool(initialdir)!r} else None)
root.destroy()
print(path or '', end='')
"""
    elif eff_mode == "save":
        script = f"""
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)
ft = {filetypes_repr}
path = filedialog.asksaveasfilename(
    title={title!r},
    filetypes=ft,
    initialdir={initialdir!r} if {bool(initialdir)!r} else None,
    initialfile={default_name!r} if {bool(default_name)!r} else None,
    defaultextension={('.' + default_ext.lstrip('.'))!r} if {bool(default_ext)!r} else '',
)
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
path = filedialog.askopenfilename(title={title!r}, filetypes=ft, initialdir={initialdir!r} if {bool(initialdir)!r} else None)
root.destroy()
print(path or '', end='')
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    return (result.stdout or "").strip()


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
        """Opens a native OS file/folder dialog (open, save, or folder) and returns the selected path."""
        try:
            data = request.get_json(force=True, silent=True) or {}
            path = pick_native_os_path(
                mode=data.get("mode", "open"),
                title=data.get("title", "Hecos — Select"),
                initialdir=data.get("initialdir", "") or "",
                pick_dir=bool(data.get("pick_dir", False)),
                filetypes=data.get("filetypes"),
                default_name=data.get("default_name", "") or "",
                default_ext=data.get("default_ext", "") or "",
            )
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
            if not path:
                from hecos.core.constants import MEDIA_DIR
                path = MEDIA_DIR
            if not os.path.exists(path):
                return jsonify({"ok": False, "error": "Invalid path"}), 400
            
            # If path is a file, open its parent
            if os.path.isfile(path):
                path = os.path.dirname(path)

            from hecos.core.system.os_adapter import OSAdapter
            details = OSAdapter.open_path_detailed(path)
            return jsonify({"ok": details.get("ok", False), "details": details})
        except Exception as e:
            logger.error(f"[EXPLORER] Open Folder Error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
