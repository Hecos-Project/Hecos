# hecos/setup/web_ui/server.py
# Localhost-only, CSRF-protected HTTP/SSE server + Native App-Window Launcher
# for the Unified Hecos Setup Wizard (Core + Tray).

from __future__ import annotations

import contextlib
import http.server
import io
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import webbrowser
from typing import Any, Dict, Optional

from ..install_registry import is_valid_core_dir, validate_install_path
from ..unified_installer import (
    InstallJob,
    detect_environment_status,
    get_free_disk_gb,
    launch_hecos_now,
    pick_folder_dialog,
)
from ..utils import CWD, LOGO_PATH
from . import state
from .templates import TemplateMixin


class SetupHTTPRequestHandler(http.server.BaseHTTPRequestHandler, TemplateMixin):
    """Handles HTTP, JSON API, and SSE streaming routes for the Unified Setup Wizard."""

    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        # Keep console tidy during SSE & polling
        pass

    def _send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def send_html(self, html: str) -> None:
        raw = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _verify_csrf(self, body: Dict[str, Any]) -> bool:
        token = self.headers.get("X-CSRF-Token") or str(body.get("csrf_token", ""))
        return bool(token) and secrets.compare_digest(token, state.SESSION_TOKEN)

    def _local_core_hint(self) -> Optional[str]:
        if state.STANDALONE_MODE:
            return None
        return CWD if is_valid_core_dir(CWD) else None

    # ── GET Routes ───────────────────────────────────────────────────────────

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]

        if path == "/logo.png":
            if os.path.isfile(LOGO_PATH):
                with open(LOGO_PATH, "rb") as f:
                    raw = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                try:
                    self.wfile.write(raw)
                except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                    pass
            else:
                self.send_error(404)
            return

        if path == "/":
            status = detect_environment_status(local_core_hint=self._local_core_hint())
            self.render_unified_wizard(status)
            return

        if path == "/api/status":
            status = detect_environment_status(local_core_hint=self._local_core_hint())
            self._send_json(status)
            return

        if path == "/api/events":
            job = state.CURRENT_JOB
            if job is None:
                self.send_error(404, "No active installation job.")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                for ev in job.stream_events():
                    chunk = f"data: {json.dumps(ev)}\n\n".encode("utf-8")
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                pass
            return

        self.send_error(404)

    # ── POST Routes (ALL CSRF-protected) ─────────────────────────────────────

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        body = self._read_json_body()

        if not self._verify_csrf(body):
            self._send_json({"ok": False, "error": "Invalid or missing CSRF token."}, status=403)
            return

        if path == "/api/validate_path":
            target = str(body.get("path", "")).strip()
            ok, errs, warns = validate_install_path(target)
            self._send_json({
                "ok": ok,
                "errors": errs,
                "warnings": warns,
                "free_gb": get_free_disk_gb(target) if ok else None,
            })
            return

        if path == "/api/browse_folder":
            chosen = pick_folder_dialog(str(body.get("initial_dir", "")))
            self._send_json({"ok": bool(chosen), "path": chosen})
            return

        if path == "/api/install":
            if state.CURRENT_JOB is not None and not state.CURRENT_JOB.finished:
                self._send_json({"started": False, "error": "An installation is already running."}, status=409)
                return
            job = InstallJob(body)
            state.CURRENT_JOB = job
            job.start()
            self._send_json({"started": True})
            return

        if path == "/api/doctor":
            status = detect_environment_status(local_core_hint=self._local_core_hint())
            if not status["core_installed"]:
                self._send_json({"ok": False, "checks": [], "message": "Hecos Core is not installed yet on this PC."})
                return
            core_dir = status["core_path"]
            if not state.STANDALONE_MODE and os.path.normcase(os.path.abspath(core_dir)) == os.path.normcase(os.path.abspath(CWD)):
                from ..setup_env import run_doctor
                report = run_doctor()
                self._send_json(report)
                return
            # Spawn Core's own python if available
            cand_py = os.path.join(core_dir, "python_env", "python.exe" if os.name == "nt" else os.path.join("bin", "python3"))
            py_exe = cand_py if os.path.isfile(cand_py) else sys.executable
            try:
                out = subprocess.check_output(
                    [
                        py_exe,
                        "-c",
                        "import json, sys; sys.path.insert(0, sys.argv[1]); "
                        "from hecos.setup.setup_env import run_doctor; print(json.dumps(run_doctor()))",
                        core_dir,
                    ],
                    cwd=core_dir,
                    text=True,
                    timeout=30,
                )
                self._send_json(json.loads(out.strip()))
            except Exception as exc:
                self._send_json({"ok": False, "checks": [], "message": f"Doctor error: {exc}"})
            return

        if path == "/api/launch":
            ok, msg = launch_hecos_now(body.get("core_path"), body.get("tray_path"))
            self._send_json({"ok": ok, "message": msg})
            return

        if path in ("/api/uninstall_hecos", "/api/uninstall_wipe", "/uninstall_hecos", "/uninstall"):
            if state.STANDALONE_MODE:
                self._send_json({"ok": False, "output": "Run Uninstall from inside an installed Hecos Core folder."})
                return
            from ..uninstaller import GlobalUninstaller
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                uni = GlobalUninstaller()
                if path.endswith("wipe") or path == "/uninstall":
                    uni.execute_wipe_all_packages()
                else:
                    uni.execute_full_uninstall()
            self._send_json({"ok": True, "output": buf.getvalue()})
            return

        if path == "/api/shutdown":
            self._send_json({"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return

        self.send_error(404)


def _find_chromium_app_browser() -> Optional[str]:
    """Locate Edge/Chrome/Brave to open the wizard in a native app-mode desktop window."""
    if os.name == "nt":
        candidates = [
            os.path.join(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"), "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(os.environ.get("PROGRAMFILES", r"C:\Program Files"), "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(os.environ.get("PROGRAMFILES", r"C:\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        for name in ("msedge", "chrome", "brave"):
            found = shutil.which(name)
            if found:
                return found
    elif sys.platform == "darwin":
        for app in (
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ):
            if os.path.isfile(app):
                return app
    else:
        for name in ("microsoft-edge", "google-chrome", "chromium", "chromium-browser", "brave-browser"):
            found = shutil.which(name)
            if found:
                return found
    return None


def _has_graphical_display() -> bool:
    if os.name == "nt" or sys.platform == "darwin":
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _open_app_window(url: str) -> None:
    """Open the Setup Wizard in a dedicated chromeless desktop app window (with browser fallback)."""
    if not _has_graphical_display():
        port = url.rsplit(":", 1)[-1]
        print("       [INFO] Headless Linux detected (no DISPLAY/WAYLAND_DISPLAY).")
        print(f"       Open in a browser or forward via SSH: ssh -L {port}:127.0.0.1:{port} user@host")
        return

    browser = _find_chromium_app_browser()
    if browser:
        try:
            profile_dir = os.path.join(tempfile.gettempdir(), "hecos_setup_app_profile")
            os.makedirs(profile_dir, exist_ok=True)
            cmd = [
                browser,
                f"--app={url}",
                "--window-size=1000,720",
                "--new-window",
                f"--user-data-dir={profile_dir}",
                "--no-first-run",
                "--no-default-browser-check",
            ]
            kwargs: Dict[str, Any] = {
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            }
            if os.name != "nt":
                kwargs["start_new_session"] = True
            subprocess.Popen(cmd, **kwargs)
            return
        except Exception:
            pass
    webbrowser.open(url)


class _LocalSetupServer(http.server.ThreadingHTTPServer):
    """ThreadingHTTPServer that prevents silent port double-binding on Windows."""

    allow_reuse_address = (os.name != "nt")

    def server_bind(self) -> None:
        if os.name == "nt":
            import socket
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def _bind_local_server() -> http.server.ThreadingHTTPServer:
    """Bind strictly to 127.0.0.1 with reliable automatic port fallback (8080..8099)."""
    for port in range(8080, 8100):
        try:
            return _LocalSetupServer(("127.0.0.1", port), SetupHTTPRequestHandler)
        except OSError:
            continue
    return _LocalSetupServer(("127.0.0.1", 0), SetupHTTPRequestHandler)


def start_web_setup(standalone: bool = False, open_browser: bool = True) -> None:
    """Starts the Unified Graphical Setup Wizard in native app-window mode."""
    state.STANDALONE_MODE = standalone
    server = _bind_local_server()
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}"
    print("\n[ OK ] Hecos Unified Setup Wizard started (localhost-only):")
    print(f"       {url}")
    print("       Keep this window open while using the graphical installer (Ctrl+C to stop).")
    if open_browser:
        _open_app_window(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
