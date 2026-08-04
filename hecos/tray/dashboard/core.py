import os
import sys
import threading
import subprocess
import socket as _sock
import customtkinter as ctk

from hecos.tray.system_utils import get_named_executable, get_version
from hecos.tray.browser_manager import intelligent_open_webui

from hecos.tray.dashboard.theme import apply_theme, BG, SURFACE, BORDER, ACCENT, MUTED, TEXT, ACCENT2, RED
from hecos.tray.dashboard.context import DashboardContext

from hecos.tray.dashboard.tabs.status import build_status
from hecos.tray.dashboard.tabs.settings import build_settings
from hecos.tray.dashboard.tabs.browser import build_browser
from hecos.tray.dashboard.tabs.mobile import build_mobile
from hecos.tray.dashboard.tabs.logs import build_logs
from hecos.tray.dashboard.tabs.processes import build_processes
from hecos.tray.dashboard.tabs.about import build_about
from hecos.tray.dashboard.tabs.webui import build_webui

_proc = None

def show_control_center(icon=None, item=None):
    """Launch the dashboard in a separate subprocess (non-blocking)."""
    global _proc
    with threading.Lock():
        if '_proc' in globals() and _proc and _proc.poll() is None:
            return
        env = os.environ.copy()
        from hecos.tray.config import _ROOT
        
        # Check if we are running as a compiled Nuitka binary (which is in bin/)
        dashboard_exe_nuitka = os.path.join(_ROOT, "bin", "hecos_dashboard.exe")
        
        if os.path.exists(dashboard_exe_nuitka) and getattr(sys, 'compiled', False):
            cmd = [dashboard_exe_nuitka]
        else:
            exe = get_named_executable("hecos_dashboard", sys.executable)
            cmd = [exe, "-m", "hecos.tray.control_center"]
        
        _proc = subprocess.Popen(
            cmd,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            env=env,
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
        )

def run_dashboard():
    """Main entry point for the Dashboard subprocess."""
    # ── Single Instance Lock ───────────────────────────────────────────────────
    try:
        __lock_socket = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
        __lock_socket.bind(("127.0.0.1", 54321))
    except _sock.error:
        print("[Tray Dashboard] Already running.")
        sys.exit(0)

    # ── Native Splash Screen (thread-based, safe for compiled binary) ──────────
    from hecos.tray.config import _ROOT
    logo_path = os.path.join(_ROOT, "hecos", "assets", "Hecos_Logo_SQR_NBG_LogoOnly.png")

    import tkinter as tk
    _splash_root = [None]

    def _show_splash():
        try:
            splash = tk.Tk()
            splash.overrideredirect(True)
            splash.configure(bg='#111318')
            sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
            splash.geometry(f'280x280+{(sw-280)//2}+{(sh-280)//2}')
            try:
                img = tk.PhotoImage(file=logo_path)
                img = img.subsample(max(1, img.width() // 150))
                lbl = tk.Label(splash, image=img, bg='#111318')
                lbl.image = img
                lbl.pack(expand=True, pady=(30, 0))
            except Exception:
                pass
            tk.Label(splash, text='Loading Hecos Dashboard...', fg='#00b4d8',
                     bg='#111318', font=('Helvetica', 11, 'bold')).pack(pady=20)
            _splash_root[0] = splash
            splash.mainloop()
        except Exception:
            pass

    splash_thread = threading.Thread(target=_show_splash, daemon=True)
    splash_thread.start()

    # ── Theme ──────────────────────────────────────────────────────────────────
    apply_theme()

    # ── App Window ─────────────────────────────────────────────────────────────
    try:
        _tray_ver_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "version")
        _tray_ver = open(_tray_ver_file, encoding="utf-8").read().strip()
    except Exception:
        _tray_ver = "1.0.1"

    app = ctk.CTk()
    app.title(f"Hecos Tray Dashboard v{_tray_ver}")
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
        ico = os.path.join(_ROOT, "hecos", "assets", "Hecos_Logo_SQR_NBG_LogoOnly.ico")
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
        ("webui",    "🖥  Web UI"),
        ("browser",  "🌐  Browser"),
        ("mobile",   "📱  Remote Access"),
        ("logs",     "📋  Live Logs"),
        ("processes","🛠  Processes"),
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

    # Instantiate the Dashboard Context
    ctx = DashboardContext(
        app=app,
        content_frame=content_frame,
        content_widgets=_content_widgets,
        active_tab=_active_tab,
        rebuild_tab_fn=lambda key: _rebuild_tab(key),
        switch_tab_fn=lambda key: _switch_tab(key)
    )

    TAB_BUILDERS = {
        "status":    lambda: build_status(ctx),
        "settings":  lambda: build_settings(ctx),
        "webui":     lambda: build_webui(ctx),
        "browser":   lambda: build_browser(ctx),
        "mobile":    lambda: build_mobile(ctx),
        "logs":      lambda: build_logs(ctx),
        "processes": lambda: build_processes(ctx),
        "about":     lambda: build_about(ctx),
    }

    def _rebuild_tab(key):
        """Force-rebuild the content of a tab."""
        _active_tab["key"] = key
        _highlight(key)
        _clear_content()
        try:
            TAB_BUILDERS[key]()
        except Exception as _tab_err:
            import traceback
            _err_msg = traceback.format_exc()
            # Log to file for debugging compiled binary
            try:
                _log_path = os.path.join(_ROOT, "hecos", "logs", "dashboard_tab_error.log")
                with open(_log_path, "a", encoding="utf-8") as _f:
                    _f.write(f"\n[TAB ERROR: {key}]\n{_err_msg}\n")
            except Exception:
                pass
            # Show error in UI so it's visible
            import customtkinter as _ctk
            _err_frame = _ctk.CTkFrame(content_frame, fg_color="transparent")
            _err_frame.pack(fill="both", expand=True, padx=30, pady=30)
            _content_widgets.append(_err_frame)
            _ctk.CTkLabel(_err_frame, text=f"⚠ Error loading tab '{key}':",
                          font=_ctk.CTkFont(size=13, weight="bold"),
                          text_color="#ef4444").pack(anchor="w", pady=(0, 8))
            _ctk.CTkLabel(_err_frame, text=str(_tab_err),
                          font=_ctk.CTkFont(size=11),
                          text_color="#aaaaaa", wraplength=600, justify="left").pack(anchor="w")

    def _switch_tab(key):
        if _active_tab["key"] == key:
            return  # already active
        _rebuild_tab(key)

    nav_area = ctk.CTkFrame(sidebar, fg_color="transparent", corner_radius=0)
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

    # ── Open default tab ───────────────────────────────────────────────────────
    _switch_tab("status")

    # ── Kill splash as soon as the window is ready ─────────────────────────────
    def _kill_splash():
        try:
            splash = _splash_root[0]
            if splash:
                splash.quit()
                splash.destroy()
        except Exception:
            pass
    app.after(300, _kill_splash)

    # ── Main Loop ──────────────────────────────────────────────────────────────
    try:
        app.mainloop()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[ControlCenter] UI crashed: {e}")
    finally:
        # Ensure splash is dead even if mainloop exits unexpectedly
        try:
            splash = _splash_root[0]
            if splash:
                splash.quit()
        except Exception:
            pass
