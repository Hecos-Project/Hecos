"""
hecos/tray/control_center.py
Hecos Tray Dashboard — CustomTkinter Edition (replaces Flet)
Ultra-light: opens in < 400ms, no Flutter/Dart runtime required.
"""

import sys
import os
import subprocess
import threading


def show_control_center(icon=None, item=None):
    """Launch the dashboard in a separate subprocess (non-blocking)."""
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


# ── Dashboard App (runs when launched as subprocess) ───────────────────────────

if __name__ == "__main__":
    import os
    import sys
    import tkinter as tk

    # ── Single Instance Lock ───────────────────────────────────────────────────
    import socket as _sock
    try:
        __lock_socket = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
        __lock_socket.bind(("127.0.0.1", 54321))
    except _sock.error:
        print("[Tray Dashboard] Already running.")
        sys.exit(0)

    # ── Native Splash Screen (Isolated Process) ────────────────────────────────
    import subprocess
    logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "Hecos_Logo_SQR_NBG_LogoOnly.png"))
    
    splash_code = f"""
import tkinter as tk
splash = tk.Tk()
splash.overrideredirect(True)
splash.configure(bg='#111318')
sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
splash.geometry(f'280x280+{{(sw-280)//2}}+{{(sh-280)//2}}')
try:
    img = tk.PhotoImage(file=r'{logo_path}')
    img = img.subsample(max(1, img.width() // 150))
    lbl = tk.Label(splash, image=img, bg='#111318')
    lbl.image = img
    lbl.pack(expand=True, pady=(30, 0))
except Exception:
    pass
tk.Label(splash, text='Loading Hecos Dashboard...', fg='#00b4d8', bg='#111318', font=('Helvetica', 11, 'bold')).pack(pady=20)
splash.mainloop()
"""
    # Launch splash in a separate process to avoid tkinter dual-root freezing issues
    splash_proc = subprocess.Popen([sys.executable, "-c", splash_code], creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)

    # ── Heavy Imports ──────────────────────────────────────────────────────────
    import time
    import webbrowser
    import urllib.request
    import json as _json

    import customtkinter as ctk
    from hecos.tray.config import load_settings, save_settings, HECOS_PORT
    from hecos.tray.network_utils import is_hecos_online, get_lan_ip, get_scheme, get_urls
    from hecos.tray.system_utils import get_version
    from hecos.tray.browser_manager import (
        _get_cdp_port, is_ai_ready_browser_running,
        intelligent_open_webui, launch_ai_ready_browser
    )

    # ── Theme ──────────────────────────────────────────────────────────────────
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    # ── Color Palette ──────────────────────────────────────────────────────────
    BG      = "#111318"
    SURFACE = "#1a1d24"
    CARD    = "#22262f"
    ACCENT  = "#00b4d8"
    ACCENT2 = "#0077b6"
    TEXT    = "#e2e8f0"
    MUTED   = "#64748b"
    RED     = "#ef4444"
    GREEN   = "#22c55e"
    AMBER   = "#f59e0b"
    BORDER  = "#2d3240"

    # ── App Window ─────────────────────────────────────────────────────────────
    app = ctk.CTk()
    app.title("Hecos Tray Dashboard")
    app.geometry("780x540")
    app.minsize(680, 480)
    app.configure(fg_color=BG)
    app.resizable(True, True)

    # Icon and AppUserModelID for Taskbar
    try:
        import ctypes
        myappid = 'hecos.tray.dashboard'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    try:
        ico = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets",
                                           "Hecos_Logo_SQR_NBG_LogoOnly.ico"))
        if os.path.exists(ico):
            app.iconbitmap(ico)
    except Exception:
        pass

    # ── Layout: sidebar + content ───────────────────────────────────────────────
    sidebar = ctk.CTkFrame(app, width=190, fg_color=SURFACE, corner_radius=0)
    sidebar.pack(side="left", fill="y", padx=(0, 1))
    sidebar.pack_propagate(False)

    # Separator line
    sep = ctk.CTkFrame(app, width=1, fg_color=BORDER, corner_radius=0)
    sep.pack(side="left", fill="y")

    content_frame = ctk.CTkFrame(app, fg_color=BG, corner_radius=0)
    content_frame.pack(side="left", fill="both", expand=True)

    # ── Sidebar Header ─────────────────────────────────────────────────────────
    hdr = ctk.CTkFrame(sidebar, fg_color="transparent")
    hdr.pack(fill="x", padx=12, pady=(20, 8))
    ctk.CTkLabel(hdr, text="HECOS", font=ctk.CTkFont(size=22, weight="bold"),
                 text_color=ACCENT).pack(anchor="w")
    ctk.CTkLabel(hdr, text=f"v{get_version()}", font=ctk.CTkFont(size=10),
                 text_color=MUTED).pack(anchor="w")

    # ── Nav buttons ────────────────────────────────────────────────────────────
    NAV_ITEMS = [
        ("status",   "◉  Status"),
        ("settings", "⚙  Settings"),
        ("browser",  "🌐  Browser"),
        ("mobile",   "📱  Remote Access"),
        ("logs",     "📋  Live Logs"),
        ("about",    "ℹ  About"),
    ]

    _active_tab = {"key": None}
    _nav_btns = {}
    _content_widgets = []  # keep refs to destroy on tab switch

    def _clear_content():
        for w in _content_widgets:
            try:
                w.destroy()
            except Exception:
                pass
        _content_widgets.clear()

    def _highlight(active_key):
        for k, btn in _nav_btns.items():
            if k == active_key:
                btn.configure(fg_color=ACCENT2, text_color="#ffffff")
            else:
                btn.configure(fg_color="transparent", text_color=TEXT)

    def _rebuild_tab(key):
        """Force-rebuild the content of a tab, even if it is already the active tab.
        Used by the Refresh button so it works when already on the status tab."""
        _active_tab["key"] = key
        _highlight(key)
        _clear_content()
        TAB_BUILDERS[key]()

    def _switch_tab(key):
        if _active_tab["key"] == key:
            return  # already active — no visual change needed
        _rebuild_tab(key)

    nav_area = ctk.CTkScrollableFrame(sidebar, fg_color="transparent", corner_radius=0)
    nav_area.pack(fill="both", expand=True, padx=4)

    for _key, _label in NAV_ITEMS:
        _btn = ctk.CTkButton(
            nav_area, text=_label, anchor="w",
            fg_color="transparent", text_color=TEXT,
            hover_color=BORDER, corner_radius=8,
            font=ctk.CTkFont(size=12),
            command=lambda k=_key: _switch_tab(k)
        )
        _btn.pack(fill="x", pady=2, ipady=4)
        _nav_btns[_key] = _btn

    # ── Sidebar bottom buttons ─────────────────────────────────────────────────
    bottom = ctk.CTkFrame(sidebar, fg_color="transparent")
    bottom.pack(fill="x", padx=8, pady=(0, 12))

    def _open_chat():
        threading.Thread(target=lambda: intelligent_open_webui(None, None), daemon=True).start()

    def _restart_core():
        from hecos.tray.orchestrator import restart_hecos
        from hecos.tray.system_utils import play_beep
        play_beep(400, 100)
        threading.Thread(target=restart_hecos, daemon=True).start()

    ctk.CTkButton(bottom, text="Open Chat", fg_color=ACCENT, text_color="#000000",
                  hover_color=ACCENT2, corner_radius=8, font=ctk.CTkFont(size=11, weight="bold"),
                  command=_open_chat).pack(fill="x", pady=(0, 5))
    ctk.CTkButton(bottom, text="Restart Core", fg_color=RED, text_color="#ffffff",
                  hover_color="#b91c1c", corner_radius=8, font=ctk.CTkFont(size=11, weight="bold"),
                  command=_restart_core).pack(fill="x")

    # ─────────────────────────────────────────────────────────────────────────
    # Helper widgets
    # ─────────────────────────────────────────────────────────────────────────

    def _make_card(parent, **kw):
        f = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=10, **kw)
        return f

    def _title(parent, text):
        lbl = ctk.CTkLabel(parent, text=text,
                           font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT)
        lbl.pack(anchor="w", pady=(0, 2))
        _content_widgets.append(lbl)
        return lbl

    def _subtitle(parent, text):
        lbl = ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=11), text_color=MUTED)
        lbl.pack(anchor="w", pady=(0, 8))
        _content_widgets.append(lbl)
        return lbl

    def _section_label(parent, text):
        lbl = ctk.CTkLabel(parent, text=text,
                           font=ctk.CTkFont(size=10, weight="bold"), text_color=MUTED)
        lbl.pack(anchor="w", pady=(8, 2))
        _content_widgets.append(lbl)
        return lbl

    def _info_row(card, label, value, value_color=TEXT):
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=5)
        ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=11), text_color=MUTED,
                     anchor="w").pack(side="left", expand=True, fill="x")
        ctk.CTkLabel(row, text=value, font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=value_color, anchor="e").pack(side="right")
        return row

    # ─────────────────────────────────────────────────────────────────────────
    # TAB: STATUS
    # ─────────────────────────────────────────────────────────────────────────

    def _build_status():
        sc = ctk.CTkScrollableFrame(content_frame, fg_color="transparent", corner_radius=0)
        sc.pack(fill="both", expand=True, padx=20, pady=20)
        _content_widgets.append(sc)

        _title(sc, "System Status")

        online = is_hecos_online()
        cdp_p  = _get_cdp_port()
        cdp_ok = is_ai_ready_browser_running(cdp_p)

        _section_label(sc, "CORE")
        c1 = _make_card(sc)
        c1.pack(fill="x", pady=(0, 8))
        _info_row(c1, "Status",   "Online" if online else "Offline",
                  ACCENT if online else RED)
        _info_row(c1, "Protocol", get_scheme().upper())
        _info_row(c1, "Port",     str(HECOS_PORT))

        _section_label(sc, "BROWSER (CDP)")
        c2 = _make_card(sc)
        c2.pack(fill="x", pady=(0, 8))
        _info_row(c2, "Connection",
                  f"Port {cdp_p} Open" if cdp_ok else f"Port {cdp_p} Closed",
                  ACCENT if cdp_ok else RED)

        row_f = ctk.CTkFrame(c2, fg_color="transparent")
        row_f.pack(fill="x", padx=14, pady=5)
        ctk.CTkLabel(row_f, text="Active Engine", font=ctk.CTkFont(size=11),
                     text_color=MUTED, anchor="w").pack(side="left", expand=True, fill="x")
        browser_lbl = ctk.CTkLabel(row_f, text="Detecting…", font=ctk.CTkFont(size=11),
                                   text_color=MUTED)
        browser_lbl.pack(side="right")

        def _fetch_browser():
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{cdp_p}/json/version",
                                            timeout=1) as r:
                    data = _json.loads(r.read().decode())
                val = data.get("Browser", "")
                if not val:
                    val = "Unknown Engine"
                col = TEXT
            except Exception:
                val = "Active (Engine Unknown)" if cdp_ok else "Not Detected"
                col = ACCENT if cdp_ok else MUTED
            
            def _update_ui(v, c):
                try: browser_lbl.configure(text=v, text_color=c)
                except: pass
            
            app.after(0, _update_ui, val, col)

        if cdp_ok:
            threading.Thread(target=_fetch_browser, daemon=True).start()
        else:
            browser_lbl.configure(text="Not Detected", text_color=MUTED)

        def _refresh():
            # Use _rebuild_tab so the refresh always works even when
            # the status tab is already the active tab.
            _rebuild_tab("status")

        ctk.CTkButton(sc, text="↻ Refresh", fg_color=SURFACE, text_color=TEXT,
                      hover_color=BORDER, corner_radius=8,
                      command=_refresh).pack(anchor="w", pady=(8, 0))

    # ─────────────────────────────────────────────────────────────────────────
    # TAB: SETTINGS
    # ─────────────────────────────────────────────────────────────────────────

    def _build_settings():
        sc = ctk.CTkScrollableFrame(content_frame, fg_color="transparent", corner_radius=0)
        sc.pack(fill="both", expand=True, padx=20, pady=20)
        _content_widgets.append(sc)

        _title(sc, "Settings")
        _subtitle(sc, "Changes apply immediately.")

        toggles = [
            ("start_hecos_on_launch",    "Start Core with Tray",              True),
            ("autoopen_webui",            "Auto-open WebUI on Startup",        True),
            ("autoopen_ai_browser",       "Auto-open Playwright Browser",      False),
            ("auto_launch_chrome_for_ai", "Auto-launch AI-Ready Chrome (CDP)", False),
            ("show_technical_menu",       "Show Technical Menu in Tray",       True),
        ]

        cfg = load_settings()

        for key, label, default in toggles:
            row = ctk.CTkFrame(sc, fg_color=CARD, corner_radius=10)
            row.pack(fill="x", pady=4)

            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=12), text_color=TEXT,
                         anchor="w").pack(side="left", padx=14, pady=10, expand=True, fill="x")

            var = ctk.BooleanVar(value=cfg.get(key, default))

            def _on_toggle(v=var, k=key):
                s = load_settings()
                s[k] = v.get()
                save_settings(s)

            sw = ctk.CTkSwitch(row, text="", variable=var, onvalue=True, offvalue=False,
                               progress_color=ACCENT, command=_on_toggle)
            sw.pack(side="right", padx=14, pady=10)

    # ─────────────────────────────────────────────────────────────────────────
    # TAB: BROWSER
    # ─────────────────────────────────────────────────────────────────────────

    def _build_browser():
        sc = ctk.CTkScrollableFrame(content_frame, fg_color="transparent", corner_radius=0)
        sc.pack(fill="both", expand=True, padx=20, pady=20)
        _content_widgets.append(sc)

        _title(sc, "Browser Control")
        _subtitle(sc, "Manage browser sessions.")

        browser_actions = [
            ("Open Hecos Chat",
             "Launch or refresh the main WebUI.",
             lambda: intelligent_open_webui(None, None)),
            ("Open AI-Ready Chrome",
             "Chrome with CDP remote debugging enabled.",
             lambda: launch_ai_ready_browser(_get_cdp_port())),
            ("Open Config Hub",
             "Open the Central Configuration Hub.",
             lambda: webbrowser.open(get_urls()[1])),
        ]

        for title, sub, action in browser_actions:
            card = ctk.CTkFrame(sc, fg_color=CARD, corner_radius=10)
            card.pack(fill="x", pady=4)

            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True, padx=14, pady=10)
            ctk.CTkLabel(info, text=title, font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=TEXT, anchor="w").pack(anchor="w")
            ctk.CTkLabel(info, text=sub, font=ctk.CTkFont(size=10),
                         text_color=MUTED, anchor="w").pack(anchor="w")

            ctk.CTkButton(card, text="Open", fg_color=ACCENT2, text_color="#ffffff",
                          hover_color=ACCENT, corner_radius=8, width=70,
                          command=lambda a=action: threading.Thread(target=a, daemon=True).start()
                          ).pack(side="right", padx=14, pady=10)

    # ─────────────────────────────────────────────────────────────────────────
    # TAB: REMOTE ACCESS (Mobile)
    # ─────────────────────────────────────────────────────────────────────────

    def _build_mobile():
        sc = ctk.CTkScrollableFrame(content_frame, fg_color="transparent", corner_radius=0)
        sc.pack(fill="both", expand=True, padx=20, pady=20)
        _content_widgets.append(sc)

        _title(sc, "Remote Access")
        _subtitle(sc, "Scan the QR code or copy the link to access Hecos from other devices.")

        scheme = get_scheme()
        lan_ip = get_lan_ip()
        url_chat  = f"{scheme}://{lan_ip}:{HECOS_PORT}/chat"
        url_local = f"{scheme}://127.0.0.1:{HECOS_PORT}"
        url_lan   = f"{scheme}://{lan_ip}:{HECOS_PORT}"

        # QR Code
        try:
            import qrcode
            from PIL import Image as _PIL_Image, ImageTk
            qr = qrcode.QRCode(box_size=5, border=2)
            qr.add_data(url_chat)
            qr.make(fit=True)
            img = qr.make_image(fill_color=ACCENT, back_color=CARD)
            # Convert to CTkImage
            pil_img = img.convert("RGB")
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img,
                                   size=(min(200, pil_img.width), min(200, pil_img.height)))
            qr_card = ctk.CTkFrame(sc, fg_color=CARD, corner_radius=10)
            qr_card.pack(pady=(0, 10))
            ctk.CTkLabel(qr_card, image=ctk_img, text="").pack(padx=20, pady=20)
        except Exception as e:
            qr_card = ctk.CTkFrame(sc, fg_color=CARD, corner_radius=10)
            qr_card.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(qr_card, text=f"QR unavailable (pip install qrcode pillow)\n{e}",
                         font=ctk.CTkFont(size=10), text_color=MUTED).pack(padx=20, pady=20)

        # The URL copy rows
        def _url_row(parent, label, val):
            row = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=10)
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=11), text_color=MUTED,
                         anchor="w").pack(side="left", padx=14, pady=8, expand=True, fill="x")
            ctk.CTkLabel(row, text=val, font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=TEXT, anchor="e").pack(side="left", expand=True, fill="x")
            ctk.CTkButton(row, text="📋", width=32, fg_color="transparent", text_color=MUTED,
                          hover_color=BORDER, corner_radius=6,
                          command=lambda v=val: app.clipboard_clear() or app.clipboard_append(v)
                          ).pack(side="right", padx=8)

        # ── Toggle Button ──
        toggle_btn = ctk.CTkButton(sc, text="▷ Show Technical Details", fg_color="transparent",
                                   text_color=ACCENT, hover_color=BORDER, corner_radius=8,
                                   font=ctk.CTkFont(size=11, weight="bold"), anchor="w")
        toggle_btn.pack(fill="x", pady=(10, 0))

        # ── Network Section (Hidden by default) ──
        network_section = ctk.CTkFrame(sc, fg_color="transparent")

        _section_label(network_section, "NETWORK INTERFACES")
        _url_row(network_section, "Localhost", url_local)
        _url_row(network_section, "LAN Host", url_lan)

        pub_row = ctk.CTkFrame(network_section, fg_color=CARD, corner_radius=10)
        pub_row.pack(fill="x", pady=3)
        ctk.CTkLabel(pub_row, text="Remote Access", font=ctk.CTkFont(size=11), text_color=MUTED,
                     anchor="w").pack(side="left", padx=14, pady=8, expand=True, fill="x")
        pub_lbl = ctk.CTkLabel(pub_row, text="Detecting…", font=ctk.CTkFont(size=11, weight="bold"),
                               text_color=MUTED, anchor="e")
        pub_lbl.pack(side="left", expand=True, fill="x")
        
        pub_copy_btn = ctk.CTkButton(pub_row, text="📋", width=32, fg_color="transparent", text_color=MUTED,
                                     hover_color=BORDER, corner_radius=6, state="disabled")
        pub_copy_btn.pack(side="right", padx=8)

        def _toggle_network():
            if network_section.winfo_ismapped():
                network_section.pack_forget()
                toggle_btn.configure(text="▷ Show Technical Details")
            else:
                network_section.pack(fill="x", pady=(5, 0))
                toggle_btn.configure(text="▽ Hide Technical Details")

        toggle_btn.configure(command=_toggle_network)

        def _fetch_pub():
            def _update_ui(txt, col, enable_btn, remote_url=None):
                try:
                    pub_lbl.configure(text=txt, text_color=col)
                    if enable_btn and remote_url:
                        pub_copy_btn.configure(state="normal", command=lambda: app.clipboard_clear() or app.clipboard_append(remote_url))
                    else:
                        pub_copy_btn.configure(state="disabled")
                except: pass
                
            try:
                ip = urllib.request.urlopen("https://api.ipify.org", timeout=4).read().decode()
                remote = f"{scheme}://{ip}:{HECOS_PORT}"
                app.after(0, _update_ui, remote, TEXT, True, remote)
            except Exception:
                app.after(0, _update_ui, "Unreachable", RED, False)

        threading.Thread(target=_fetch_pub, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────────
    # TAB: LIVE LOGS
    # ─────────────────────────────────────────────────────────────────────────

    def _build_logs():
        # Outer container
        outer = ctk.CTkFrame(content_frame, fg_color="transparent", corner_radius=0)
        outer.pack(fill="both", expand=True, padx=20, pady=20)
        _content_widgets.append(outer)

        _title(outer, "Live Logs")
        _subtitle(outer, "Read directly from disk — works even when the WebUI is offline.")

        logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))

        SEV_COLORS = {
            "ERROR": RED, "CRITICAL": RED,
            "WARNING": AMBER,
            "INFO": "#ffffff",
            "DEBUG": "#94a3b8",
        }

        def _sev_color(line):
            u = line.upper()
            for kw, col in SEV_COLORS.items():
                if kw in u:
                    return col
            return MUTED

        # Top controls
        ctrl_row = ctk.CTkFrame(outer, fg_color="transparent")
        ctrl_row.pack(fill="x", pady=(0, 6))

        # File selector
        log_files = []
        try:
            log_files = sorted(
                [f for f in os.listdir(logs_dir) if f.endswith(".log")],
                key=lambda x: os.path.getmtime(os.path.join(logs_dir, x)),
                reverse=True
            )
        except Exception:
            pass

        default_log = "hecos_main.log" if "hecos_main.log" in log_files else (log_files[0] if log_files else "")

        file_var = ctk.StringVar(value=default_log)
        file_dd = ctk.CTkOptionMenu(ctrl_row, variable=file_var,
                                    values=log_files if log_files else ["(no logs)"],
                                    fg_color=CARD, button_color=ACCENT2,
                                    dropdown_fg_color=CARD, text_color=TEXT,
                                    font=ctk.CTkFont(size=11), width=260)
        file_dd.pack(side="left", padx=(0, 8))

        lines_lbl = ctk.CTkLabel(ctrl_row, text="", font=ctk.CTkFont(size=10), text_color=MUTED)
        lines_lbl.pack(side="right")

        font_size = [10]  # mutable

        # Log text widget (tkinter Text for performance with large files)
        import tkinter as tk
        log_frame = ctk.CTkFrame(outer, fg_color=CARD, corner_radius=8)
        log_frame.pack(fill="both", expand=True, pady=(4, 0))

        log_text = tk.Text(
            log_frame, wrap="none",
            bg=CARD, fg=TEXT, selectbackground=ACCENT2, selectforeground="#ffffff",
            insertbackground=ACCENT,
            font=("Consolas", font_size[0]),
            relief="flat", padx=6, pady=4,
            state="disabled"
        )
        scroll_y = ctk.CTkScrollbar(log_frame, command=log_text.yview)
        scroll_x = ctk.CTkScrollbar(log_frame, orientation="horizontal",
                                    command=log_text.xview)
        log_text.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        log_text.pack(side="left", fill="both", expand=True)

        # Tags for coloring
        for kw, col in SEV_COLORS.items():
            log_text.tag_configure(kw, foreground=col)
        log_text.tag_configure("MUTED", foreground=MUTED)

        _last_size = [0]

        def _load(auto=False):
            fname = file_var.get()
            if not fname or fname == "(no logs)":
                return
            path = os.path.join(logs_dir, fname)
            try:
                sz = os.path.getsize(path)
                if auto and sz == _last_size[0]:
                    return
                _last_size[0] = sz
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    all_lines = f.readlines()
                tail = all_lines[-400:] if len(all_lines) > 400 else all_lines
                lines_lbl.configure(
                    text=f"{len(all_lines)} lines — showing last {len(tail)}"
                )
                log_text.configure(state="normal")
                log_text.delete("1.0", "end")
                for line in tail:
                    stripped = line.rstrip()
                    col_tag = "MUTED"
                    u = stripped.upper()
                    for kw in ("ERROR", "CRITICAL", "WARNING", "INFO", "DEBUG"):
                        if kw in u:
                            col_tag = kw
                            break
                    log_text.insert("end", stripped + "\n", col_tag)
                log_text.configure(state="disabled")
                log_text.see("end")
            except Exception as ex:
                log_text.configure(state="normal")
                log_text.delete("1.0", "end")
                log_text.insert("end", f"Error reading log: {ex}")
                log_text.configure(state="disabled")

        def _on_file_change(choice):
            _last_size[0] = 0
            _load()

        file_dd.configure(command=_on_file_change)

        # Zoom buttons
        def _zoom(delta):
            font_size[0] = max(6, min(24, font_size[0] + delta))
            log_text.configure(font=("Consolas", font_size[0]))

        btn_row = ctk.CTkFrame(ctrl_row, fg_color="transparent")
        btn_row.pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="A-", width=34, fg_color=SURFACE, text_color=TEXT,
                      hover_color=BORDER, corner_radius=6,
                      command=lambda: _zoom(-2)).pack(side="left", padx=2)
        ctk.CTkButton(btn_row, text="A+", width=34, fg_color=SURFACE, text_color=TEXT,
                      hover_color=BORDER, corner_radius=6,
                      command=lambda: _zoom(2)).pack(side="left", padx=2)
        ctk.CTkButton(btn_row, text="↻", width=34, fg_color=SURFACE, text_color=ACCENT,
                      hover_color=BORDER, corner_radius=6,
                      command=_load).pack(side="left", padx=2)

        # Initial load
        _load()

        # Auto-refresh every 2 seconds while this tab is active
        def _auto_refresh():
            while _active_tab["key"] == "logs":
                time.sleep(2)
                if _active_tab["key"] == "logs":
                    app.after(0, lambda: _load(auto=True))

        threading.Thread(target=_auto_refresh, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────────
    # TAB: ABOUT
    # ─────────────────────────────────────────────────────────────────────────

    def _build_about():
        sc = ctk.CTkScrollableFrame(content_frame, fg_color="transparent", corner_radius=0)
        sc.pack(fill="both", expand=True, padx=20, pady=20)
        _content_widgets.append(sc)

        _title(sc, "About Hecos")

        card = ctk.CTkFrame(sc, fg_color=CARD, corner_radius=14)
        card.pack(fill="x", pady=(10, 0))

        ctk.CTkLabel(card, text="HECOS", font=ctk.CTkFont(size=32, weight="bold"),
                     text_color=ACCENT).pack(pady=(20, 0))
        ctk.CTkLabel(card, text="Helping Companion System",
                     font=ctk.CTkFont(size=13), text_color=MUTED).pack()
        ctk.CTkFrame(card, height=1, fg_color=BORDER).pack(fill="x", padx=20, pady=14)

        _info_row(card, "Version",  get_version())
        _info_row(card, "Creator",  "Antonio Meloni")
        _info_row(card, "Port",     str(HECOS_PORT))

        ctk.CTkFrame(card, height=12, fg_color="transparent").pack()

    # ── Tab dispatch ───────────────────────────────────────────────────────────
    TAB_BUILDERS = {
        "status":   _build_status,
        "settings": _build_settings,
        "browser":  _build_browser,
        "mobile":   _build_mobile,
        "logs":     _build_logs,
        "about":    _build_about,
    }

    # ── Open default tab ───────────────────────────────────────────────────────
    _switch_tab("status")

    # ── Center window on screen ────────────────────────────────────────────────
    app.update_idletasks()
    w, h = app.winfo_width(), app.winfo_height()
    sw, sh = app.winfo_screenwidth(), app.winfo_screenheight()
    app.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    # Terminate splash screen just before showing the main window
    try:
        splash_proc.terminate()
    except Exception:
        pass

    app.mainloop()
