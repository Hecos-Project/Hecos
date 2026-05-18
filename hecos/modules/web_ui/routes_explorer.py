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
        """Opens a native OS file dialog and returns the selected path."""
        try:
            import tkinter as tk
            from tkinter import filedialog
            import threading
            from queue import Queue

            res_q = Queue()

            def _dialog_task(q):
                try:
                    root = tk.Tk()
                    root.withdraw()
                    root.attributes("-topmost", True)
                    
                    # Remove the 'feather' icon (Windows hack)
                    try:
                        # Use an empty photo to replace the icon
                        root.tk.call('wm', 'iconphoto', root._w, tk.PhotoImage(data=''))
                    except Exception: pass
                    
                    # Open dialog
                    path = filedialog.askopenfilename(
                        title="Hecos — Select Background Image",
                        filetypes=[
                            ("Image Files", "*.jpg *.jpeg *.png *.gif *.webp"),
                            ("All Files", "*.*")
                        ]
                    )
                    root.destroy()
                    q.put(path)
                except Exception as e:
                    q.put(e)

            t = threading.Thread(target=_dialog_task, args=(res_q,))
            t.start()
            # Wait for user (unlimited time for picker)
            t.join()
            
            result = res_q.get()
            if isinstance(result, Exception):
                raise result
                
            return jsonify({"ok": True, "path": result if result else ""})
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
