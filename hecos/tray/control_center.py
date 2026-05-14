"""
hecos/tray/control_center.py
Hecos Control Center — Enterprise Dashboard (Ultra-Stable / No Font Icons)
"""

import sys
import os
import subprocess
import threading

def show_control_center(icon=None, item=None):
    global _proc
    with threading.Lock():
        if '_proc' in globals() and _proc and _proc.poll() is None:
            return
        env = os.environ.copy()
        globals()['_proc'] = subprocess.Popen(
            [sys.executable, "-m", "hecos.tray.control_center"],
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            env=env,
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
        )

if __name__ == "__main__":
    import flet as ft
    from hecos.tray.config import load_settings, save_settings, HECOS_PORT
    from hecos.tray.network_utils import is_hecos_online, get_lan_ip, get_scheme, get_urls
    from hecos.tray.system_utils import get_version
    from hecos.tray.browser_manager import (
        _get_cdp_port, is_ai_ready_browser_running,
        intelligent_open_webui, launch_ai_ready_browser
    )

    # ── Constants (Explicit Hex) ──────────────────────────────────
    ACCENT  = "#00b4d8" # Hecos Cyan
    ACCENT2 = "#0077b6" # Hecos Blue
    BG      = "#111318"
    SURFACE = "#1a1d24"
    CARD    = "#22262f"
    TEXT    = "#e2e8f0"
    MUTED   = "#64748b"
    BORDER  = "#2d3240"
    RED     = "#ef4444"

    # ── Helpers ──────────────────────────────────────────────────
    def _title(text):
        return ft.Text(text, size=18, weight="bold", color=TEXT)

    def _subtitle(text):
        return ft.Text(text, size=11, color=MUTED)

    def _section_label(text):
        return ft.Text(text, size=10, color=MUTED, weight="bold")

    def _info_row(label, value, value_color=TEXT):
        return ft.Container(
            content=ft.Row([
                ft.Text(label, size=11, color=MUTED, expand=1),
                ft.Text(value, size=11, weight="bold", color=value_color),
            ]),
            padding=ft.Padding(16, 9, 16, 9),
        )

    def _card(*controls):
        return ft.Container(
            content=ft.Column(list(controls), spacing=0),
            bgcolor=CARD, border_radius=10,
            padding=ft.Padding(0, 4, 0, 4),
            margin=ft.Margin(0, 0, 0, 8),
        )

    # BUGFIX: Strict avoidance of 'ink=True' or native flet buttons to prevent gray overlays
    def _safe_btn(label, bgcolor, textcolor, on_click):
        return ft.Container(
            content=ft.Text(label, size=11, color=textcolor, text_align="center", weight="bold"),
            bgcolor=bgcolor, border_radius=8,
            padding=ft.Padding(14, 8, 14, 8),
            on_click=on_click,
        )

    def _build_status(page, body_col):
        online = is_hecos_online()
        cdp_p  = _get_cdp_port()
        cdp_ok = is_ai_ready_browser_running(cdp_p)

        scheme = get_scheme()
        lan_ip = get_lan_ip()
        
        url_local = f"{scheme}://127.0.0.1:{HECOS_PORT}"
        url_lan   = f"{scheme}://{lan_ip}:{HECOS_PORT}"

        def refresh(e):
            body_col.controls.clear()
            body_col.controls.append(_build_status(page, body_col))
            page.update()
            
        def make_copy_row(label, val):
            def do_copy(e):
                page.set_clipboard(val)
                # Visual feedback placeholder if needed
            return ft.Container(
                content=ft.Row([
                    ft.Text(label, size=11, color=MUTED, expand=1),
                    ft.Text(val, size=11, weight="bold", color=TEXT),
                    ft.Container(
                        content=ft.Text("📋", size=13, color=MUTED),
                        on_click=do_copy,
                        padding=ft.Padding(10, 0, 5, 0),
                        tooltip=f"Copy {val}"
                    )
                ]),
                padding=ft.Padding(16, 9, 16, 9),
            )

        public_ip_val = ft.Text("Detecting...", size=11, weight="bold", color=MUTED)
        public_ip_row = ft.Container(
            content=ft.Row([
                ft.Text("Remote Access", size=11, color=MUTED, expand=1),
                public_ip_val,
            ]), padding=ft.Padding(16, 9, 16, 9)
        )

        def fetch_pub_ip():
            import urllib.request
            try:
                ip = urllib.request.urlopen("https://api.ipify.org", timeout=4).read().decode("utf-8")
                remote_url = f"{scheme}://{ip}:{HECOS_PORT}"
                public_ip_val.value = remote_url
                public_ip_val.color = TEXT
                # Inject copy button
                def do_copy(e): page.set_clipboard(remote_url)
                public_ip_row.content.controls.append(
                    ft.Container(
                        content=ft.Text("📋", size=13, color=MUTED),
                        on_click=do_copy,
                        padding=ft.Padding(10, 0, 5, 0),
                        tooltip=f"Copy {remote_url}"
                    )
                )
            except Exception:
                public_ip_val.value = "Unreachable"
                public_ip_val.color = RED
            try:
                page.update()
            except: pass

        threading.Thread(target=fetch_pub_ip, daemon=True).start()

        network_section = ft.Column([
            _section_label("NETWORK INTERFACES"),
            _card(
                make_copy_row("Localhost", url_local),
                make_copy_row("LAN Host", url_lan),
                public_ip_row,
            ),
        ], visible=False)

        def toggle_network(e):
            network_section.visible = not network_section.visible
            toggle_btn.content.controls[0].value = "▽ Hide Technical Details" if network_section.visible else "▷ Show Technical Details"
            page.update()

        toggle_btn = ft.Container(
            content=ft.Row([
                ft.Text("▷ Show Technical Details", size=11, color=ACCENT, weight="bold"),
            ]),
            on_click=toggle_network,
            padding=ft.Padding(12, 5, 12, 5),
            border_radius=6,
        )

        return ft.Column([
            _title("System Status"),
            ft.Container(height=10),
            _section_label("CORE"),
            _card(
                _info_row("Status",   "🟢 Online"  if online else "🔴 Offline", ACCENT if online else RED),
                _info_row("Protocol", scheme.upper()),
                _info_row("Port",     str(HECOS_PORT)),
            ),
            toggle_btn,
            network_section,
            _section_label("BROWSER"),
            _card(
                _info_row("CDP Port",         str(cdp_p)),
                _info_row("AI-Ready Browser", "🟢 Active" if cdp_ok else "⚫ Not Detected", ACCENT if cdp_ok else MUTED),
            ),
            ft.Container(height=8),
            _safe_btn("↻ Refresh", SURFACE, TEXT, refresh),
        ], spacing=6, expand=1, scroll="auto")

    def _build_settings(page, body_col):
        cfg = load_settings()
        toggles = [
            ("start_hecos_on_launch",    "Start Core with Tray",         True),
            ("autoopen_webui",            "Auto-open WebUI on Startup",    True),
            ("autoopen_ai_browser",       "Auto-open Playwright Browser",  False),
            ("auto_launch_chrome_for_ai", "Auto-launch AI-Ready Chrome",   False),
            ("show_technical_menu",       "Show Technical Menu in Tray",   True),
        ]

        def _make_row(key, label, default):
            def on_change(e):
                s = load_settings(); s[key] = e.control.value; save_settings(s)

            return ft.Container(
                content=ft.Row([
                    ft.Text(label, size=12, color=TEXT, expand=1),
                    ft.Switch(value=cfg.get(key, default), active_color=ACCENT, on_change=on_change),
                ]),
                bgcolor=CARD, border_radius=10,
                padding=ft.Padding(16, 4, 16, 4),
                margin=ft.Margin(0, 0, 0, 6),
            )

        return ft.Column([
            _title("Settings"),
            _subtitle("Changes apply immediately."),
            ft.Container(height=10),
            *[_make_row(k, lbl, d) for k, lbl, d in toggles],
        ], spacing=0, expand=1)

    def _build_browser(page, body_col):
        def row(title, sub, btn_label, bgcolor, action):
            return ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Text(title, size=12, weight="bold", color=TEXT),
                        ft.Text(sub, size=10, color=MUTED),
                    ], expand=1, spacing=2),
                    _safe_btn(btn_label, bgcolor, "#ffffff", lambda e, a=action: threading.Thread(target=a, daemon=True).start()),
                ], vertical_alignment="center"),
                bgcolor=CARD, border_radius=10,
                padding=ft.Padding(16, 14, 16, 14),
                margin=ft.Margin(0, 0, 0, 6),
            )

        return ft.Column([
            _title("Browser Control"),
            _subtitle("Manage browser sessions."),
            ft.Container(height=10),
            row("Open Hecos Chat",      "Launch or refresh the main WebUI.",         "Open",   ACCENT2, lambda: intelligent_open_webui(None, None)),
            row("Open AI-Ready Chrome", "Chrome with CDP remote debugging enabled.", "Launch", ACCENT2, lambda: launch_ai_ready_browser(_get_cdp_port())),
            row("Open Config Hub",      "Open the Central Configuration Hub.",       "Open",   ACCENT2, lambda: __import__('webbrowser').open(get_urls()[1])),
        ], spacing=0, expand=1)

    def _build_mobile(page, body_col):
        url = f"{get_scheme()}://{get_lan_ip()}:{HECOS_PORT}/chat"
        qr_ctrl = ft.Text("Generating QR…", color=MUTED)
        try:
            import qrcode
            qr = qrcode.QRCode(box_size=1, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            matrix = qr.get_matrix()
            
            rows = []
            block_size = 5
            for row in matrix:
                flet_row = []
                for cell in row:
                    flet_row.append(
                        ft.Container(
                            width=block_size, 
                            height=block_size, 
                            bgcolor=ACCENT if cell else CARD
                        )
                    )
                rows.append(ft.Row(flet_row, spacing=0))
                
            qr_ctrl = ft.Container(
                content=ft.Column(rows, spacing=0),
                bgcolor=CARD,
                border_radius=8,
                padding=10
            )
        except Exception as ex:
            qr_ctrl = ft.Text(f"QR error: {ex}", color=RED, size=11)

        return ft.Column([
            _title("Mobile Access"),
            _subtitle("Scan to open Hecos on your phone."),
            ft.Container(height=14),
            ft.Container(
                content=ft.Column([
                    qr_ctrl,
                    ft.Text(url, size=11, color=MUTED, text_align="center"),
                ], horizontal_alignment="center"),
                bgcolor=CARD, border_radius=14, padding=24,
            ),
        ], spacing=6, horizontal_alignment="center", expand=1)

    def _build_about(page, body_col):
        return ft.Column([
            _title("About Hecos"),
            ft.Container(height=10),
            ft.Container(
                content=ft.Column([
                    ft.Container(height=12),
                    ft.Text("HECOS", size=32, weight="bold", color=ACCENT, text_align="center"),
                    ft.Text("Helping Companion System", size=13, color=MUTED, text_align="center"),
                    ft.Container(height=12),
                    _info_row("Version",  get_version()),
                    _info_row("Creator",  "Antonio Meloni"),
                    _info_row("Port",     str(HECOS_PORT)),
                    ft.Container(height=12),
                ], spacing=4, horizontal_alignment="center"),
                bgcolor=CARD, border_radius=14, padding=20, expand=1,
            ),
        ], spacing=6, expand=1)

    # ── Master Layout ──────────────────────────────────────────────
    def _build_ui_master(page: ft.Page):
        page.title = "Hecos Control Center"
        page.bgcolor = BG
        page.theme_mode = "dark"
        page.padding = 0
        try:
            page.window.icon = "Hecos_Logo_SQR_NBG_LogoOnly.ico"
        except:
            try:
                page.window_icon = "Hecos_Logo_SQR_NBG_LogoOnly.ico"
            except:
                pass
        
        try:
            page.window.width = 760
            page.window.height = 560
        except:
            page.window_width = 760
            page.window_height = 560

        nav_refs = {}
        body_col = ft.Column(expand=1, scroll="auto")

        # Replaced ALL Font Icons with extremely standard Unicode equivalents
        nav_items = [
            ("status",   "◉", "Status"),
            ("settings", "⚙", "Settings"),
            ("browser",  "🌐", "Browser"),
            ("mobile",   "📱", "Mobile QR"),
            ("about",    "ℹ", "About"),
        ]

        def _highlight(active):
            for k, c in nav_refs.items():
                c.bgcolor = ACCENT2 if k == active else SURFACE
                for ctrl in c.content.controls:
                    ctrl.color = "#ffffff" if k == active else TEXT
            page.update()

        def _show_tab(key):
            _highlight(key)
            body_col.controls.clear()
            builders = {
                "status":   _build_status,
                "settings": _build_settings,
                "browser":  _build_browser,
                "mobile":   _build_mobile,
                "about":    _build_about,
            }
            if key in builders:
                body_col.controls.append(builders[key](page, body_col))
            page.update()

        def _make_nav_btn(key, icon_str, label):
            c = ft.Container(
                content=ft.Row([
                    ft.Text(icon_str, size=15, color=TEXT), # Text instead of ft.Icon
                    ft.Text(label, size=12, color=TEXT),
                ], spacing=8),
                border_radius=8,
                padding=ft.Padding(12, 9, 12, 9),
                on_click=lambda e, k=key: _show_tab(k),
                bgcolor=SURFACE
            )
            nav_refs[key] = c
            return c

        def _do_restart():
            from hecos.tray.orchestrator import restart_hecos
            from hecos.tray.system_utils import play_beep
            play_beep(400, 100)
            threading.Thread(target=restart_hecos, daemon=True).start()

        # Build Sidebar
        sidebar_controls = [
            ft.Container(
                content=ft.Column([
                    ft.Text("HECOS", size=22, weight="bold", color=ACCENT),
                    ft.Text(f"v{get_version()}", size=10, color=MUTED),
                ], spacing=2),
                padding=ft.Padding(12, 0, 0, 12)
            ),
            ft.Container(height=6),
        ]
        
        for k, ic, lbl in nav_items:
            sidebar_controls.append(_make_nav_btn(k, ic, lbl))
            
        sidebar_controls.extend([
            ft.Container(expand=1),
            ft.Container(height=8),
            _safe_btn("Open Chat", ACCENT, "#000000", lambda e: threading.Thread(target=intelligent_open_webui, args=(None, None), daemon=True).start()),
            ft.Container(height=6),
            _safe_btn("Restart Core", CARD, TEXT, lambda e: _do_restart()),
        ])

        sidebar = ft.Container(
            width=185, 
            bgcolor=SURFACE,
            padding=ft.Padding(8, 20, 8, 20),
            content=ft.Column(sidebar_controls, spacing=3, expand=1)
        )

        # Assemble Root Node
        root_container = ft.Container(
            content=ft.Row([
                sidebar,
                # Explicit vertical border
                ft.Container(width=1, bgcolor=BORDER),
                ft.Container(content=body_col, expand=1, padding=20),
            ], spacing=0, expand=1),
            expand=1,
            bgcolor=BG
        )

        page.add(root_container)
        _show_tab("status")

    assets_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))
    
    # ── Single Instance Lock ──
    try:
        import socket
        __lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        __lock_socket.bind(("127.0.0.1", 54321))
    except socket.error:
        print("[Control Center] Process is already active. Ignoring launch request.")
        sys.exit(0)
    
    ft.app(target=_build_ui_master, assets_dir=assets_path)
