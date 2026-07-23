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
        import tkinter as tk
        from hecos.tray.network_utils import get_public_ip, check_wan_port

        sc = ctk.CTkScrollableFrame(content_frame, fg_color="transparent", corner_radius=0)
        sc.pack(fill="both", expand=True, padx=20, pady=20)
        _content_widgets.append(sc)

        _title(sc, "Remote Access")
        _subtitle(sc, "Click a connection to preview its QR code. Drag or right-click the QR to copy/save it.")

        scheme   = get_scheme()
        lan_ip   = get_lan_ip()
        url_local = f"{scheme}://127.0.0.1:{HECOS_PORT}/chat"
        url_lan   = f"{scheme}://{lan_ip}:{HECOS_PORT}/chat"

        # State
        _state = {
            "active_key": "lan",   # which row is selected
            "public_ip": None,
            "url_wan": None,
            "qr_pil": None,        # current PIL image for drag-save
        }

        # ── QR helpers ────────────────────────────────────────────────────────
        def _make_qr_pil(url: str, fill=ACCENT, back=CARD):
            import qrcode
            qr = qrcode.QRCode(box_size=6, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color=fill, back_color=back)
            return img.convert("RGB")

        def _pil_to_ctk(pil_img, size=190):
            ctk_img = ctk.CTkImage(
                light_image=pil_img, dark_image=pil_img,
                size=(size, size)
            )
            return ctk_img

        # ── QR Card ───────────────────────────────────────────────────────────
        qr_outer = ctk.CTkFrame(sc, fg_color=CARD, corner_radius=12)
        qr_outer.pack(pady=(0, 10))

        qr_label = ctk.CTkLabel(qr_outer, text="", image=None)
        qr_label.pack(padx=22, pady=16)

        qr_hint = ctk.CTkLabel(
            qr_outer,
            text="Right-click to copy • Drag to save",
            font=ctk.CTkFont(size=9), text_color=MUTED
        )
        qr_hint.pack(pady=(0, 10))

        # ── Drag & Copy logic (uses tkinter canvas trick) ─────────────────────
        _drag_state = {}

        def _on_qr_right_click(event):
            """Copy QR image to clipboard as PNG bytes (Windows only via win32clipboard)."""
            if _state["qr_pil"] is None:
                return
            try:
                import io, win32clipboard, win32con
                buf = io.BytesIO()
                _state["qr_pil"].save(buf, format="BMP")
                bmp_data = buf.getvalue()[14:]   # strip BMP file header
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_DIB, bmp_data)
                win32clipboard.CloseClipboard()
                qr_hint.configure(text="✅ Copied to clipboard!", text_color=GREEN)
                app.after(2000, lambda: qr_hint.configure(
                    text="Right-click to copy • Drag to save", text_color=MUTED))
            except ImportError:
                # Fallback: save to temp file and notify user
                import tempfile, os
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                _state["qr_pil"].save(tmp.name)
                tmp.close()
                qr_hint.configure(text=f"Saved to {tmp.name}", text_color=AMBER)
                app.after(3000, lambda: qr_hint.configure(
                    text="Right-click to copy • Drag to save", text_color=MUTED))
            except Exception as e:
                qr_hint.configure(text=f"Error: {e}", text_color=RED)
                app.after(2000, lambda: qr_hint.configure(
                    text="Right-click to copy • Drag to save", text_color=MUTED))

        def _on_drag_start(event):
            _drag_state["x"] = event.x
            _drag_state["y"] = event.y

        def _on_drag_motion(event):
            dx = abs(event.x - _drag_state.get("x", event.x))
            dy = abs(event.y - _drag_state.get("y", event.y))
            if dx > 5 or dy > 5:
                qr_hint.configure(text="📁 Release to save QR as PNG…", text_color=ACCENT)

        def _on_drag_release(event):
            if _state["qr_pil"] is None:
                return
            try:
                import tkinter.filedialog as fd
                path = fd.asksaveasfilename(
                    defaultextension=".png",
                    filetypes=[("PNG Image", "*.png")],
                    initialfile="hecos_qr.png",
                    title="Save QR Code"
                )
                if path:
                    _state["qr_pil"].save(path)
                    qr_hint.configure(text=f"✅ Saved!", text_color=GREEN)
                    app.after(2000, lambda: qr_hint.configure(
                        text="Right-click to copy • Drag to save", text_color=MUTED))
                else:
                    qr_hint.configure(text="Right-click to copy • Drag to save", text_color=MUTED)
            except Exception as ex:
                qr_hint.configure(text=f"Error: {ex}", text_color=RED)
                app.after(2000, lambda: qr_hint.configure(
                    text="Right-click to copy • Drag to save", text_color=MUTED))

        qr_label.bind("<Button-3>", _on_qr_right_click)
        qr_label.bind("<ButtonPress-1>", _on_drag_start)
        qr_label.bind("<B1-Motion>", _on_drag_motion)
        qr_label.bind("<ButtonRelease-1>", _on_drag_release)

        # ── Update QR display ─────────────────────────────────────────────────
        def _show_qr(url: str, placeholder: bool = False):
            if placeholder:
                qr_label.configure(image=None, text="⏳ Detecting WAN IP…",
                                   font=ctk.CTkFont(size=12), text_color=MUTED)
                _state["qr_pil"] = None
                return
            try:
                pil = _make_qr_pil(url)
                ctk_img = _pil_to_ctk(pil)
                qr_label.configure(image=ctk_img, text="")
                _state["qr_pil"] = pil
            except Exception as e:
                qr_label.configure(image=None,
                                   text=f"QR unavailable\n(pip install qrcode pillow)\n{e}",
                                   font=ctk.CTkFont(size=9), text_color=MUTED)
                _state["qr_pil"] = None

        # ── Connection rows ───────────────────────────────────────────────────
        _row_frames = {}

        LINKS = [
            ("local", "🖥  Localhost",     url_local, None),
            ("lan",   "📡  LAN",           url_lan,   None),
            ("wan",   "🌐  Remote (WAN)",  None,      None),   # URL filled later
        ]

        conn_section = ctk.CTkFrame(sc, fg_color="transparent")
        conn_section.pack(fill="x", pady=(0, 4))

        def _select_row(key: str):
            url = _state.get(f"url_{key}") or {
                "local": url_local, "lan": url_lan
            }.get(key)

            for k, rf in _row_frames.items():
                rf.configure(border_color=ACCENT if k == key else CARD)

            _state["active_key"] = key

            if key == "wan" and _state["url_wan"] is None:
                _show_qr("", placeholder=True)
            elif url:
                _show_qr(url)

        for key, label, url, _ in LINKS:
            # store static URLs
            if key != "wan":
                _state[f"url_{key}"] = url

            row = ctk.CTkFrame(conn_section, fg_color=CARD, corner_radius=10,
                               cursor="hand2", border_width=2, border_color=CARD)
            row.pack(fill="x", pady=3)
            _row_frames[key] = row

            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(side="left", fill="both", expand=True, padx=14, pady=9)

            lbl_title = ctk.CTkLabel(inner, text=label,
                                     font=ctk.CTkFont(size=12, weight="bold"),
                                     text_color=TEXT, anchor="w")
            lbl_title.pack(anchor="w")

            # URL sub-label (dynamic for WAN)
            url_text = url if url else "Detecting…"
            lbl_url = ctk.CTkLabel(inner, text=url_text,
                                   font=ctk.CTkFont(size=10), text_color=MUTED, anchor="w")
            lbl_url.pack(anchor="w")

            # Copy button
            copy_btn = ctk.CTkButton(
                row, text="📋", width=32, fg_color="transparent",
                text_color=MUTED, hover_color=BORDER, corner_radius=6
            )
            copy_btn.pack(side="right", padx=8)

            # Status badge (WAN only)
            if key == "wan":
                wan_badge = ctk.CTkLabel(row, text="  ⏳  ", font=ctk.CTkFont(size=11),
                                         text_color=MUTED)
                wan_badge.pack(side="right", padx=(0, 4))
                _state["wan_badge"] = wan_badge
                _state["wan_url_label"] = lbl_url
                _state["wan_copy_btn"] = copy_btn
                copy_btn.configure(state="disabled")
            else:
                v = url
                copy_btn.configure(command=lambda v=v: app.clipboard_clear() or app.clipboard_append(v))

            # Bind click on the whole row
            def _make_click(k=key):
                return lambda e: _select_row(k)

            click_fn = _make_click()
            for widget in (row, inner, lbl_title, lbl_url):
                widget.bind("<Button-1>", click_fn)

        # ── WAN Port Check banner ─────────────────────────────────────────────
        port_card = ctk.CTkFrame(sc, fg_color=SURFACE, corner_radius=10, border_width=1,
                                 border_color=BORDER)
        port_card.pack(fill="x", pady=(8, 0))

        port_header = ctk.CTkFrame(port_card, fg_color="transparent")
        port_header.pack(fill="x", padx=14, pady=(10, 4))
        ctk.CTkLabel(port_header, text=f"◉  Port {HECOS_PORT} WAN Reachability",
                     font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT,
                     anchor="w").pack(side="left")

        port_status_lbl = ctk.CTkLabel(port_header, text="Checking…",
                                       font=ctk.CTkFont(size=11), text_color=MUTED)
        port_status_lbl.pack(side="right")

        port_detail_lbl = ctk.CTkLabel(port_card, text="",
                                       font=ctk.CTkFont(size=9), text_color=MUTED,
                                       wraplength=420, justify="left")
        port_detail_lbl.pack(anchor="w", padx=14, pady=(0, 10))

        recheck_btn = ctk.CTkButton(
            port_card, text="↻ Re-check", fg_color="transparent", text_color=ACCENT,
            hover_color=BORDER, corner_radius=6, font=ctk.CTkFont(size=10), width=90
        )
        recheck_btn.pack(anchor="e", padx=14, pady=(0, 8))

        # ── Background fetches ────────────────────────────────────────────────
        def _do_wan_fetch():
            """Fetch public IP, then kick off port check — all in background thread."""
            # Step 1: get public IP
            try:
                pub_ip = get_public_ip(timeout=5)
                wan_url = f"{scheme}://{pub_ip}:{HECOS_PORT}/chat"
                _state["public_ip"] = pub_ip
                _state["url_wan"] = wan_url

                def _on_ip(ip=pub_ip, url=wan_url):
                    try:
                        _state["wan_url_label"].configure(text=url)
                        _state["wan_badge"].configure(text=" ✅ ", text_color=ACCENT)
                        _state["wan_copy_btn"].configure(
                            state="normal",
                            command=lambda: app.clipboard_clear() or app.clipboard_append(url)
                        )
                        if _state["active_key"] == "wan":
                            _show_qr(url)
                    except Exception:
                        pass

                app.after(0, _on_ip)

                # Step 2: check if port is actually reachable
                _do_port_check(pub_ip)

            except Exception as exc:
                def _on_fail():
                    try:
                        _state["wan_url_label"].configure(text="Unreachable")
                        _state["wan_badge"].configure(text=" 🔴 ", text_color=RED)
                        port_status_lbl.configure(text="No public IP", text_color=RED)
                        port_detail_lbl.configure(
                            text=f"Could not determine public IP: {exc}")
                    except Exception:
                        pass
                app.after(0, _on_fail)

        def _do_port_check(ip: str):
            """Run port check and update the banner (called from background thread)."""
            result = check_wan_port(ip, port=HECOS_PORT, timeout=10)
            status = result.get("status", "error")
            method = result.get("method", "")
            detail = result.get("detail", "")

            if status == "open":
                badge_txt = "✅ Open"
                col = GREEN
            elif status == "closed":
                badge_txt = "🔴 Closed"
                col = RED
            elif status == "timeout":
                badge_txt = "⚠️ Timeout"
                col = AMBER
            else:
                badge_txt = "⚠️ Unknown"
                col = AMBER

            via = f" · via {method}" if method else ""

            def _upd_port():
                try:
                    port_status_lbl.configure(text=badge_txt, text_color=col)
                    port_detail_lbl.configure(
                        text=f"{detail}{via}",
                        text_color=MUTED if status in ("open", "closed") else AMBER
                    )
                except Exception:
                    pass

            app.after(0, _upd_port)

        def _start_all_checks():
            """(Re-)trigger all background checks."""
            port_status_lbl.configure(text="Checking…", text_color=MUTED)
            port_detail_lbl.configure(text="")
            _state["wan_url_label"].configure(text="Detecting…")
            _state["wan_badge"].configure(text=" ⏳ ", text_color=MUTED)
            _state["wan_copy_btn"].configure(state="disabled")
            threading.Thread(target=_do_wan_fetch, daemon=True).start()

        recheck_btn.configure(command=_start_all_checks)

        # ── Initial state: select LAN row + start background checks ──────────
        _select_row("lan")
        _start_all_checks()


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
        log_text.tag_configure("URL", foreground=ACCENT, underline=True)

        def _open_url(event):
            try:
                idx = log_text.index(f"@{event.x},{event.y}")
                tags = log_text.tag_names(idx)
                if "URL" in tags:
                    rng = log_text.tag_prevrange("URL", f"{idx}+1c")
                    if rng:
                        url = log_text.get(rng[0], rng[1])
                        webbrowser.open(url)
            except Exception:
                pass

        log_text.tag_bind("URL", "<Button-1>", _open_url)
        log_text.tag_bind("URL", "<Enter>", lambda e: log_text.configure(cursor="hand2"))
        log_text.tag_bind("URL", "<Leave>", lambda e: log_text.configure(cursor=""))

        _last_size = [0]

        def _load(auto=False):
            fname = file_var.get()
            if not fname or fname == "(no logs)":
                return
            path = os.path.join(logs_dir, fname)
            try:
                sz = os.path.getsize(path)
                if auto and (sz == _last_size[0] or is_paused[0]):
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
                import re
                url_pattern = re.compile(r'(https?://[^\s\'"<>]+)')

                for line in tail:
                    stripped = line.rstrip()
                    col_tag = "MUTED"
                    u = stripped.upper()
                    for kw in ("ERROR", "CRITICAL", "WARNING", "INFO", "DEBUG"):
                        if kw in u:
                            col_tag = kw
                            break
                    
                    parts = url_pattern.split(stripped)
                    for p in parts:
                        if url_pattern.match(p):
                            log_text.insert("end", p, ("URL", col_tag))
                        else:
                            log_text.insert("end", p, col_tag)
                    log_text.insert("end", "\n", col_tag)
                
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
        
        is_paused = [False]

        def _toggle_pause():
            is_paused[0] = not is_paused[0]
            if is_paused[0]:
                btn_pause.configure(text="🔒", text_color=RED)
            else:
                btn_pause.configure(text="🔓", text_color=MUTED)

        btn_pause = ctk.CTkButton(btn_row, text="🔓", width=34, fg_color=SURFACE, text_color=MUTED,
                                  hover_color=BORDER, corner_radius=6,
                                  command=_toggle_pause)
        btn_pause.pack(side="left", padx=2)

        ctk.CTkButton(btn_row, text="A-", width=34, fg_color=SURFACE, text_color=TEXT,
                      hover_color=BORDER, corner_radius=6,
                      command=lambda: _zoom(-2)).pack(side="left", padx=2)
        ctk.CTkButton(btn_row, text="A+", width=34, fg_color=SURFACE, text_color=TEXT,
                      hover_color=BORDER, corner_radius=6,
                      command=lambda: _zoom(2)).pack(side="left", padx=2)
        ctk.CTkButton(btn_row, text="↻", width=34, fg_color=SURFACE, text_color=ACCENT,
                      hover_color=BORDER, corner_radius=6,
                      command=lambda: _load(auto=False)).pack(side="left", padx=2)

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
