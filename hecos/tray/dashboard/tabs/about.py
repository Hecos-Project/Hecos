import os
import customtkinter as ctk

from hecos.tray.dashboard.theme import CARD, ACCENT, MUTED, BORDER
from hecos.tray.dashboard.ui import title, info_row
from hecos.tray.system_utils import get_version
from hecos.tray.config import HECOS_PORT

def get_tray_version() -> str:
    try:
        _dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        vfile = os.path.join(_dir, "version")
        with open(vfile, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "1.3.1"

def build_about(ctx):
    sc = ctk.CTkFrame(ctx.content_frame, fg_color="transparent", corner_radius=0)
    sc.pack(fill="both", expand=True, padx=20, pady=20)
    ctx.append_widget(sc)

    title(ctx, sc, "About Hecos")

    card = ctk.CTkFrame(sc, fg_color=CARD, corner_radius=14)
    card.pack(fill="x", pady=(10, 0))

    ctk.CTkLabel(card, text="HECOS", fg_color="transparent", font=ctk.CTkFont(size=32, weight="bold"),
                 text_color=ACCENT).pack(pady=(20, 0))
    ctk.CTkLabel(card, text="Helping Companion System", fg_color="transparent",
                 font=ctk.CTkFont(size=13), text_color=MUTED).pack()
    
    ctk.CTkFrame(card, height=1, fg_color=BORDER).pack(fill="x", padx=20, pady=14)

    info_row(card, "Tray Version",      get_tray_version())
    info_row(card, "Creator",           "Antonio Meloni")
    info_row(card, "Port",              str(HECOS_PORT))

    ctk.CTkFrame(card, height=12, fg_color="transparent").pack()
