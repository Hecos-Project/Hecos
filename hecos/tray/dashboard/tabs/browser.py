import customtkinter as ctk
import webbrowser
import threading
from hecos.tray.dashboard.theme import CARD, TEXT, MUTED, ACCENT, ACCENT2
from hecos.tray.dashboard.ui import title, subtitle
from hecos.tray.browser_manager import intelligent_open_webui, launch_ai_ready_browser, _get_cdp_port
from hecos.tray.network_utils import get_urls

def build_browser(ctx):
    sc = ctk.CTkFrame(ctx.content_frame, fg_color="transparent", corner_radius=0)
    sc.pack(fill="both", expand=True, padx=20, pady=20)
    ctx.append_widget(sc)

    title(ctx, sc, "Browser Control")
    subtitle(ctx, sc, "Manage browser sessions.")

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

    for title_text, sub, action in browser_actions:
        card = ctk.CTkFrame(sc, fg_color=CARD, corner_radius=10)
        card.pack(fill="x", pady=4)

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=14, pady=10)
        ctk.CTkLabel(info, text=title_text, fg_color="transparent", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=TEXT, anchor="w").pack(anchor="w")
        ctk.CTkLabel(info, text=sub, fg_color="transparent", font=ctk.CTkFont(size=10),
                     text_color=MUTED, anchor="w").pack(anchor="w")

        ctk.CTkButton(card, text="Open", fg_color=ACCENT2, text_color="#ffffff",
                      hover_color=ACCENT, corner_radius=8, width=70,
                      command=lambda a=action: threading.Thread(target=a, daemon=True).start()
                      ).pack(side="right", padx=14, pady=10)
