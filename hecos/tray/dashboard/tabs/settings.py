import customtkinter as ctk
from hecos.tray.config import load_settings, save_settings
from hecos.tray.dashboard.theme import CARD, TEXT, ACCENT
from hecos.tray.dashboard.ui import title, subtitle

def build_settings(ctx):
    sc = ctk.CTkFrame(ctx.content_frame, fg_color="transparent", corner_radius=0)
    sc.pack(fill="both", expand=True, padx=20, pady=20)
    ctx.append_widget(sc)

    title(ctx, sc, "Settings")
    subtitle(ctx, sc, "Changes apply immediately.")

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

        ctk.CTkLabel(row, text=label, fg_color="transparent", font=ctk.CTkFont(size=12), text_color=TEXT,
                     anchor="w").pack(side="left", padx=14, pady=10, expand=True, fill="x")

        var = ctk.BooleanVar(value=cfg.get(key, default))

        def _on_toggle(v=var, k=key):
            s = load_settings()
            s[k] = v.get()
            save_settings(s)

        sw = ctk.CTkSwitch(row, text="", variable=var, onvalue=True, offvalue=False,
                           progress_color=ACCENT, command=_on_toggle)
        sw.pack(side="right", padx=14, pady=10)
