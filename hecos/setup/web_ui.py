import os
import sys
import io
import re
import contextlib
import http.server
import urllib.parse
import webbrowser
from . import i18n
from .i18n import T
from .utils import (
    CWD, PIPER_DIR, SYSTEM_CONFIG_PATH, AUDIO_CONFIG_PATH, 
    LOGO_PATH, VOICE_MAP, safe_replace_yaml,
    TRAY_DIR, TRAY_DIR_VERSIONED, TRAY_DIR_CANONICAL
)
from .engine import (
    check_python_version, check_dependencies, install_dependencies,
    auto_fix_piper_path, set_system_language, download_voice,
    unattended_onboarding, fetch_piper_voices
)
from .uninstaller import GlobalUninstaller

LAST_RESULTS = []
ONBOARDING_DONE = False
UNINSTALL_DONE = False
WIPE_DONE = False

# Available Setup Languages
SETUP_LANGS = {
    "en": "English",
    "it": "Italiano",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch"
}

class SetupHTTPRequestHandler(http.server.BaseHTTPRequestHandler):

    def _render_tray_banner(self):
        """Returns an HTML banner if the Tray folder is missing or has a version suffix."""
        if TRAY_DIR is None:
            return f"""
            <div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.35);
                        border-radius:10px; padding:16px 20px; margin-bottom:24px; display:flex; gap:14px; align-items:flex-start;">
                <span style="font-size:1.1rem; flex-shrink:0;">⚠️</span>
                <div>
                    <div style="font-size:0.8rem; font-weight:700; color:#ef4444; margin-bottom:4px;">Hecos Tray not found</div>
                    <div style="font-size:0.77rem; color:#9ca3af; line-height:1.6;">
                        The Hecos Tray folder was not found in <code style="color:#d1d5db;">C:\\</code>.<br>
                        Make sure the folder is placed at: <code style="color:#d1d5db;">{TRAY_DIR_CANONICAL}</code>
                    </div>
                </div>
            </div>"""
        if TRAY_DIR_VERSIONED:
            return f"""
            <div style="background:rgba(245,158,11,0.07); border:1px solid rgba(245,158,11,0.3);
                        border-radius:10px; padding:16px 20px; margin-bottom:24px; display:flex; gap:14px; align-items:flex-start;">
                <span style="font-size:1.1rem; flex-shrink:0;">📁</span>
                <div>
                    <div style="font-size:0.8rem; font-weight:700; color:#f59e0b; margin-bottom:4px;">Rename the Tray folder</div>
                    <div style="font-size:0.77rem; color:#9ca3af; line-height:1.6;">
                        Found: <code style="color:#d1d5db;">{TRAY_DIR}</code><br>
                        Please rename it to: <code style="color:#d1d5db;">{TRAY_DIR_CANONICAL}</code><br>
                        <span style="opacity:0.6;">The folder was downloaded from GitHub with a version suffix. Hecos requires the exact name <strong style="color:#d1d5db;">Hecos-Tray</strong>.</span>
                    </div>
                </div>
            </div>"""
        return ""  # all good, no banner needed

    def do_GET(self):

        global LAST_RESULTS
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
            if UNINSTALL_DONE:
                self.render_uninstall_done()
                return
            if WIPE_DONE:
                self.render_wipe_done()
                return
            if not i18n.SPLASH_DONE:
                self.render_splash()
                return
            if ONBOARDING_DONE:
                self.render_done()
                return
            self.render_wizard()
            return
            
        if self.path == '/toggle_ui_lang':
            i18n.UI_LANG = "it" if i18n.UI_LANG == "en" else "en"
            self.redirect_to_home()
        elif self.path == '/clear':
            LAST_RESULTS.clear()
            self.redirect_to_home()
        elif self.path.startswith('/preview_lang'):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            i18n.UI_LANG = query.get('lang', ['en'])[0]
            self.redirect_to_home()

    def do_POST(self):
        global LAST_RESULTS
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
                global ONBOARDING_DONE
                v_list = params.get('voices', [])
                if isinstance(v_list, str): v_list = [v_list]
                unattended_onboarding(target_voices=v_list)
                ONBOARDING_DONE = True
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
            elif self.path == '/uninstall':
                global UNINSTALL_DONE
                uninstaller = GlobalUninstaller()
                uninstaller.execute_full_uninstall()
                UNINSTALL_DONE = True
            elif self.path == '/wipe_all':
                global WIPE_DONE
                uninstaller = GlobalUninstaller()
                uninstaller.execute_wipe_all_packages()
                WIPE_DONE = True

        out_text = output.getvalue().strip()
        if out_text:
            LAST_RESULTS.append(out_text)
            
        self.redirect_to_home()

    def redirect_to_home(self):
        self.send_response(303)
        self.send_header('Location', '/')
        self.end_headers()

    def render_splash(self):
        lang_options = "".join([f'<option value="{k}" {"selected" if k == i18n.UI_LANG else ""}>{v}</option>' for k, v in SETUP_LANGS.items()])
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Hecos Setup - Welcome</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>{self.get_css_vars()}</style>
            <style>
                * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                body {{
                    display: flex; align-items: center; justify-content: center; min-height: 100vh;
                    background: var(--bg); font-family: 'Inter', system-ui, sans-serif; color: var(--text);
                }}
                .splash-card {{
                    background: var(--bg2); border: 1px solid var(--border); padding: 48px 40px;
                    border-radius: 16px; text-align: center; max-width: 380px; width: 90%;
                    box-shadow: 0 24px 64px rgba(0,0,0,0.5);
                }}
                .logo {{ height: 52px; margin-bottom: 24px; opacity: 0.9; }}
                .splash-title {{ font-size: 0.7rem; font-weight: 600; letter-spacing: 4px; color: var(--muted); text-transform: uppercase; margin-bottom: 28px; }}
                select {{
                    width: 100%; padding: 11px 14px; background: var(--bg3); color: var(--text);
                    border: 1px solid var(--border); border-radius: 8px; margin-bottom: 20px;
                    font-size: 0.88rem; font-family: inherit; appearance: none; cursor: pointer;
                    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236b7280' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
                    background-repeat: no-repeat; background-position: right 12px center;
                }}
                select:focus {{ outline: none; border-color: var(--accent); }}
                .btn-primary {{
                    background: var(--accent); color: #fff; padding: 11px 20px; border-radius: 8px;
                    font-weight: 600; border: none; width: 100%; cursor: pointer; font-size: 0.85rem;
                    font-family: inherit; letter-spacing: 0.5px; transition: opacity 0.15s, transform 0.15s;
                }}
                .btn-primary:hover {{ opacity: 0.88; transform: translateY(-1px); }}
            </style>
        </head>
        <body>
            <div class="splash-card">
                <img src="/logo.png" class="logo" alt="Logo">
                <div class="splash-title">{T('select_setup_lang')}</div>
                <form action="/select_setup_lang" method="POST">
                    <select name="lang" onchange="window.location.href='/preview_lang?lang='+this.value">
                        {lang_options}
                    </select>
                    <button class="btn-primary">{T('button_continue')} →</button>
                </form>
            </div>
        </body>
        </html>
        """
        self.send_html(html)

    def render_wizard(self):
        # Current Config
        sys_lang = "en"
        if os.path.exists(SYSTEM_CONFIG_PATH):
            with open(SYSTEM_CONFIG_PATH, 'r', encoding='utf-8') as f:
                m = re.search(r'language:\s*(.*)', f.read())
                if m: sys_lang = m.group(1).strip().lower()

        # Fetch Dynamic Voices
        voices = fetch_piper_voices()
        grouped = {}
        for k, v in voices.items():
            l = v.get("language", {}).get("name_english", "Other")
            if l not in grouped: grouped[l] = []
            grouped[l].append((k, v.get("name", "Unknown"), v.get("quality", "")))

        v_options = '<div class="voice-list">'
        if voices:
            for lang in sorted(grouped.keys()):
                v_options += f'<div class="voice-lang-label">{lang}</div>'
                for vk, vn, vq in sorted(grouped[lang], key=lambda x:x[1]):
                    v_options += f'''
                    <label class="voice-row">
                        <input type="checkbox" name="voices" value="{vk}" class="voice-check">
                        <span class="voice-name">{vn}</span><span class="voice-quality">{vq}</span>
                    </label>
                    '''
        else:
            v_options += f'<div class="error-msg">{T("err_dl", filename="voices.json", err="Connection Timeout")}<br><br><button type="button" class="btn-ghost" onclick="window.location.reload()">↺ Retry</button></div>'
        v_options += '</div>'

        res_html = f'<div class="console">{("<br>").join(LAST_RESULTS)}</div>' if LAST_RESULTS else ""

        html = f"""
        <!DOCTYPE html>
        <html lang="{i18n.UI_LANG}">
        <head>
            <meta charset="UTF-8">
            <title>{T('header')}</title>
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>{self.get_css_vars()}{self.get_main_styles()}</style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="/logo.png" class="logo-img" alt="Logo">
                    <h1 class="title-text">HECOS SETUP</h1>
                </div>

                <div class="card">
                    {res_html}
                    {self._render_tray_banner()}

                    <div class="section">
                        <div class="section-label">01 — {T('step_lang').upper()}</div>
                        <p class="tip">{T('tip_lang')}</p>
                        <p class="tip-sub">{T('tip_lang_multilingual')}</p>
                        <form action="/set_lang" method="POST" style="display:flex; gap:8px; margin-top:14px;">
                            <button name="lang" value="en" class="btn-lang {'btn-lang-active' if sys_lang == 'en' else ''}">English</button>
                            <button name="lang" value="it" class="btn-lang {'btn-lang-active' if sys_lang == 'it' else ''}">Italiano</button>
                        </form>
                    </div>

                    <form action="/onboarding" method="POST">
                        <div class="section">
                            <div class="section-label">02 — {T('step_voice').upper()}</div>
                            <p class="tip">{T('tip_voice')}</p>
                            {v_options}
                        </div>

                        <div class="install-block">
                            <div class="section-label" style="margin-bottom:10px;">03 — {T('step_install').upper()}</div>
                            <p class="tip" style="margin-bottom:20px;">{T('tip_onboarding')}</p>
                            <button id="launch-btn" class="btn-primary"
                                onclick="
                                    setTimeout(() => this.disabled=true, 10);
                                    this.textContent='Installing... Downloading AI Engine (100MB+). Please wait 1-2 minutes! DO NOT CLOSE!';
                                    document.getElementById('next-steps').style.display='block';
                                ">▶ Launch Setup</button>

                            <div id="next-steps" style="display:none; margin-top:24px; border-top:1px solid var(--border); padding-top:20px;">
                                <div class="next-label">What to do while you wait</div>
                                <div class="step-item">
                                    <span class="step-num">1</span>
                                    <div>
                                        <div class="step-title">Find the Hecos Tray Icon</div>
                                        <div class="step-desc">Look in the <strong>bottom-right corner of your taskbar</strong> (system clock area). Click <strong>▲</strong> to expand hidden icons.</div>
                                    </div>
                                </div>
                                <div class="step-item">
                                    <span class="step-num">2</span>
                                    <div>
                                        <div class="step-title">Right-click → <span style="color:var(--accent);">Start Core</span></div>
                                        <div class="step-desc">After setup completes, right-click the tray icon and click <strong>▶ Start Core</strong>.</div>
                                    </div>
                                </div>
                                <div class="step-item">
                                    <span class="step-num">3</span>
                                    <div>
                                        <div class="step-title">Auto-start is enabled</div>
                                        <div class="step-desc">The tray launches automatically on every Windows login.</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </form>

                    <div class="emergency">
                        <div class="section-label" style="color:var(--red-muted);">⚠ {T('section_emergency')}</div>
                        <div class="diag-row">
                            <form action="/full_check" method="POST">
                                <button class="btn-ghost">{T('btn_full_check')}</button>
                            </form>
                            <form action="/fix" method="POST">
                                <button class="btn-ghost">{T('btn_fix_paths')}</button>
                            </form>
                            <form action="/uninstall" method="POST" onsubmit="return confirm('Permanently uninstall Hecos? This will remove all its dependencies.');">
                                <button class="btn-ghost btn-danger-ghost" onclick="setTimeout(() => this.disabled=true, 10); this.textContent='Uninstalling... Check terminal for logs. Please wait 1-2 mins!';">{T('btn_uninstall_svc')} Hecos</button>
                            </form>
                        </div>
                    </div>
                </div>

                <div class="footer">
                    <a href="/toggle_ui_lang" class="btn-ghost" style="font-size:0.7rem;">UI: {i18n.UI_LANG.upper()}</a>
                    <a href="/clear" class="btn-ghost" style="font-size:0.7rem;">Clear Logs</a>
                </div>
            </div>
        </body>
        </html>
        """
        self.send_html(html)

    def render_done(self):
        res_html = f'<div class="console" style="max-height:300px;">{("<br>").join(LAST_RESULTS)}</div>' if LAST_RESULTS else ""
        html = f"""
        <!DOCTYPE html>
        <html lang="{i18n.UI_LANG}">
        <head>
            <meta charset="UTF-8">
            <title>Hecos — Installation Complete</title>
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>{self.get_css_vars()}{self.get_main_styles()}</style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="/logo.png" class="logo-img" alt="Logo">
                    <h1 class="title-text">HECOS SETUP</h1>
                </div>

                <div class="done-banner">
                    <div class="done-label">Installation Complete</div>
                    <div class="done-sub">All components have been installed. Hecos is ready.</div>
                </div>

                {res_html}

                <div class="card">
                    <div class="section-label" style="margin-bottom:16px;">How to start Hecos</div>
                    <div class="step-item">
                        <span class="step-num">1</span>
                        <div>
                            <div class="step-title">Find the tray icon</div>
                            <div class="step-desc">Look in the <strong>bottom-right taskbar</strong> near the clock. Expand hidden icons with <strong>▲</strong>.</div>
                        </div>
                    </div>
                    <div class="step-item">
                        <span class="step-num">2</span>
                        <div>
                            <div class="step-title">Right-click → <span style="color:var(--accent);">Start Core</span></div>
                            <div class="step-desc">A beep confirms Hecos is online. Your browser will open automatically.</div>
                        </div>
                    </div>
                    <div class="step-item">
                        <span class="step-num">3</span>
                        <div>
                            <div class="step-title">Auto-start is enabled</div>
                            <div class="step-desc">The tray launches automatically on every login — no action needed next time.</div>
                        </div>
                    </div>
                    <div class="close-note">✓ You can close this window and the terminal. Hecos runs independently in the background.</div>
                </div>
            </div>
        </body>
        </html>
        """
        self.send_html(html)

    def render_uninstall_done(self):
        res_html = f'<div class="console" style="max-height:300px;">{("<br>").join(LAST_RESULTS)}</div>' if LAST_RESULTS else ""
        html = f"""
        <!DOCTYPE html>
        <html lang="{i18n.UI_LANG}">
        <head>
            <meta charset="UTF-8">
            <title>Hecos — Uninstall Complete</title>
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>{self.get_css_vars()}{self.get_main_styles()}</style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="/logo.png" class="logo-img" alt="Logo">
                    <h1 class="title-text" style="color:var(--red-muted);">HECOS UNINSTALLER</h1>
                </div>
                <div class="done-banner" style="border-color:var(--red-muted); background:rgba(220,38,38,0.06);">
                    <div class="done-label" style="color:var(--red-muted);">Uninstallation Complete</div>
                    <div class="done-sub">Hecos dependencies and autostart shortcuts have been removed.</div>
                </div>
                {res_html}
                <div class="close-note">✓ You can safely close this window. You may also delete the Hecos folder from your computer.</div>
            </div>
        </body>
        </html>
        """
        self.send_html(html)

    def render_wipe_done(self):
        res_html = f'<div class="console" style="max-height:300px;">{("<br>").join(LAST_RESULTS)}</div>' if LAST_RESULTS else ""
        html = f"""
        <!DOCTYPE html>
        <html lang="{i18n.UI_LANG}">
        <head>
            <meta charset="UTF-8">
            <title>Hecos — Environment Wiped</title>
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>{self.get_css_vars()}{self.get_main_styles()}</style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="/logo.png" class="logo-img" alt="Logo">
                    <h1 class="title-text" style="color:var(--red-muted);">ENVIRONMENT WIPER</h1>
                </div>
                <div class="done-banner" style="border-color:var(--red-muted); background:rgba(220,38,38,0.06);">
                    <div class="done-label" style="color:var(--red-muted);">Python Environment Wiped</div>
                    <div class="done-sub">All packages (except pip) have been removed from the environment.</div>
                </div>
                {res_html}
                <div class="close-note">✓ The environment is clean. Run setup again to reinstall dependencies.</div>
            </div>
        </body>
        </html>
        """
        self.send_html(html)

    def send_html(self, html):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        try:
            self.wfile.write(html.encode('utf-8'))
        except (ConnectionAbortedError, ConnectionResetError):
            pass

    def get_css_vars(self):
        return """
        :root {
            --bg: #0c0e16; --bg2: #111420; --bg3: #181c2e;
            --accent: #5b7dff;
            --accent-dim: rgba(91,125,255,0.15);
            --accent-rgb: 91,125,255;
            --text: #d1d5db; --muted: #6b7280; --border: #1e2235;
            --red-muted: #ef4444;
        }
        """

    def get_main_styles(self):
        return """
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: var(--bg); color: var(--text);
            font-family: 'Inter', system-ui, sans-serif;
            font-size: 14px; line-height: 1.6;
            padding: 48px 20px; display: flex; justify-content: center;
        }
        a { color: inherit; text-decoration: none; }

        /* Layout */
        .container { max-width: 620px; width: 100%; }
        .header { text-align: center; margin-bottom: 40px; }
        .logo-img { height: 46px; margin-bottom: 12px; opacity: 0.85; }
        .title-text {
            font-size: 0.68rem; font-weight: 600; letter-spacing: 4px;
            color: var(--accent); text-transform: uppercase; margin: 0;
        }

        /* Card */
        .card {
            background: var(--bg2); border: 1px solid var(--border);
            border-radius: 14px; padding: 36px; margin-bottom: 16px;
        }

        /* Sections */
        .section { margin-bottom: 32px; }
        .section-label {
            font-size: 0.65rem; font-weight: 700; letter-spacing: 3px;
            color: var(--muted); text-transform: uppercase; margin-bottom: 10px;
        }
        .tip { font-size: 0.82rem; color: var(--muted); margin-bottom: 4px; }
        .tip-sub { font-size: 0.72rem; color: var(--accent); opacity: 0.55; font-style: italic; margin-top: 2px; }

        /* Language buttons */
        .btn-lang {
            padding: 8px 18px; border-radius: 7px; font-size: 0.8rem; font-weight: 500;
            border: 1px solid var(--border); background: var(--bg3); color: var(--muted);
            cursor: pointer; font-family: inherit; transition: border-color 0.15s, color 0.15s;
        }
        .btn-lang:hover { border-color: var(--accent); color: var(--text); }
        .btn-lang-active { border-color: var(--accent); color: var(--accent); background: var(--accent-dim); }

        /* Voice list */
        .voice-list {
            max-height: 180px; overflow-y: auto; background: var(--bg);
            border: 1px solid var(--border); border-radius: 8px;
            padding: 12px; margin-top: 12px;
            scrollbar-width: thin; scrollbar-color: var(--border) transparent;
        }
        .voice-lang-label {
            font-size: 0.6rem; font-weight: 700; letter-spacing: 2px;
            color: var(--accent); text-transform: uppercase; margin: 10px 0 6px 0; opacity: 0.7;
        }
        .voice-row {
            display: flex; align-items: center; gap: 10px; padding: 6px 8px;
            border-radius: 6px; cursor: pointer; font-size: 0.8rem; color: var(--text);
            transition: background 0.1s;
        }
        .voice-row:hover { background: var(--bg3); }
        .voice-check { accent-color: var(--accent); }
        .voice-name { flex: 1; }
        .voice-quality { font-size: 0.7rem; color: var(--muted); }

        /* Install block */
        .install-block {
            background: rgba(var(--accent-rgb), 0.04);
            border: 1px solid rgba(var(--accent-rgb), 0.15);
            border-radius: 12px; padding: 28px; margin: 32px 0;
        }
        .btn-primary {
            background: var(--accent); color: #fff; padding: 10px 22px;
            border-radius: 8px; font-weight: 600; border: none;
            cursor: pointer; font-size: 0.85rem; font-family: inherit;
            letter-spacing: 0.3px; transition: opacity 0.15s, transform 0.12s;
            display: inline-block;
        }
        .btn-primary:hover { opacity: 0.88; transform: translateY(-1px); }
        .btn-primary:disabled { opacity: 0.45; cursor: not-allowed; transform: none; }

        /* Next steps */
        .next-label {
            font-size: 0.65rem; font-weight: 700; letter-spacing: 2px;
            color: var(--accent); text-transform: uppercase; margin-bottom: 14px;
        }
        .step-item {
            display: flex; gap: 14px; padding: 12px 0;
            border-bottom: 1px solid var(--border);
        }
        .step-item:last-of-type { border-bottom: none; }
        .step-num {
            width: 22px; height: 22px; border-radius: 50%;
            border: 1px solid var(--accent); color: var(--accent);
            font-size: 0.7rem; font-weight: 700; flex-shrink: 0;
            display: flex; align-items: center; justify-content: center;
        }
        .step-title { font-size: 0.82rem; font-weight: 600; color: var(--text); margin-bottom: 3px; }
        .step-desc { font-size: 0.77rem; color: var(--muted); line-height: 1.5; }

        /* Emergency */
        .emergency { margin-top: 36px; padding-top: 24px; border-top: 1px solid var(--border); }
        .diag-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }

        /* Ghost buttons */
        .btn-ghost {
            padding: 7px 14px; border-radius: 7px; font-size: 0.75rem; font-weight: 500;
            border: 1px solid var(--border); background: transparent; color: var(--muted);
            cursor: pointer; font-family: inherit; transition: border-color 0.15s, color 0.15s;
            display: inline-block;
        }
        .btn-ghost:hover { border-color: var(--text); color: var(--text); }
        .btn-danger-ghost { border-color: rgba(239,68,68,0.3); color: var(--red-muted); }
        .btn-danger-ghost:hover { border-color: var(--red-muted); }

        /* Console */
        .console {
            background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
            padding: 16px; color: #7dd3b0; font-family: 'SF Mono', 'Fira Code', monospace;
            font-size: 0.75rem; max-height: 180px; overflow-y: auto;
            margin-bottom: 24px; line-height: 1.6;
            scrollbar-width: thin; scrollbar-color: var(--border) transparent;
        }
        .error-msg { color: var(--red-muted); font-size: 0.8rem; text-align: center; padding: 20px; }

        /* Done banner */
        .done-banner {
            background: rgba(var(--accent-rgb), 0.06); border: 1px solid rgba(var(--accent-rgb), 0.2);
            border-radius: 12px; padding: 28px; text-align: center; margin-bottom: 24px;
        }
        .done-label { font-size: 1rem; font-weight: 700; color: var(--accent); margin-bottom: 6px; }
        .done-sub { font-size: 0.82rem; color: var(--muted); }

        /* Footer */
        .footer { display: flex; justify-content: center; gap: 10px; margin-top: 20px; }
        .close-note {
            margin-top: 20px; padding: 12px 16px;
            background: var(--bg); border-radius: 8px;
            font-size: 0.75rem; color: var(--muted);
            border: 1px solid var(--border);
        }
        """

def start_web_setup():
    port = 8080
    server = http.server.HTTPServer(('0.0.0.0', port), SetupHTTPRequestHandler)
    print(f"\n[+] Hecos Setup Wizard (WebUI) started at:")
    print(f"    http://localhost:{port}")
    webbrowser.open(f"http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

