# hecos/setup/web_ui/templates.py
# TemplateMixin: all HTML page renderers.
# Inherits StyleMixin so render methods can call self.get_css_vars() / self.get_main_styles().
# Also uses self.send_html() which is defined on SetupHTTPRequestHandler in server.py.

import os
import sys
import re
import subprocess
import importlib

from .. import i18n
from ..i18n import T
from ..utils import (
    CWD, SYSTEM_CONFIG_PATH, LOGO_PATH,
    TRAY_DIR, TRAY_DIR_VERSIONED, TRAY_DIR_CANONICAL,
)
from ..engine import fetch_piper_voices
from .state import LAST_RESULTS, SETUP_LANGS
from .styles import StyleMixin


class TemplateMixin(StyleMixin):

    # ── Helpers ────────────────────────────────────────────────────────────────

    def send_html(self, html: str) -> None:
        """Send an HTML response. Defined here as a fallback; overridden by the server."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        try:
            self.wfile.write(html.encode('utf-8'))
        except (ConnectionAbortedError, ConnectionResetError):
            pass

    def _render_tray_banner(self) -> str:
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

    def _render_core_banner(self) -> str:
        """Returns an HTML banner if the Hecos core folder is named incorrectly (e.g. Hecos-main)."""
        basename = os.path.basename(CWD)
        if basename.lower() != "hecos":
            return f"""
            <div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.35);
                        border-radius:10px; padding:16px 20px; margin-bottom:24px; display:flex; gap:14px; align-items:flex-start;">
                <span style="font-size:1.1rem; flex-shrink:0;">⚠️</span>
                <div>
                    <div style="font-size:0.8rem; font-weight:700; color:#ef4444; margin-bottom:4px;">Core Folder Name is Incorrect</div>
                    <div style="font-size:0.77rem; color:#9ca3af; line-height:1.6;">
                        Current path: <code style="color:#d1d5db;">{CWD}</code><br>
                        The core folder must be named exactly <strong style="color:#d1d5db;">Hecos</strong> (e.g. <code style="color:#d1d5db;">C:\\Hecos</code>).<br>
                        Please rename it now, otherwise setup and launch scripts will fail!
                    </div>
                </div>
            </div>"""
        return ""

    # ── Diagnostics helpers ────────────────────────────────────────────────────


    @staticmethod
    def _diag_python():
        """Detect Python across all possible environments (system, venv, conda, pyenv…)."""
        import shutil
        candidates = []
        candidates.append(("Current interpreter", sys.executable, sys.version))

        if sys.platform == "win32":
            py = shutil.which("py")
            if py:
                try:
                    out = subprocess.check_output([py, "--version"], stderr=subprocess.STDOUT, timeout=5).decode().strip()
                    candidates.append(("Windows py launcher", py, out))
                except Exception:
                    pass

        for name in ("python3", "python"):
            p = shutil.which(name)
            if p and p != sys.executable:
                try:
                    out = subprocess.check_output([p, "--version"], stderr=subprocess.STDOUT, timeout=5).decode().strip()
                    candidates.append((f"PATH ({name})", p, out))
                except Exception:
                    pass

        conda = shutil.which("conda")
        if conda:
            try:
                out = subprocess.check_output(
                    [conda, "run", "python", "--version"],
                    stderr=subprocess.STDOUT, timeout=5
                ).decode().strip()
                candidates.append(("Conda environment", conda, out))
            except Exception:
                pass

        best = candidates[0] if candidates else None
        return best, candidates

    @staticmethod
    def _diag_hecos_version():
        """Return the installed Hecos Core version string, or None if not found."""
        ver_path = os.path.join(CWD, "hecos", "core", "version")
        if os.path.exists(ver_path):
            try:
                v = open(ver_path).read().strip()
                return v if v else "Unknown"
            except Exception:
                pass
        return None

    @staticmethod
    def _diag_key_packages():
        """Check a set of key pip packages and return their install status + version."""
        pkgs = {
            "pydantic": "pydantic",
            "pyyaml": "yaml",
            "litellm": "litellm",
            "pystray": "pystray",
            "customtkinter": "customtkinter",
            "psutil": "psutil",
            "PIL": "PIL",
        }
        results = {}
        for label, mod in pkgs.items():
            try:
                m = importlib.import_module(mod)
                ver = getattr(m, "__version__", "✓")
                results[label] = ("ok", ver)
            except ImportError:
                results[label] = ("missing", None)
        return results

    def _build_diag_html(self):
        """Run all diagnostics and return the rendered HTML fragment."""
        best_python, _ = self._diag_python()
        hecos_ver = self._diag_hecos_version()
        key_pkgs = self._diag_key_packages()

        py_icon = "✓" if best_python else "✗"
        py_color = "var(--accent)" if best_python else "var(--red-muted)"
        if best_python:
            ver_part = best_python[2].split()[1] if len(best_python[2].split()) > 1 else best_python[2]
            py_label = f"{ver_part} <span style='color:var(--muted); font-weight:400;'>({best_python[0]})</span>"
        else:
            py_label = "Not found"

        core_icon = "✓" if hecos_ver else "✗"
        core_color = "var(--accent)" if hecos_ver else "var(--muted)"
        core_label = f"v{hecos_ver}" if hecos_ver else "Not detected in C:\\Hecos"

        all_ok = all(s == "ok" for s, _ in key_pkgs.values())
        pkg_rows = ""
        for label, (status, ver) in key_pkgs.items():
            color = "var(--accent)" if status == "ok" else "var(--red-muted)"
            icon = "✓" if status == "ok" else "✗"
            ver_str = f"<span style='color:var(--muted); font-size:0.7rem;'>({ver})</span>" if ver and ver != "✓" else ""
            pkg_rows += f"<div class='diag-pkg'><span style='color:{color};'>{icon}</span> {label} {ver_str}</div>"

        deps_color = "var(--accent)" if all_ok else "var(--red-muted)"
        deps_icon = "✓" if all_ok else "⚠"
        deps_summary = "All key packages installed" if all_ok else "Some packages missing — run Install"

        return f"""
        <div class="card">
            <div class="section-label" style="margin-bottom:16px;">SYSTEM DIAGNOSTICS</div>
            <div style="display:flex; flex-direction:column; gap:0;">
                <div class="diag-item">
                    <span class="diag-icon" style="color:{py_color};">{py_icon}</span>
                    <div>
                        <div class="diag-title">Python</div>
                        <div class="diag-sub">{py_label}</div>
                    </div>
                </div>
                <div class="diag-item">
                    <span class="diag-icon" style="color:{core_color};">{core_icon}</span>
                    <div>
                        <div class="diag-title">Hecos Core</div>
                        <div class="diag-sub">{core_label}</div>
                    </div>
                </div>
                <div class="diag-item">
                    <span class="diag-icon" style="color:{deps_color};">{deps_icon}</span>
                    <div>
                        <div class="diag-title">Python Packages</div>
                        <div class="diag-sub">{deps_summary}</div>
                        <div class="diag-pkgs">{pkg_rows}</div>
                    </div>
                </div>
            </div>
        </div>"""

    # ── Page renderers ─────────────────────────────────────────────────────────

    def render_splash(self):
        lang_options = "".join([
            f'<option value="{k}" {"selected" if k == i18n.UI_LANG else ""}>{v}</option>'
            for k, v in SETUP_LANGS.items()
        ])
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
        # ── Diagnostics ────────────────────────────────────────────────────────
        diag_html = self._build_diag_html()

        # ── Current system language ────────────────────────────────────────────
        sys_lang = "en"
        if os.path.exists(SYSTEM_CONFIG_PATH):
            with open(SYSTEM_CONFIG_PATH, 'r', encoding='utf-8') as f:
                m = re.search(r'language:\s*(.*)', f.read())
                if m:
                    sys_lang = m.group(1).strip().lower()

        # ── Voice list ─────────────────────────────────────────────────────────
        voices = fetch_piper_voices()
        grouped = {}
        for k, v in voices.items():
            lang_name = v.get("language", {}).get("name_english", "Other")
            if lang_name not in grouped:
                grouped[lang_name] = []
            grouped[lang_name].append((k, v.get("name", "Unknown"), v.get("quality", "")))

        v_options = '<div class="voice-list">'
        if voices:
            v_options = f"""
            <input type="text" onkeyup="filterVoices(this.value)" placeholder="Search language or voice..." 
                   style="width:100%; padding:9px 12px; border-radius:6px; border:1px solid var(--border); 
                          background:var(--bg3); color:var(--text); margin-bottom:8px; font-family:inherit; font-size:0.8rem;">
            <script>
            function filterVoices(query) {{
                query = query.toLowerCase();
                document.querySelectorAll('.voice-row').forEach(r => {{
                    if(r.textContent.toLowerCase().includes(query)) r.style.display = 'flex';
                    else r.style.display = 'none';
                }});
            }}
            </script>
            <div class="voice-list">
            """
            for lang_name in sorted(grouped.keys()):
                v_options += f'<div class="voice-lang-label">{lang_name}</div>'
                for vk, vn, vq in sorted(grouped[lang_name], key=lambda x: x[1]):
                    v_options += f"""
                    <label class="voice-row">
                        <input type="checkbox" name="voices" value="{vk}" class="voice-check">
                        <span class="voice-name">{vn}</span><span class="voice-quality">{vq}</span>
                    </label>
                    """
        else:
            v_options += '<div class="error-msg">Could not fetch voice list (offline or timeout).<br><br><button type="button" class="btn-ghost" onclick="window.location.reload()">↺ Retry</button></div>'
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

                {res_html}
                {self._render_core_banner()}
                {self._render_tray_banner()}

                <!-- 01 LANGUAGE -->
                <div class="card">
                    <div class="section">
                        <div class="section-label">01 — {T('step_lang').upper()}</div>
                        <p class="tip">{T('tip_lang')}</p>
                        <p class="tip-sub">{T('tip_lang_multilingual')}</p>
                        <form action="/set_lang" method="POST" style="display:flex; gap:8px; margin-top:14px;">
                            <button name="lang" value="en" class="btn-lang {'btn-lang-active' if sys_lang == 'en' else ''}">English</button>
                            <button name="lang" value="it" class="btn-lang {'btn-lang-active' if sys_lang == 'it' else ''}">Italiano</button>
                        </form>
                    </div>
                </div>

                <!-- 02 INSTALL -->
                <div class="card">
                    <div class="section-label" style="margin-bottom:8px;">02 — INSTALL</div>
                    <p class="tip" style="margin-bottom:20px;">Installs all dependencies (Piper TTS engine, Python packages) and configures Hecos autostart.</p>
                    <form action="/onboarding" method="POST">
                        <div class="section" style="margin-bottom:16px;">
                            <div class="section-label">{T('step_voice').upper()} — OPTIONAL</div>
                            <p class="tip">{T('tip_voice')}</p>
                            {v_options}
                        </div>
                        <button id="launch-btn" class="btn-primary"
                            onclick="
                                setTimeout(() => this.disabled=true, 10);
                                this.textContent='Installing... Downloading AI Engine (100MB+). Please wait 1-2 minutes! DO NOT CLOSE!';
                                document.getElementById('next-steps').style.display='block';
                            ">▶ Start Installation</button>
                        <div id="next-steps" style="display:none; margin-top:24px; border-top:1px solid var(--border); padding-top:20px;">
                            <div class="next-label">What to do while you wait</div>
                            {
                            f'''
                            <div class="step-item">
                                <span class="step-num">1</span>
                                <div>
                                    <div class="step-title">Find the Hecos Tray Icon</div>
                                    <div class="step-desc">Look in the <strong>bottom-right corner of your taskbar</strong>. Click <strong>▲</strong> to expand hidden icons.</div>
                                </div>
                            </div>
                            <div class="step-item">
                                <span class="step-num">2</span>
                                <div>
                                    <div class="step-title">Right-click → <span style="color:var(--accent);">Start Core</span></div>
                                    <div class="step-desc">After setup completes, right-click the tray icon and click <strong>▶ Start Core</strong>.</div>
                                </div>
                            </div>
                            ''' if TRAY_DIR else '''
                            <div class="step-item">
                                <span class="step-num">1</span>
                                <div>
                                    <div class="step-title">Run Global Launcher</div>
                                    <div class="step-desc">Open the <strong>C:\\Hecos</strong> folder and double-click <strong>HECOS_GLOBAL_LAUNCHER</strong>.</div>
                                </div>
                            </div>
                            <div class="step-item">
                                <span class="step-num">2</span>
                                <div>
                                    <div class="step-title">Press 4 to Start WebUI</div>
                                    <div class="step-desc">After setup completes, press 4 to launch the Web Interface.</div>
                                </div>
                            </div>
                            '''
                            }
                        </div>
                    </form>
                </div>

                <!-- 03 UNINSTALL -->
                <div class="card" style="border-color: rgba(239,68,68,0.2);">
                    <div class="section-label" style="color:var(--red-muted); margin-bottom:8px;">03 — UNINSTALL</div>
                    <p class="tip" style="margin-bottom:20px;">Choose how to remove Hecos from your system. The Hecos folders will need to be deleted manually afterwards.</p>

                    <div style="display:flex; flex-direction:column; gap:12px;">

                        <!-- Option A: Smart uninstall -->
                        <div style="background:rgba(239,68,68,0.04); border:1px solid rgba(239,68,68,0.15); border-radius:10px; padding:20px;">
                            <div style="display:flex; align-items:flex-start; gap:14px;">
                                <span style="font-size:1.3rem; flex-shrink:0; margin-top:2px;">🧹</span>
                                <div style="flex:1;">
                                    <div style="font-size:0.82rem; font-weight:700; color:var(--text); margin-bottom:4px;">Remove Hecos Only</div>
                                    <div style="font-size:0.75rem; color:var(--muted); line-height:1.6; margin-bottom:14px;">
                                        Removes only the packages that Hecos installed. <strong style="color:var(--text);">Safe if you use Python for other projects</strong> — your other libraries will not be touched.
                                    </div>
                                    <form id="smart-uninstall-form" action="/uninstall_hecos" method="POST">
                                        <button type="button" class="btn-ghost btn-danger-ghost"
                                            onclick="document.getElementById('smart-modal').classList.add('active');"
                                            style="font-size:0.78rem;">
                                            🧹 Remove Hecos Only
                                        </button>
                                    </form>
                                </div>
                            </div>
                        </div>

                        <!-- Option B: Full wipe -->
                        <div style="background:rgba(239,68,68,0.06); border:1px solid rgba(239,68,68,0.25); border-radius:10px; padding:20px;">
                            <div style="display:flex; align-items:flex-start; gap:14px;">
                                <span style="font-size:1.3rem; flex-shrink:0; margin-top:2px;">🗑</span>
                                <div style="flex:1;">
                                    <div style="font-size:0.82rem; font-weight:700; color:var(--red-muted); margin-bottom:4px;">Full Environment Wipe</div>
                                    <div style="font-size:0.75rem; color:var(--muted); line-height:1.6; margin-bottom:14px;">
                                        Removes <strong style="color:var(--red-muted);">every package</strong> from the Python environment — not just Hecos. <strong style="color:var(--text);">Only use this if Python is dedicated to Hecos</strong> and you want to start with a completely clean slate.
                                    </div>
                                    <form id="wipe-form" action="/uninstall" method="POST">
                                        <button type="button" class="btn-ghost btn-danger-ghost"
                                            onclick="document.getElementById('wipe-modal').classList.add('active');"
                                            style="font-size:0.78rem; border-color:rgba(239,68,68,0.6);">
                                            🗑 Full Environment Wipe
                                        </button>
                                    </form>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>

                <!-- 04 DIAGNOSTICS -->
                {diag_html}

                <div class="footer">
                    <a href="/toggle_ui_lang" class="btn-ghost" style="font-size:0.7rem;">UI: {i18n.UI_LANG.upper()}</a>
                    <a href="/clear" class="btn-ghost" style="font-size:0.7rem;">Clear Logs</a>
                </div>
            </div>

            <!-- Modal: Smart uninstall -->
            <div id="smart-modal" class="modal-overlay">
                <div class="modal-box">
                    <div class="modal-icon">🧹</div>
                    <div class="modal-title" style="color:var(--text);">REMOVE HECOS ONLY?</div>
                    <div class="modal-desc">
                        This will uninstall <strong>only the packages listed in Hecos' pyproject.toml</strong>.<br><br>
                        Your other Python libraries will <strong>not be affected</strong>. Autostart will also be disabled.
                    </div>
                    <div class="modal-actions">
                        <button type="button" class="btn-ghost" onclick="document.getElementById('smart-modal').classList.remove('active');" style="border-color:var(--border);">Cancel</button>
                        <button type="button" class="btn-solid-danger" style="background:#6b7280;" onclick="
                            this.textContent='Removing... Check terminal (wait 30-60s)';
                            this.disabled=true;
                            document.getElementById('smart-uninstall-form').submit();
                        ">Yes, Remove Hecos Only</button>
                    </div>
                </div>
            </div>

            <!-- Modal: Full wipe -->
            <div id="wipe-modal" class="modal-overlay">
                <div class="modal-box">
                    <div class="modal-icon">⚠️</div>
                    <div class="modal-title">WIPE ENTIRE PYTHON ENVIRONMENT?</div>
                    <div class="modal-desc">
                        This will remove <strong>ALL packages</strong> from your Python environment — not just Hecos.<br><br>
                        <strong style="color:var(--red-muted);">Only proceed if this Python installation is dedicated to Hecos</strong> and you don't use it for anything else.
                    </div>
                    <div class="modal-actions">
                        <button type="button" class="btn-ghost" onclick="document.getElementById('wipe-modal').classList.remove('active');" style="border-color:var(--border);">Cancel</button>
                        <button type="button" class="btn-solid-danger" onclick="
                            this.textContent='Wiping... Check terminal (wait 1-2m)';
                            this.disabled=true;
                            document.getElementById('wipe-form').submit();
                        ">Yes, Full Wipe</button>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        self.send_html(html)

    def render_smart_uninstall_done(self):
        res_html = f'<div class="console" style="max-height:300px;">{("<br>").join(LAST_RESULTS)}</div>' if LAST_RESULTS else ""
        html = f"""
        <!DOCTYPE html>
        <html lang="{i18n.UI_LANG}">
        <head>
            <meta charset="UTF-8">
            <title>Hecos — Removed</title>
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>{self.get_css_vars()}{self.get_main_styles()}</style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="/logo.png" class="logo-img" alt="Logo">
                    <h1 class="title-text" style="color:var(--muted);">HECOS UNINSTALLER</h1>
                </div>
                <div class="done-banner" style="border-color:rgba(107,114,128,0.4); background:rgba(107,114,128,0.05);">
                    <div class="done-label" style="color:var(--text);">🧹 Hecos Removed</div>
                    <div class="done-sub">All Hecos packages have been uninstalled. Your other Python libraries were not affected.</div>
                </div>
                {res_html}
                <div class="close-note">✓ You can safely close this window. You may also delete the Hecos folder from your computer.</div>
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

                    {
                    f'''
                    <div class="next-label" style="margin-top:10px; color:var(--text);">Via Hecos Tray Icon (Recommended):</div>
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
                    <div class="step-item" style="border-bottom:none;">
                        <span class="step-num">3</span>
                        <div>
                            <div class="step-title">Auto-start is enabled</div>
                            <div class="step-desc">The tray launches automatically on every login — no action needed next time.</div>
                        </div>
                    </div>
                    ''' if TRAY_DIR else '''
                    <div class="next-label" style="margin-top:10px; color:var(--text);">Via Hecos Core Standalone:</div>
                    <div class="step-item">
                        <span class="step-num" style="border-color:var(--text); color:var(--text);">★</span>
                        <div>
                            <div class="step-title">Use the Global Launcher</div>
                            <div class="step-desc">Open the <strong>C:\\Hecos</strong> folder and double-click <strong>HECOS_GLOBAL_LAUNCHER</strong> to access all startup options (including WebUI).</div>
                        </div>
                    </div>
                    '''
                    }

                    <div class="close-note">
                        <strong style="color:var(--text); font-size:0.85rem;">✓ You can now close this window and the setup terminal.</strong><br>
                        Hecos is ready to be launched.
                    </div>
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
