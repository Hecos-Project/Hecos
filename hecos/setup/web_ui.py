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
    LOGO_PATH, VOICE_MAP, safe_replace_yaml
)
from .engine import (
    check_python_version, check_dependencies, install_dependencies,
    auto_fix_piper_path, set_system_language, download_voice,
    unattended_onboarding, fetch_piper_voices
)

LAST_RESULTS = []
ONBOARDING_DONE = False

# Available Setup Languages
SETUP_LANGS = {
    "en": "English",
    "it": "Italiano",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch"
}

class SetupHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
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
            elif self.path == '/fix':
                auto_fix_piper_path()
            elif self.path == '/full_check':
                check_python_version()
                check_dependencies()
                auto_fix_piper_path()

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
            <style>{self.get_css_vars()}</style>
            <style>
                body {{ 
                    display: flex; align-items: center; justify-content: center; height: 100vh; 
                    margin: 0; background: var(--bg); font-family: 'Inter', sans-serif; color: #fff;
                    background-image: radial-gradient(circle at center, rgba(var(--accent-rgb), 0.1) 0%, transparent 70%);
                }}
                .splash-card {{ 
                    background: var(--bg2); border: 2px solid var(--accent); padding: 50px; 
                    border-radius: 24px; box-shadow: 0 0 40px var(--accent-dim); text-align: center;
                    max-width: 400px; width: 90%;
                }}
                select {{ 
                    width: 100%; padding: 15px; background: #000; color: #fff; 
                    border: 1px solid var(--border); border-radius: 10px; margin-bottom: 25px; 
                    appearance: auto; font-size: 1rem;
                }}
                .btn {{ 
                    background: var(--accent); color: #000; padding: 16px; border-radius: 12px; 
                    font-weight: 800; border: none; width: 100%; cursor: pointer; font-size: 1rem;
                }}
            </style>
        </head>
        <body>
            <div class="splash-card">
                <img src="/logo.png" style="height:80px; margin-bottom:20px;" alt="Logo">
                <h1 style="color:#fff; margin-bottom:10px; text-transform:uppercase; letter-spacing:1px;">{T('welcome')}</h1>
                <p style="color:var(--muted); margin-bottom:30px; font-size:0.9rem;">{T('select_setup_lang')}</p>
                <form action="/select_setup_lang" method="POST">
                    <select name="lang" onchange="window.location.href='/preview_lang?lang='+this.value">
                        {lang_options}
                    </select>
                    <button class="btn">{T('button_continue').upper()} ➔</button>
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

        v_options = '<div style="max-height:200px; overflow-y:auto; background:#000; border:1px solid var(--border); padding:15px; border-radius:10px; margin-bottom:20px;">'
        if voices:
            for lang in sorted(grouped.keys()):
                v_options += f'<div style="color:var(--accent); font-size:0.65rem; font-weight:bold; margin:15px 0 8px 0; opacity:0.8; text-transform:uppercase;">{lang}</div>'
                for vk, vn, vq in sorted(grouped[lang], key=lambda x:x[1]):
                    v_options += f'''
                    <label style="display:flex; align-items:center; color:#ccc; margin-bottom:6px; cursor:pointer; font-size:0.8rem; padding:6px; background:#111; border-radius:6px;">
                        <input type="checkbox" name="voices" value="{vk}" style="margin-right:10px;">
                        <span>{vn} <small style="opacity:0.5;">({vq})</small></span>
                    </label>
                    '''
        else:
            v_options += f'<div style="color:var(--red); padding:20px; text-align:center;">{T("err_dl", filename="voices.json", err="Connection Timeout")}<br><br><button type="button" class="btn btn-secondary" onclick="window.location.reload()">RETRY ↺</button></div>'
        v_options += '</div>'

        res_html = f'<div class="console">{"<br>".join(LAST_RESULTS)}</div>' if LAST_RESULTS else ""

        html = f"""
        <!DOCTYPE html>
        <html lang="{i18n.UI_LANG}">
        <head>
            <meta charset="UTF-8">
            <title>{T('header')}</title>
            <style>{self.get_css_vars()}{self.get_main_styles()}</style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="/logo.png" class="logo-img" alt="Logo">
                    <h1 class="title-text">{T('header').replace('HECOS CORE - ', '')}</h1>
                </div>

                <div class="card">
                    {res_html}
                    
                    <div class="section">
                        <h2>1️⃣ STEP: {T('step_lang').upper()}</h2>
                        <p class="tip">{T('tip_lang')}</p>
                        <p class="tip-sub">{T('tip_lang_multilingual')}</p>
                        <form action="/set_lang" method="POST" style="display:flex; gap:10px; margin-top:15px;">
                            <button name="lang" value="en" class="btn {'' if sys_lang == 'en' else 'btn-outline'}" style="flex:1;">English</button>
                            <button name="lang" value="it" class="btn {'' if sys_lang == 'it' else 'btn-outline'}" style="flex:1;">Italiano</button>
                        </form>
                    </div>

                    <form action="/onboarding" method="POST">
                        <div class="section">
                            <h2>2️⃣ STEP: {T('step_voice').upper()}</h2>
                            <p class="tip">{T('tip_voice')}</p>
                            {v_options}
                        </div>

                        <div class="hero">
                            <h2>3️⃣ STEP: {T('step_install').upper()}</h2>
                            <p class="tip">{T('tip_onboarding')}</p>
                            <button id="launch-btn" class="btn" style="width:100%; padding:20px; font-size:1.1rem; margin:0;"
                                onclick="
                                    this.innerHTML='⏳ INSTALLATION STARTED, PLEASE WAIT... (Check console for details)';
                                    this.style.pointerEvents='none';
                                    this.style.opacity='0.7';
                                    document.getElementById('next-steps').style.display='block';
                                ">🚀 LAUNCH TURNKEY SETUP</button>

                            <div id="next-steps" style="display:none; margin-top:28px; background:#0a1a15; border:1px solid var(--accent); border-radius:14px; padding:24px;">
                                <div style="color:var(--accent); font-size:0.9rem; font-weight:800; letter-spacing:1px; margin-bottom:16px;">✅ WHAT TO DO NEXT</div>
                                <p style="color:#ccc; font-size:0.85rem; margin:0 0 16px 0;">
                                    The installer is now running in the background. While you wait, read these instructions to start using Hecos once the setup is complete.
                                </p>
                                <div style="display:flex; flex-direction:column; gap:12px;">
                                    <div style="background:#111; border-radius:10px; padding:14px 16px; display:flex; gap:14px; align-items:flex-start;">
                                        <span style="font-size:1.4rem; line-height:1;">1️⃣</span>
                                        <div>
                                            <div style="color:#fff; font-size:0.82rem; font-weight:700; margin-bottom:4px;">Find the Hecos Tray Icon</div>
                                            <div style="color:#888; font-size:0.78rem; line-height:1.5;">
                                                Look at the <strong style="color:#ccc;">bottom-right corner of your taskbar</strong> (the system clock area). You may need to click the <strong style="color:#ccc;">▲ arrow</strong> to expand hidden icons. The Hecos icon will appear there after setup completes.
                                            </div>
                                        </div>
                                    </div>
                                    <div style="background:#111; border-radius:10px; padding:14px 16px; display:flex; gap:14px; align-items:flex-start;">
                                        <span style="font-size:1.4rem; line-height:1;">2️⃣</span>
                                        <div>
                                            <div style="color:#fff; font-size:0.82rem; font-weight:700; margin-bottom:4px;">Right-click the icon</div>
                                            <div style="color:#888; font-size:0.78rem; line-height:1.5;">
                                                Right-click on the Hecos icon to open the control menu, then click <strong style="color:var(--accent);">▶ Start Core</strong> to launch the Hecos AI engine.
                                            </div>
                                        </div>
                                    </div>
                                    <div style="background:#111; border-radius:10px; padding:14px 16px; display:flex; gap:14px; align-items:flex-start;">
                                        <span style="font-size:1.4rem; line-height:1;">3️⃣</span>
                                        <div>
                                            <div style="color:#fff; font-size:0.82rem; font-weight:700; margin-bottom:4px;">Hecos will start automatically on next login</div>
                                            <div style="color:#888; font-size:0.78rem; line-height:1.5;">
                                                The tray icon is configured to launch automatically every time you log into Windows, so you only need to do this manually the first time.
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div style="margin-top:18px; padding:12px 16px; background:rgba(0,255,204,0.06); border-radius:8px; border-left:3px solid var(--accent);">
                                    <span style="color:var(--accent); font-size:0.75rem; font-weight:700;">💡 TIP</span>
                                    <span style="color:#888; font-size:0.75rem; margin-left:8px;">You can also double-click the tray icon to open the Hecos Control Center directly.</span>
                                </div>
                            </div>
                        </div>
                    </form>

                    <div class="emergency">
                        <h2>{T('section_emergency')}</h2>
                        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap:15px; margin-top:20px;">
                            <div class="diag-item">
                                <span class="diag-tip">{T('tip_full_check')}</span>
                                <form action="/full_check" method="POST"><button class="btn btn-warn" style="width:100%">{T('btn_full_check')}</button></form>
                            </div>
                            <div class="diag-item">
                                <span class="diag-tip">{T('tip_fix_paths')}</span>
                                <form action="/fix" method="POST"><button class="btn btn-secondary" style="width:100%">{T('btn_fix_paths')}</button></form>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="footer">
                    <div style="color:var(--accent); font-size:0.8rem; font-weight:bold; margin-bottom:10px;">🛡️ {T('tip_change_later')}</div>
                    <div class="footer-links">
                        <a href="/toggle_ui_lang" class="btn btn-secondary" style="font-size:0.7rem;">UI: {i18n.UI_LANG.upper()}</a>
                        <a href="/clear" class="btn btn-secondary" style="font-size:0.7rem;">CLEAR LOGS</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        self.send_html(html)

    def render_done(self):
        res_html = f'<div class="console" style="max-height:300px;">{"<br>".join(LAST_RESULTS)}</div>' if LAST_RESULTS else ""
        html = f"""
        <!DOCTYPE html>
        <html lang="{i18n.UI_LANG}">
        <head>
            <meta charset="UTF-8">
            <title>Hecos — Installation Complete</title>
            <style>{self.get_css_vars()}{self.get_main_styles()}</style>
            <style>
                .done-card {{ background: linear-gradient(135deg, #0a1a15 0%, #0d1f18 100%); border: 2px solid var(--accent); border-radius: 20px; padding: 40px; text-align: center; margin-bottom: 30px; box-shadow: 0 0 60px rgba(0,255,204,0.15); }}
                .done-icon {{ font-size: 4rem; margin-bottom: 16px; }}
                .done-title {{ font-size: 1.8rem; font-weight: 900; color: var(--accent); letter-spacing: 2px; margin: 0 0 10px 0; }}
                .done-sub {{ color: #888; font-size: 0.9rem; margin: 0 0 30px 0; }}
                .step-card {{ background: #111; border-radius: 12px; padding: 16px 20px; display: flex; gap: 16px; align-items: flex-start; text-align: left; margin-bottom: 12px; }}
                .step-num {{ font-size: 1.6rem; line-height: 1; flex-shrink: 0; }}
                .step-title {{ color: #fff; font-size: 0.85rem; font-weight: 700; margin-bottom: 5px; }}
                .step-desc {{ color: #888; font-size: 0.78rem; line-height: 1.6; }}
                .accent {{ color: var(--accent); font-weight: 700; }}
                .tip-box {{ background: rgba(0,255,204,0.06); border-left: 3px solid var(--accent); border-radius: 8px; padding: 14px 16px; margin-top: 24px; text-align: left; font-size: 0.78rem; color: #888; }}
                .close-note {{ margin-top: 30px; padding: 14px; background: #111; border-radius: 10px; color: #555; font-size: 0.75rem; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="/logo.png" class="logo-img" alt="Logo">
                    <h1 class="title-text">HECOS SETUP</h1>
                </div>
                <div class="done-card">
                    <div class="done-icon">🎉</div>
                    <div class="done-title">INSTALLATION COMPLETE!</div>
                    <div class="done-sub">All components have been installed successfully. Hecos is ready to start.</div>
                </div>

                {res_html}

                <div class="card">
                    <h2 style="color:var(--accent); margin-top:0;">🚀 HOW TO START HECOS</h2>

                    <div class="step-card">
                        <span class="step-num">1️⃣</span>
                        <div>
                            <div class="step-title">Find the Hecos Tray Icon</div>
                            <div class="step-desc">
                                Look at the <strong style="color:#ccc;">bottom-right corner of your taskbar</strong>, near the system clock.
                                You may need to click the <strong style="color:#ccc;">▲ arrow</strong> to expand hidden icons.
                                The Hecos icon should already be visible — it was launched automatically during setup.
                            </div>
                        </div>
                    </div>

                    <div class="step-card">
                        <span class="step-num">2️⃣</span>
                        <div>
                            <div class="step-title">Right-click the icon → <span class="accent">▶ Start Core</span></div>
                            <div class="step-desc">
                                Right-click on the Hecos tray icon to open the control menu,
                                then click <span class="accent">▶ Start Core</span> to launch the Hecos AI engine.
                                A beep will confirm the engine is online.
                            </div>
                        </div>
                    </div>

                    <div class="step-card">
                        <span class="step-num">3️⃣</span>
                        <div>
                            <div class="step-title">Hecos will auto-start on every login</div>
                            <div class="step-desc">
                                The tray icon is registered to launch automatically every time you log into Windows.
                                You only need to manually start it this first time.
                            </div>
                        </div>
                    </div>

                    <div class="tip-box">
                        <span style="color:var(--accent); font-weight:700;">💡 TIP &nbsp;</span>
                        Double-click the tray icon anytime to open the Hecos Control Center.
                    </div>

                    <div class="close-note">
                        ✅ You can now close this window and the terminal. Hecos runs independently in the background.
                    </div>
                </div>
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
            --bg: #070707; --bg2: #111; --bg3: #181818;
            --accent: #00ffcc; --accent-dim: rgba(0, 255, 204, 0.2);
            --accent-rgb: 0, 255, 204;
            --text: #eee; --muted: #777; --border: rgba(255, 255, 255, 0.08);
        }
        """

    def get_main_styles(self):
        return """
        body { margin: 0; padding: 40px 20px; background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; display: flex; justify-content: center; }
        .container { max-width: 680px; width: 100%; }
        .header { text-align: center; margin-bottom: 40px; }
        .logo-img { height: 70px; margin-bottom: 10px; filter: drop-shadow(0 0 10px var(--accent-dim)); }
        .title-text { font-size: 1.6rem; font-weight: 800; letter-spacing: 2px; color: #fff; text-transform: uppercase; margin: 0; }
        .card { background: var(--bg2); border: 1px solid var(--border); border-radius: 20px; padding: 40px; position: relative; overflow: hidden; box-shadow: 0 30px 60px rgba(0,0,0,0.4); }
        .card::after { content:''; position:absolute; top:0; left:0; right:0; height:2px; background: linear-gradient(90deg, transparent, var(--accent), transparent); }
        h2 { font-size: 0.85rem; color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-top: 30px; letter-spacing: 1px; }
        .tip { font-size: 0.85rem; color: var(--muted); margin-bottom: 5px; }
        .tip-sub { font-size: 0.7rem; color: var(--accent); opacity: 0.6; font-style: italic; margin-top: 0; }
        .section { margin-bottom: 30px; }
        .hero { background: rgba(var(--accent-rgb), 0.05); padding: 30px; border-radius: 15px; border: 1px solid var(--accent-dim); margin: 40px 0; }
        .btn { background: var(--accent); color: #000; padding: 12px 20px; border-radius: 10px; font-weight: 700; cursor: pointer; border: none; font-size: 0.8rem; text-decoration: none; transition: 0.2s; }
        .btn:hover { background: #fff; transform: translateY(-2px); box-shadow: 0 5px 15px var(--accent-dim); }
        .btn-outline { background: transparent; border: 1px solid var(--accent); color: var(--accent); }
        .btn-secondary { background: #222; color: #888; border: 1px solid #333; }
        .btn-warn { background: #ffcc00; color: #000; }
        .btn-danger { background: #ff4444; color: #fff; }
        .console { background: #000; padding: 20px; border-radius: 10px; border: 1px solid var(--border); color: var(--accent); font-family: monospace; font-size: 0.8rem; max-height: 200px; overflow-y: auto; margin-bottom: 30px; }
        .emergency h2 { margin-bottom: 5px; color: #f44336; border-color: rgba(244, 67, 54, 0.2); }
        .diag-item { display: flex; flex-direction: column; gap: 8px; }
        .diag-tip { font-size: 0.65rem; color: var(--muted); min-height: 28px; line-height: 1.3; }
        .footer { text-align: center; margin-top: 40px; border-top: 1px solid var(--border); padding-top: 30px; }
        .footer-links { display: flex; justify-content: center; gap: 10px; margin-top: 10px; }
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
