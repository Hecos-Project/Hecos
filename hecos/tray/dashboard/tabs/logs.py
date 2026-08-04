import os
import time
import threading
import webbrowser
import customtkinter as ctk
import tkinter as tk
import re as _re

from hecos.tray.config import load_settings, save_settings
from hecos.tray.dashboard.theme import CARD, TEXT, MUTED, ACCENT, ACCENT2, RED, AMBER, SURFACE, BORDER
from hecos.tray.dashboard.ui import title, subtitle

def build_logs(ctx):
    # Outer container
    outer = ctk.CTkFrame(ctx.content_frame, fg_color="transparent", corner_radius=0)
    outer.pack(fill="both", expand=True, padx=20, pady=20)
    ctx.append_widget(outer)

    title(ctx, outer, "Live Logs")
    subtitle(ctx, outer, "Read directly from disk — works even when the WebUI is offline.")

    logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs"))

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

    # Tags for coloring — severity levels
    for kw, col in SEV_COLORS.items():
        log_text.tag_configure(kw, foreground=col)
    log_text.tag_configure("MUTED", foreground=MUTED)
    log_text.tag_configure("URL", foreground=ACCENT, underline=True)

    # Tags for Source Tagging (Full Color mode)
    TAG_COLORS_MAP = {
        "CORE":   "#4dabf7",  # Bright Blue
        "DAEMON": "#b197fc",  # Purple
        "WEBUI":  "#69db7c",  # Green
        "PLUGIN": "#ffa94d",  # Orange
    }
    for tag_key, tag_col in TAG_COLORS_MAP.items():
        log_text.tag_configure(f"TAG_{tag_key}", foreground=tag_col, font=("Consolas", font_size[0], "bold"))

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

    full_color       = [load_settings().get("full_color_logs", True)]
    _last_size       = [0]
    _last_line_count = [0]   # total lines tracked in the background thread
    
    url_pattern = _re.compile(r'(https?://[^\s\'"<>]+)')
    tag_pattern  = _re.compile(r'(\[(?:CORE|PLUGIN|WEBUI|DAEMON)[^\]]*\])', _re.IGNORECASE)

    def _get_source_tag(txt):
        t = txt.upper()
        if t.startswith("[CORE"):   return "TAG_CORE"
        if t.startswith("[PLUGIN"): return "TAG_PLUGIN"
        if t.startswith("[WEBUI"):  return "TAG_WEBUI"
        if t.startswith("[DAEMON"): return "TAG_DAEMON"
        return None

    def _parse_lines(lines):
        segments_out = []
        fc = full_color[0]
        for line in lines:
            stripped = line.rstrip()
            col_tag = "MUTED"
            u = stripped.upper()
            for kw in ("ERROR", "CRITICAL", "WARNING", "INFO", "DEBUG"):
                if kw in u:
                    col_tag = kw
                    break
            if fc and col_tag in ("INFO", "DEBUG", "MUTED"):
                for seg in url_pattern.split(stripped):
                    if url_pattern.match(seg):
                        segments_out.append((seg, ("URL", col_tag)))
                    else:
                        for sub in tag_pattern.split(seg):
                            src_tag = _get_source_tag(sub)
                            if src_tag:
                                segments_out.append((sub, (src_tag, col_tag)))
                            else:
                                segments_out.append((sub, col_tag))
            else:
                for p in url_pattern.split(stripped):
                    if url_pattern.match(p):
                        segments_out.append((p, ("URL", col_tag)))
                    else:
                        segments_out.append((p, col_tag))
            segments_out.append(("\n", col_tag))
        return segments_out

    def _full_reload_on_main(segments, total, tail_len):
        log_text.configure(state="normal")
        log_text.delete("1.0", "end")
        for text, tag in segments:
            log_text.insert("end", text, tag)
        log_text.configure(state="disabled")
        log_text.see("end")
        lines_lbl.configure(text=f"{total} lines — showing last {tail_len}")

    def _do_full_reload(path):
        try:
            sz = os.path.getsize(path)
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            tail = all_lines[-400:] if len(all_lines) > 400 else all_lines
            _last_size[0] = sz
            _last_line_count[0] = len(all_lines)
            segments = _parse_lines(tail)
            ctx.app.after(0, _full_reload_on_main, segments, len(all_lines), len(tail))
        except Exception as ex:
            ctx.app.after(0, lambda: (
                log_text.configure(state="normal"),
                log_text.delete("1.0", "end"),
                log_text.insert("end", f"Error reading log: {ex}"),
                log_text.configure(state="disabled")
            ))

    def _load(auto=False):
        fname = file_var.get()
        if not fname or fname == "(no logs)": return
        path = os.path.join(logs_dir, fname)
        if not os.path.exists(path): return
        threading.Thread(target=_do_full_reload, args=(path,), daemon=True).start()

    def _on_file_change(choice):
        _last_size[0] = 0
        _last_line_count[0] = 0
        _load()

    file_dd.configure(command=_on_file_change)

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

    def _toggle_full_color():
        full_color[0] = not full_color[0]
        s = load_settings()
        s["full_color_logs"] = full_color[0]
        save_settings(s)
        btn_color.configure(
            text="🎨" if full_color[0] else "⬜",
            text_color=ACCENT if full_color[0] else MUTED
        )
        _last_size[0] = 0
        _last_line_count[0] = 0
        _load()

    btn_color = ctk.CTkButton(
        btn_row, text="🎨" if full_color[0] else "⬜",
        width=34, fg_color=SURFACE,
        text_color=ACCENT if full_color[0] else MUTED,
        hover_color=BORDER, corner_radius=6,
        command=_toggle_full_color
    )
    btn_color.pack(side="left", padx=2)

    ctk.CTkButton(btn_row, text="A-", width=34, fg_color=SURFACE, text_color=TEXT,
                  hover_color=BORDER, corner_radius=6,
                  command=lambda: _zoom(-2)).pack(side="left", padx=2)
    ctk.CTkButton(btn_row, text="A+", width=34, fg_color=SURFACE, text_color=TEXT,
                  hover_color=BORDER, corner_radius=6,
                  command=lambda: _zoom(2)).pack(side="left", padx=2)
    ctk.CTkButton(btn_row, text="↻", width=34, fg_color=SURFACE, text_color=ACCENT,
                  hover_color=BORDER, corner_radius=6,
                  command=lambda: (_last_size.__setitem__(0, 0), _last_line_count.__setitem__(0, 0), _load())).pack(side="left", padx=2)

    _load()

    def _auto_refresh():
        while ctx.active_tab["key"] == "logs":
            time.sleep(0.5)
            if ctx.active_tab["key"] != "logs" or is_paused[0]:
                continue
            fname = file_var.get()
            if not fname or fname == "(no logs)":
                continue
            path = os.path.join(logs_dir, fname)
            try:
                sz = os.path.getsize(path)
                if sz == _last_size[0]:
                    continue
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    all_lines = f.readlines()
                total = len(all_lines)
                already = _last_line_count[0]
                if total < already:
                    _last_size[0] = 0
                    _last_line_count[0] = 0
                    ctx.app.after(0, _load)
                    continue
                new_lines = all_lines[already:]
                if not new_lines:
                    _last_size[0] = sz
                    continue
                segments = _parse_lines(new_lines)
                _last_size[0] = sz
                _last_line_count[0] = total
                def _push(segs=segments, tot=total, nl=len(new_lines)):
                    at_bottom = log_text.yview()[1] >= 0.97
                    log_text.configure(state="normal")
                    for text, tag in segs:
                        log_text.insert("end", text, tag)
                    log_text.configure(state="disabled")
                    if at_bottom:
                        log_text.see("end")
                    lines_lbl.configure(text=f"{tot} lines (+{nl})")
                ctx.app.after(0, _push)
            except Exception:
                pass

    threading.Thread(target=_auto_refresh, daemon=True).start()
