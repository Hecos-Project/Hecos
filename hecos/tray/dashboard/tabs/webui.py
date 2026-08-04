import os
import tkinter.filedialog as fd
import customtkinter as ctk

from hecos.tray.config import get_webui_config, save_webui_config
from hecos.tray.dashboard.theme import CARD, TEXT, MUTED, ACCENT, ACCENT2, BORDER, GREEN, RED, SURFACE
from hecos.tray.dashboard.ui import title, subtitle, make_card

def build_webui(ctx):
    sc = ctk.CTkFrame(ctx.content_frame, fg_color="transparent", corner_radius=0)
    sc.pack(fill="both", expand=True, padx=20, pady=20)
    ctx.append_widget(sc)

    title(ctx, sc, "Web UI Configuration")
    subtitle(ctx, sc, "Read and write the WebUI server settings. Changes are saved to plugins.yaml and require a Hecos restart.")

    cfg = get_webui_config()

    # ── Status banner ─────────────────────────────────────────────────────────
    banner = ctk.CTkFrame(sc, fg_color=SURFACE, corner_radius=10, border_width=1, border_color=BORDER)
    banner.pack(fill="x", pady=(0, 12))
    banner_lbl = ctk.CTkLabel(banner, text="", fg_color="transparent", font=ctk.CTkFont(size=11), text_color=MUTED)
    banner_lbl.pack(padx=14, pady=8, anchor="w")

    def _show_banner(msg, color=GREEN):
        banner_lbl.configure(text=msg, text_color=color)
        ctx.app.after(4000, lambda: banner_lbl.configure(text=""))

    # ── Card: Port & Toggles ──────────────────────────────────────────────────
    card1 = make_card(sc)
    card1.pack(fill="x", pady=(0, 8))

    # Port
    port_row = ctk.CTkFrame(card1, fg_color="transparent")
    port_row.pack(fill="x", padx=14, pady=(14, 6))
    ctk.CTkLabel(port_row, text="Server Port", fg_color="transparent",
                 font=ctk.CTkFont(size=12), text_color=TEXT, anchor="w").pack(side="left", expand=True, fill="x")
    ctk.CTkLabel(port_row, text="(requires restart)", fg_color="transparent",
                 font=ctk.CTkFont(size=10), text_color=MUTED).pack(side="left", padx=(0, 12))
    port_var = ctk.StringVar(value=str(cfg.get("port", 7070)))
    ctk.CTkEntry(port_row, textvariable=port_var, width=80,
                 fg_color=SURFACE, border_color=BORDER, text_color=TEXT,
                 justify="center", font=ctk.CTkFont(size=12)).pack(side="right")

    # Toggles — auto_open_browser intentionally excluded (managed in Settings tab)
    toggles = [
        ("https_enabled", "Enable HTTPS",           "Use SSL/TLS encryption (cert and key files required below)"),
        ("force_login",   "Require Authentication", "Users must log in to access the WebUI"),
    ]

    toggle_vars = {}
    for key, label, hint in toggles:
        row = ctk.CTkFrame(card1, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=4)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(info, text=label, fg_color="transparent",
                     font=ctk.CTkFont(size=12), text_color=TEXT, anchor="w").pack(anchor="w")
        ctk.CTkLabel(info, text=hint, fg_color="transparent",
                     font=ctk.CTkFont(size=10), text_color=MUTED, anchor="w").pack(anchor="w")

        var = ctk.BooleanVar(value=bool(cfg.get(key, False)))
        toggle_vars[key] = var
        ctk.CTkSwitch(row, text="", variable=var, onvalue=True, offvalue=False,
                      progress_color=ACCENT).pack(side="right", pady=6)

    ctk.CTkFrame(card1, height=8, fg_color="transparent").pack()

    # ── Card: SSL Certificates ────────────────────────────────────────────────
    card2 = make_card(sc)
    card2.pack(fill="x", pady=(0, 8))

    ctk.CTkLabel(card2, text="SSL Certificates", fg_color="transparent",
                 font=ctk.CTkFont(size=11, weight="bold"), text_color=MUTED,
                 anchor="w").pack(padx=14, pady=(12, 6), anchor="w")

    def _path_row(parent, label, initial_val):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(row, text=label, fg_color="transparent", font=ctk.CTkFont(size=11),
                     text_color=TEXT, width=60, anchor="w").pack(side="left")
        var = ctk.StringVar(value=str(initial_val or ""))
        ctk.CTkEntry(row, textvariable=var, fg_color=SURFACE, border_color=BORDER,
                     text_color=TEXT, font=ctk.CTkFont(size=10)).pack(side="left", fill="x", expand=True, padx=(8, 6))

        def _browse(v=var):
            path = fd.askopenfilename(
                title=f"Select {label}",
                filetypes=[("PEM files", "*.pem"), ("CRT files", "*.crt"), ("All files", "*.*")]
            )
            if path:
                v.set(path)

        ctk.CTkButton(row, text="Browse", width=70, fg_color=SURFACE, text_color=MUTED,
                      hover_color=BORDER, border_width=1, border_color=BORDER,
                      corner_radius=6, command=_browse).pack(side="right")
        return var

    cert_var = _path_row(card2, "cert.pem", cfg.get("cert_file", ""))
    key_var  = _path_row(card2, "key.pem",  cfg.get("key_file", ""))
    ctk.CTkFrame(card2, height=8, fg_color="transparent").pack()

    # ── Save ──────────────────────────────────────────────────────────────────
    def _save():
        try:
            port_val = int(port_var.get().strip())
            if not (1 <= port_val <= 65535):
                raise ValueError("out of range")
        except ValueError:
            _show_banner("⚠  Invalid port. Enter a number between 1 and 65535.", RED)
            return

        new_cfg = {
            "port":          port_val,
            "https_enabled": toggle_vars["https_enabled"].get(),
            "force_login":   toggle_vars["force_login"].get(),
            "cert_file":     cert_var.get().strip(),
            "key_file":      key_var.get().strip(),
        }
        save_webui_config(new_cfg)
        _show_banner("✅  Saved to plugins.yaml — restart Hecos to apply changes.", GREEN)

    ctk.CTkButton(sc, text="💾  Save Configuration", fg_color=ACCENT, text_color="#000000",
                  hover_color=ACCENT2, corner_radius=8, font=ctk.CTkFont(size=12, weight="bold"),
                  height=40, command=_save).pack(fill="x", pady=(8, 0))
