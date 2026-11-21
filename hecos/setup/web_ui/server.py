# hecos/setup/web_ui/server.py
# Core HTTP server and request routing (localhost-only, CSRF-protected).
# Inherits from TemplateMixin to gain access to all render methods.

import contextlib
import http.server
import io
import os
import secrets
import sys
import urllib.parse
import webbrowser

from .. import i18n
from ..engine import (
    auto_fix_piper_path,
    check_dependencies,
    check_python_version,
    set_system_language,
    unattended_onboarding,
)
from ..uninstaller import GlobalUninstaller
from ..utils import LOGO_PATH
from . import state
from .templates import TemplateMixin


class SetupHTTPRequestHandler(http.server.BaseHTTPRequestHandler, TemplateMixin):
    """Handles HTTP routing for the Web UI Setup Wizard."""

    def do_GET(self):
        if self.path == "/logo.png":
            if os.path.exists(LOGO_PATH):
                self.send_response(200)
                self.send_header("Content-type", "image/png")
                self.end_headers()
                with open(LOGO_PATH, "rb") as f:
                    try:
                        self.wfile.write(f.read())
                    except (ConnectionAbortedError, ConnectionResetError):
                        pass
            else:
                self.send_error(404)
            return

        if self.path == "/":
            if state.UNINSTALL_DONE:
                self.render_uninstall_done()
                return
            if state.SMART_UNINSTALL_DONE:
                self.render_smart_uninstall_done()
                return
            if state.WIPE_DONE:
                self.render_wipe_done()
                return
            if not i18n.SPLASH_DONE:
                self.render_splash()
                return
            if state.ONBOARDING_DONE:
                self.render_done()
                return
            self.render_wizard()
            return

        if self.path == "/toggle_ui_lang":
            i18n.UI_LANG = "it" if i18n.UI_LANG == "en" else "en"
            self.redirect_to_home()
        elif self.path == "/clear":
            state.LAST_RESULTS.clear()
            self.redirect_to_home()
        elif self.path.startswith("/preview_lang"):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            i18n.UI_LANG = query.get("lang", ["en"])[0]
            self.redirect_to_home()
        else:
            self.send_error(404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        post_data = self.rfile.read(content_length).decode("utf-8", errors="replace")
        params_raw = urllib.parse.parse_qs(post_data)
        params = {k: v[0] if len(v) == 1 else v for k, v in params_raw.items()}

        # Verify per-session CSRF token on every state-changing POST
        provided_token = str(params.get("csrf_token", ""))
        if not provided_token or not secrets.compare_digest(provided_token, state.SESSION_TOKEN):
            self.send_error(403, "Invalid or missing setup session token. Refresh the page and retry.")
            return

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            if self.path == "/select_setup_lang":
                i18n.UI_LANG = params.get("lang", "en")
                i18n.SPLASH_DONE = True
            elif self.path == "/set_lang":
                set_system_language(params.get("lang", "en"))
            elif self.path == "/onboarding":
                v_list = params.get("voices", [])
                if isinstance(v_list, str):
                    v_list = [v_list]
                ok = unattended_onboarding(target_voices=v_list)
                if ok:
                    state.ONBOARDING_DONE = True
                    print("\n" + "=" * 60, file=sys.__stdout__)
                    print("[ OK ] INSTALLATION COMPLETE! / INSTALLAZIONE COMPLETATA!", file=sys.__stdout__)
                    print("[ .. ] You can now safely close this window and launch Hecos.", file=sys.__stdout__)
                    print("[ .. ] Puoi chiudere questa finestra e avviare Hecos.", file=sys.__stdout__)
                    print("=" * 60 + "\n", file=sys.__stdout__)
                else:
                    print("\n[FAIL] Installation encountered critical errors. Check log output above.", file=sys.__stdout__)
            elif self.path == "/fix":
                auto_fix_piper_path()
            elif self.path == "/full_check":
                check_python_version()
                check_dependencies()
                auto_fix_piper_path()
            elif self.path == "/uninstall_hecos":
                # Smart uninstall: remove only Hecos deps (safe for shared Python envs)
                uninstaller = GlobalUninstaller()
                uninstaller.execute_full_uninstall()
                state.SMART_UNINSTALL_DONE = True
            elif self.path == "/uninstall":
                # Full wipe: remove ALL pip packages (for dedicated Hecos environments)
                uninstaller = GlobalUninstaller()
                uninstaller.execute_wipe_all_packages()
                state.UNINSTALL_DONE = True

        out_text = output.getvalue().strip()
        if out_text:
            state.LAST_RESULTS.append(out_text)

        self.redirect_to_home()

    def redirect_to_home(self):
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def send_html(self, html):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        try:
            self.wfile.write(html.encode("utf-8"))
        except (ConnectionAbortedError, ConnectionResetError):
            pass


def _bind_local_server():
    """Bind ThreadingHTTPServer strictly to 127.0.0.1 with automatic port fallback."""
    for port in range(8080, 8100):
        try:
            return http.server.ThreadingHTTPServer(("127.0.0.1", port), SetupHTTPRequestHandler)
        except OSError:
            continue
    return http.server.ThreadingHTTPServer(("127.0.0.1", 0), SetupHTTPRequestHandler)


def start_web_setup():
    """Starts the localhost-only Setup Wizard web server."""
    server = _bind_local_server()
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}"
    print("\n[ OK ] Hecos Setup Wizard (WebUI, localhost-only) started at:")
    print(f"       {url}")
    print("       Press Ctrl+C in this terminal to stop the setup server.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
