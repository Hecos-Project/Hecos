# hecos/setup/web_ui/server.py
# Core HTTP server and request routing.
# Inherits from TemplateMixin to gain access to all render methods.

import os
import sys
import io
import contextlib
import http.server
import urllib.parse
import webbrowser

from .. import i18n
from ..engine import (
    check_python_version, check_dependencies,
    auto_fix_piper_path, set_system_language,
    unattended_onboarding
)
from ..utils import LOGO_PATH
from ..uninstaller import GlobalUninstaller

from . import state
from .templates import TemplateMixin


class SetupHTTPRequestHandler(http.server.BaseHTTPRequestHandler, TemplateMixin):
    """Handles HTTP routing for the Web UI Setup Wizard."""

    def do_GET(self):
        if self.path == '/logo.png':
            if os.path.exists(LOGO_PATH):
                self.send_response(200)
                self.send_header('Content-type', 'image/png')
                self.end_headers()
                with open(LOGO_PATH, 'rb') as f:
                    try:
                        self.wfile.write(f.read())
                    except (ConnectionAbortedError, ConnectionResetError):
                        pass
            else:
                self.send_error(404)
            return

        if self.path == '/':
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

        if self.path == '/toggle_ui_lang':
            i18n.UI_LANG = "it" if i18n.UI_LANG == "en" else "en"
            self.redirect_to_home()
        elif self.path == '/clear':
            state.LAST_RESULTS.clear()
            self.redirect_to_home()
        elif self.path.startswith('/preview_lang'):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            i18n.UI_LANG = query.get('lang', ['en'])[0]
            self.redirect_to_home()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        params_raw = urllib.parse.parse_qs(post_data)
        params = {k: v[0] if len(v) == 1 else v for k, v in params_raw.items()}

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            if self.path == '/select_setup_lang':
                i18n.UI_LANG = params.get('lang', 'en')
                i18n.SPLASH_DONE = True
            elif self.path == '/set_lang':
                set_system_language(params.get('lang', 'en'))
            elif self.path == '/onboarding':
                v_list = params.get('voices', [])
                if isinstance(v_list, str): v_list = [v_list]
                unattended_onboarding(target_voices=v_list)
                state.ONBOARDING_DONE = True
                print("\n" + "="*60, file=sys.__stdout__)
                print("[+] INSTALLATION COMPLETE! / INSTALLAZIONE COMPLETATA!", file=sys.__stdout__)
                print("[*] You can now safely close this window and launch Hecos.", file=sys.__stdout__)
                print("[*] Puoi chiudere questa finestra e avviare Hecos dal desktop.", file=sys.__stdout__)
                print("="*60 + "\n", file=sys.__stdout__)
            elif self.path == '/fix':
                auto_fix_piper_path()
            elif self.path == '/full_check':
                check_python_version()
                check_dependencies()
                auto_fix_piper_path()
            elif self.path == '/uninstall_hecos':
                # Smart uninstall: remove only Hecos deps (safe for shared Python envs)
                uninstaller = GlobalUninstaller()
                uninstaller.execute_full_uninstall()
                state.SMART_UNINSTALL_DONE = True
            elif self.path == '/uninstall':
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
        self.send_header('Location', '/')
        self.end_headers()

    def send_html(self, html):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        try:
            self.wfile.write(html.encode('utf-8'))
        except (ConnectionAbortedError, ConnectionResetError):
            pass


def start_web_setup():
    """Starts the Setup Wizard web server."""
    port = 8080
    server = http.server.HTTPServer(('0.0.0.0', port), SetupHTTPRequestHandler)
    print(f"\n[+] Hecos Setup Wizard (WebUI) started at:")
    print(f"    http://localhost:{port}")
    webbrowser.open(f"http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
