import os
import sys
import threading
import subprocess
import customtkinter as ctk

from hecos.tray.dashboard.theme import TEXT, MUTED, ACCENT, SURFACE, BORDER, RED
from hecos.tray.update_sources import load_sources, set_active_source, add_source, remove_source, import_source_list
from hecos.tray.updater import check_for_updates, download_asset, apply_update_and_restart, get_tray_version, get_current_version
from hecos.tray.config import _ROOT


def _card(parent, title):
    """Helper: creates a titled section card."""
    frame = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=10)
    frame.pack(fill="x", pady=(0, 14), ipadx=2, ipady=2)
    ctk.CTkLabel(
        frame, text=title,
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color=TEXT
    ).pack(anchor="w", padx=16, pady=(14, 6))
    return frame


def build_update(ctx):
    container = ctk.CTkScrollableFrame(ctx.content_frame, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=20, pady=16)
    ctx.content_widgets.append(container)

    # ── Page Header ────────────────────────────────────────────────────────────
    ctk.CTkLabel(
        container, text="Updates & Installation",
        font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT
    ).pack(anchor="w", pady=(0, 2))
    ctk.CTkLabel(
        container,
        text="Check for Hecos updates, manage sources, or repair your environment.",
        font=ctk.CTkFont(size=12), text_color=MUTED
    ).pack(anchor="w", pady=(0, 18))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1: Update Sources
    # ══════════════════════════════════════════════════════════════════════════
    src_card = _card(container, "🔗  Update Source")

    sources_data = load_sources()
    active_src = sources_data.get("active_source", "")
    source_names = [s["name"] for s in sources_data.get("sources", [])]
    if not source_names:
        source_names = ["(No sources configured)"]

    src_var = ctk.StringVar(value=active_src if active_src in source_names else source_names[0])

    def on_source_change(val):
        set_active_source(val)

    ctk.CTkOptionMenu(
        src_card, values=source_names, variable=src_var, command=on_source_change,
        fg_color=BORDER, button_color=BORDER, button_hover_color=ACCENT,
        dropdown_fg_color=SURFACE, text_color=TEXT
    ).pack(fill="x", padx=16, pady=(0, 10))

    # Remove source button
    def remove_selected():
        name = src_var.get()
        remove_source(name)
        ctx.switch_tab_fn("update")

    ctk.CTkButton(
        src_card, text="Remove Selected Source",
        fg_color="transparent", border_width=1, border_color=RED,
        text_color=RED, hover_color="#3a1a1a", height=28,
        command=remove_selected
    ).pack(anchor="w", padx=16, pady=(0, 4))

    # ── Add custom source expander ──────────────────────────────────────────
    add_panel = ctk.CTkFrame(src_card, fg_color="transparent")

    def toggle_add_panel():
        if add_panel.winfo_ismapped():
            add_panel.pack_forget()
            toggle_btn.configure(text="+ Add Custom Source")
        else:
            add_panel.pack(fill="x", padx=16, pady=(6, 4))
            toggle_btn.configure(text="▲ Hide")

    toggle_btn = ctk.CTkButton(
        src_card, text="+ Add Custom Source",
        fg_color="transparent", border_width=1, border_color=BORDER,
        text_color=MUTED, hover_color=BORDER, height=28,
        command=toggle_add_panel
    )
    toggle_btn.pack(anchor="w", padx=16, pady=(0, 4))

    # ── Import source list from URL (eMule-style) ──────────────────────────
    import_lbl = ctk.CTkLabel(src_card, text="", text_color=MUTED, font=ctk.CTkFont(size=11))

    import_url_entry = ctk.CTkEntry(
        src_card,
        placeholder_text="Import list from URL — paste a .toml source list URL here"
    )
    import_url_entry.pack(fill="x", padx=16, pady=(0, 4))

    def do_import():
        url = import_url_entry.get().strip()
        if not url:
            import_lbl.configure(text="⚠ Enter a URL first.", text_color=RED)
            return
        import_lbl.configure(text="Downloading source list…", text_color=MUTED)
        def _task():
            added, err = import_source_list(url)
            if err:
                import_lbl.configure(text=f"⚠ {err}", text_color=RED)
            else:
                import_lbl.configure(text=f"✅ {added} new source(s) added.", text_color="#4ade80")
                ctx.switch_tab_fn("update")
        threading.Thread(target=_task, daemon=True).start()

    ctk.CTkButton(
        src_card, text="⬇  Import List",
        fg_color=BORDER, text_color=TEXT, hover_color=ACCENT, height=28,
        command=do_import
    ).pack(anchor="w", padx=16, pady=(0, 4))
    import_lbl.pack(anchor="w", padx=16, pady=(0, 12))

    name_entry = ctk.CTkEntry(add_panel, placeholder_text="Source name (e.g. My Server)")
    name_entry.pack(fill="x", pady=3)
    url_entry = ctk.CTkEntry(add_panel, placeholder_text="URL — GitHub release API or custom JSON endpoint")
    url_entry.pack(fill="x", pady=3)
    type_var = ctk.StringVar(value="github_release")
    ctk.CTkOptionMenu(
        add_panel, values=["github_release", "custom_json"], variable=type_var,
        fg_color=BORDER, button_color=BORDER, button_hover_color=ACCENT,
        dropdown_fg_color=SURFACE, text_color=TEXT
    ).pack(fill="x", pady=3)

    def save_new_source():
        n, u, t = name_entry.get().strip(), url_entry.get().strip(), type_var.get()
        if n and u:
            add_source(n, u, t)
            ctx.switch_tab_fn("update")

    ctk.CTkButton(
        add_panel, text="Save Source", fg_color=ACCENT,
        text_color="#000", hover_color=ACCENT, height=30,
        command=save_new_source
    ).pack(anchor="e", pady=(6, 0))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2: Check & Download Updates
    # ══════════════════════════════════════════════════════════════════════════
    upd_card = _card(container, "⬆  Check & Install Updates")

    curr_tray_v = get_tray_version()
    curr_core_v = get_current_version()
    
    versions_frame = ctk.CTkFrame(upd_card, fg_color="transparent")
    versions_frame.pack(fill="x", padx=16, pady=(0, 8))
    
    ctk.CTkLabel(versions_frame, text=f"• Hecos Core:", text_color=MUTED, font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w", padx=(0, 10))
    ctk.CTkLabel(versions_frame, text=f"v{curr_core_v}", text_color=TEXT, font=ctk.CTkFont(size=12)).grid(row=0, column=1, sticky="w")
    
    ctk.CTkLabel(versions_frame, text=f"• Hecos Tray:", text_color=MUTED, font=ctk.CTkFont(size=12, weight="bold")).grid(row=1, column=0, sticky="w", padx=(0, 10))
    ctk.CTkLabel(versions_frame, text=f"v{curr_tray_v}", text_color=TEXT, font=ctk.CTkFont(size=12)).grid(row=1, column=1, sticky="w")
    
    ctk.CTkLabel(versions_frame, text=f"• Tray Dashboard:", text_color=MUTED, font=ctk.CTkFont(size=12, weight="bold")).grid(row=2, column=0, sticky="w", padx=(0, 10))
    ctk.CTkLabel(versions_frame, text=f"v{curr_tray_v}", text_color=TEXT, font=ctk.CTkFont(size=12)).grid(row=2, column=1, sticky="w")

    status_lbl = ctk.CTkLabel(upd_card, text="", text_color=TEXT, font=ctk.CTkFont(size=11))
    status_lbl.pack(anchor="w", padx=16)

    progress_bar = ctk.CTkProgressBar(upd_card, fg_color=BORDER, progress_color=ACCENT)
    progress_bar.set(0)

    action_btn = ctk.CTkButton(
        upd_card, text="Check for Updates",
        fg_color=ACCENT, text_color="#000", hover_color=ACCENT, height=34
    )
    action_btn.pack(anchor="w", padx=16, pady=(10, 14))

    _dl_files = {}

    def do_check():
        src = src_var.get()
        if not src or src == "(No sources configured)":
            status_lbl.configure(
                text="⚠ No update source selected. Add one above.", text_color=RED
            )
            return
        action_btn.configure(state="disabled", text="Checking…")
        status_lbl.configure(text="Contacting update server…", text_color=MUTED)

        def _task():
            res = check_for_updates()
            err = res.get("error")
            if err:
                status_lbl.configure(text=f"⚠ {err}", text_color=RED)
                action_btn.configure(state="normal", text="Check for Updates", command=do_check)
            elif res.get("update_available"):
                lv = res["latest_version"]
                status_lbl.configure(text=f"✅ Update available: v{lv}", text_color="#4ade80")
                action_btn.configure(
                    state="normal", text=f"Download v{lv}",
                    command=lambda: do_download(res["assets"])
                )
            else:
                status_lbl.configure(text="✓ You are on the latest version.", text_color="#4ade80")
                action_btn.configure(state="normal", text="Check for Updates", command=do_check)

        threading.Thread(target=_task, daemon=True).start()

    def do_download(assets):
        action_btn.configure(state="disabled", text="Downloading…")
        progress_bar.pack(fill="x", padx=16, pady=(0, 8))

        def _task():
            try:
                temp_dir = os.path.join(_ROOT, "bin", "update_temp")
                os.makedirs(temp_dir, exist_ok=True)

                target_assets = []
                for a in assets:
                    nl = a["name"].lower()
                    if sys.platform == "win32" and nl.endswith(".exe"):
                        target_assets.append(a)
                    elif sys.platform != "win32" and not nl.endswith(".exe"):
                        if any(k in nl for k in ("linux", "darwin", "mac")):
                            target_assets.append(a)

                if not target_assets:
                    status_lbl.configure(text="⚠ No compatible binaries found for this OS.", text_color=RED)
                    progress_bar.pack_forget()
                    action_btn.configure(state="normal", text="Check for Updates", command=do_check)
                    return

                for i, asset in enumerate(target_assets):
                    status_lbl.configure(
                        text=f"Downloading {asset['name']} ({i+1}/{len(target_assets)})…",
                        text_color=MUTED
                    )

                    def cb(done, total, bar=progress_bar):
                        if total > 0:
                            bar.set(done / total)

                    dest = os.path.join(temp_dir, asset["name"])
                    download_asset(asset["url"], dest, cb)
                    nl = asset["name"].lower()
                    if "tray" in nl:
                        _dl_files["tray"] = dest
                    elif "dashboard" in nl or "control" in nl:
                        _dl_files["dashboard"] = dest

                status_lbl.configure(text="✅ Download complete — ready to install.", text_color="#4ade80")
                progress_bar.pack_forget()
                action_btn.configure(
                    state="normal", text="Restart & Apply Update",
                    command=do_apply
                )
            except Exception as e:
                status_lbl.configure(text=f"⚠ {e}", text_color=RED)
                progress_bar.pack_forget()
                action_btn.configure(state="normal", text="Retry", command=lambda: do_download(assets))

        threading.Thread(target=_task, daemon=True).start()

    def do_apply():
        action_btn.configure(state="disabled", text="Applying…")
        status_lbl.configure(text="Launching updater and restarting…", text_color=MUTED)
        apply_update_and_restart(
            _dl_files.get("tray", ""),
            _dl_files.get("dashboard", "")
        )

    action_btn.configure(command=do_check)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3: Environment / Repair
    # ══════════════════════════════════════════════════════════════════════════
    env_card = _card(container, "🔧  Environment & Installation")

    ctk.CTkLabel(
        env_card,
        text=(
            "Use these tools if Hecos is misbehaving, if you moved the folder,\n"
            "or if you're setting up on a new machine."
        ),
        font=ctk.CTkFont(size=11), text_color=MUTED, justify="left"
    ).pack(anchor="w", padx=16, pady=(0, 10))

    env_status = ctk.CTkLabel(env_card, text="", text_color=MUTED, font=ctk.CTkFont(size=11))
    env_status.pack(anchor="w", padx=16)

    def _run_bat(bat_name, label):
        bat = os.path.join(_ROOT, "scripts", "windows", "setup", bat_name)
        if not os.path.exists(bat):
            env_status.configure(text=f"⚠ Script not found: {bat_name}", text_color=RED)
            return
        env_status.configure(text=f"Running {label}…", text_color=MUTED)
        try:
            subprocess.Popen(
                ["cmd.exe", "/c", bat],
                creationflags=0x00000010,  # CREATE_NEW_CONSOLE
                cwd=_ROOT
            )
        except Exception as e:
            env_status.configure(text=f"⚠ {e}", text_color=RED)

    def run_setup_wizard():
        env_status.configure(text="Opening Setup Wizard…", text_color=MUTED)
        wizard = os.path.join(_ROOT, "scripts", "windows", "setup", "HECOS_SETUP_CONSOLE_WIN.bat")
        if not os.path.exists(wizard):
            env_status.configure(text="⚠ Setup wizard script not found.", text_color=RED)
            return
        try:
            subprocess.Popen(
                ["cmd.exe", "/c", wizard],
                creationflags=0x00000010,
                cwd=_ROOT
            )
        except Exception as e:
            env_status.configure(text=f"⚠ {e}", text_color=RED)

    def run_install():
        env_status.configure(text="Opening Installer…", text_color=MUTED)
        installer = os.path.join(_ROOT, "scripts", "windows", "setup", "INSTALL_HECOS_WIN.bat")
        if not os.path.exists(installer):
            env_status.configure(text="⚠ Installer script not found.", text_color=RED)
            return
        try:
            subprocess.Popen(
                ["cmd.exe", "/c", installer],
                creationflags=0x00000010,
                cwd=_ROOT
            )
        except Exception as e:
            env_status.configure(text=f"⚠ {e}", text_color=RED)

    def run_pip_update():
        env_status.configure(text="Updating Python packages…", text_color=MUTED)
        python_candidates = [
            os.path.join(_ROOT, "python_env", "python.exe"),
            os.path.join(_ROOT, "venv", "Scripts", "python.exe"),
            sys.executable,
        ]
        python_cmd = next((p for p in python_candidates if os.path.exists(p)), sys.executable)
        req = os.path.join(_ROOT, "requirements.txt")

        def _task():
            try:
                cmd = [python_cmd, "-m", "pip", "install", "--upgrade"]
                if os.path.exists(req):
                    cmd += ["-r", req]
                else:
                    cmd += ["hecos"]
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=_ROOT)
                if result.returncode == 0:
                    env_status.configure(text="✅ Python packages updated.", text_color="#4ade80")
                else:
                    env_status.configure(text=f"⚠ pip error: {result.stderr[:120]}", text_color=RED)
            except Exception as e:
                env_status.configure(text=f"⚠ {e}", text_color=RED)

        threading.Thread(target=_task, daemon=True).start()

    btn_cfg = dict(height=32, corner_radius=8, font=ctk.CTkFont(size=11))

    buttons = ctk.CTkFrame(env_card, fg_color="transparent")
    buttons.pack(fill="x", padx=16, pady=(6, 14))
    buttons.columnconfigure((0, 1, 2), weight=1, uniform="btn")

    ctk.CTkButton(
        buttons, text="🔁  Update Python Packages",
        fg_color=BORDER, text_color=TEXT, hover_color=ACCENT,
        command=run_pip_update, **btn_cfg
    ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

    ctk.CTkButton(
        buttons, text="⚙  Run Setup Wizard",
        fg_color=BORDER, text_color=TEXT, hover_color=ACCENT,
        command=run_setup_wizard, **btn_cfg
    ).grid(row=0, column=1, padx=6, sticky="ew")

    ctk.CTkButton(
        buttons, text="📦  Full Re-Install",
        fg_color=BORDER, text_color=TEXT, hover_color=ACCENT,
        command=run_install, **btn_cfg
    ).grid(row=0, column=2, padx=(6, 0), sticky="ew")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4: Uninstall
    # ══════════════════════════════════════════════════════════════════════════
    uni_card = _card(container, "🗑  Uninstall & Cleanup")

    ctk.CTkLabel(
        uni_card,
        text=(
            "Use these tools to remove Hecos from your system."
        ),
        font=ctk.CTkFont(size=11), text_color=MUTED, justify="left"
    ).pack(anchor="w", padx=16, pady=(0, 10))

    uni_status = ctk.CTkLabel(uni_card, text="", text_color=MUTED, font=ctk.CTkFont(size=11))
    uni_status.pack(anchor="w", padx=16)

    def run_uninstall(mode):
        uni_status.configure(text=f"Opening Uninstaller ({mode})…", text_color=MUTED)
        uninstaller = os.path.join(_ROOT, "scripts", "windows", "setup", "UNINSTALL_HECOS_WIN.bat")
        if not os.path.exists(uninstaller):
            uni_status.configure(text="⚠ Uninstaller script not found.", text_color=RED)
            return
        try:
            subprocess.Popen(
                ["cmd.exe", "/c", uninstaller, mode],
                creationflags=0x00000010,
                cwd=_ROOT
            )
        except Exception as e:
            uni_status.configure(text=f"⚠ {e}", text_color=RED)

    uni_buttons = ctk.CTkFrame(uni_card, fg_color="transparent")
    uni_buttons.pack(fill="x", padx=16, pady=(6, 14))
    uni_buttons.columnconfigure((0, 1, 2), weight=1, uniform="ubtn")

    ctk.CTkButton(
        uni_buttons, text="Remove Core",
        fg_color=BORDER, text_color=TEXT, hover_color="#8b5cf6",
        command=lambda: run_uninstall("--core"), **btn_cfg
    ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

    ctk.CTkButton(
        uni_buttons, text="Remove Core + Deps",
        fg_color=BORDER, text_color=TEXT, hover_color="#f97316",
        command=lambda: run_uninstall("--deps"), **btn_cfg
    ).grid(row=0, column=1, padx=6, sticky="ew")

    ctk.CTkButton(
        uni_buttons, text="🔴 Full Nuke",
        fg_color="transparent", border_width=1, border_color=RED,
        text_color=RED, hover_color="#3a1a1a",
        command=lambda: run_uninstall("--full"), **btn_cfg
    ).grid(row=0, column=2, padx=(6, 0), sticky="ew")
