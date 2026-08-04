import customtkinter as ctk
import urllib.request
import json as _json
import threading
from hecos.tray.dashboard.theme import TEXT, MUTED, ACCENT, RED, SURFACE, BORDER
from hecos.tray.dashboard.ui import make_card, title, section_label, info_row
from hecos.tray.network_utils import is_hecos_online, get_scheme
from hecos.tray.browser_manager import _get_cdp_port, is_ai_ready_browser_running
from hecos.tray.config import HECOS_PORT

def build_status(ctx):
    sc = ctk.CTkFrame(ctx.content_frame, fg_color="transparent", corner_radius=0)
    sc.pack(fill="both", expand=True, padx=20, pady=20)
    ctx.append_widget(sc)

    title(ctx, sc, "System Status")

    online = is_hecos_online()
    cdp_p  = _get_cdp_port()
    cdp_ok = is_ai_ready_browser_running(cdp_p)

    section_label(ctx, sc, "CORE")
    c1 = make_card(sc)
    c1.pack(fill="x", pady=(0, 8))
    info_row(c1, "Status",   "Online" if online else "Offline",
              ACCENT if online else RED)
    info_row(c1, "Protocol", get_scheme().upper())
    info_row(c1, "Port",     str(HECOS_PORT))

    section_label(ctx, sc, "BROWSER (CDP)")
    c2 = make_card(sc)
    c2.pack(fill="x", pady=(0, 8))
    info_row(c2, "Connection",
              f"Port {cdp_p} Open" if cdp_ok else f"Port {cdp_p} Closed",
              ACCENT if cdp_ok else RED)

    row_f = ctk.CTkFrame(c2, fg_color="transparent")
    row_f.pack(fill="x", padx=14, pady=5)
    ctk.CTkLabel(row_f, text="Active Engine", fg_color="transparent", font=ctk.CTkFont(size=11),
                 text_color=MUTED, anchor="w").pack(side="left", expand=True, fill="x")
    browser_lbl = ctk.CTkLabel(row_f, text="Detecting…", fg_color="transparent", font=ctk.CTkFont(size=11),
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
        
        ctx.app.after(0, _update_ui, val, col)

    if cdp_ok:
        threading.Thread(target=_fetch_browser, daemon=True).start()
    else:
        browser_lbl.configure(text="Not Detected", text_color=MUTED)

    def _refresh():
        ctx.rebuild_tab("status")

    ctk.CTkButton(sc, text="↻ Refresh", fg_color=SURFACE, text_color=TEXT,
                  hover_color=BORDER, corner_radius=8,
                  command=_refresh).pack(anchor="w", pady=(8, 0))
