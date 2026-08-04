import customtkinter as ctk
from hecos.tray.dashboard.theme import CARD, TEXT, MUTED

def make_card(parent, **kw):
    f = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=10, **kw)
    return f

def title(ctx, parent, text):
    lbl = ctk.CTkLabel(parent, text=text, fg_color="transparent",
                       font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT)
    lbl.pack(anchor="w", pady=(0, 2))
    ctx.append_widget(lbl)
    return lbl

def subtitle(ctx, parent, text):
    lbl = ctk.CTkLabel(parent, text=text, fg_color="transparent", font=ctk.CTkFont(size=11), text_color=MUTED)
    lbl.pack(anchor="w", pady=(0, 8))
    ctx.append_widget(lbl)
    return lbl

def section_label(ctx, parent, text):
    lbl = ctk.CTkLabel(parent, text=text, fg_color="transparent",
                       font=ctk.CTkFont(size=10, weight="bold"), text_color=MUTED)
    lbl.pack(anchor="w", pady=(8, 2))
    ctx.append_widget(lbl)
    return lbl

def info_row(card, label, value, value_color=TEXT):
    row = ctk.CTkFrame(card, fg_color="transparent")
    row.pack(fill="x", padx=14, pady=5)
    ctk.CTkLabel(row, text=label, fg_color="transparent", font=ctk.CTkFont(size=11), text_color=MUTED,
                 anchor="w").pack(side="left", expand=True, fill="x")
    ctk.CTkLabel(row, text=value, fg_color="transparent", font=ctk.CTkFont(size=11, weight="bold"),
                 text_color=value_color, anchor="e").pack(side="right")
    return row
