import customtkinter as ctk
import time
import threading

from hecos.tray.dashboard.theme import BG, CARD, MUTED, ACCENT, RED, AMBER, TEXT
from hecos.tray.dashboard.ui import make_card, title, subtitle
from hecos.tray.system_utils import get_hecos_processes, kill_all_hecos_processes, kill_duplicate_hecos_processes

def build_processes(ctx):
    outer = ctk.CTkFrame(ctx.content_frame, fg_color="transparent", corner_radius=0)
    outer.pack(fill="both", expand=True, padx=20, pady=20)
    ctx.append_widget(outer)

    title(ctx, outer, "Process Manager")
    subtitle(ctx, outer, "Monitor and manage Hecos subsystems.")

    card = make_card(outer)
    card.pack(fill="both", expand=True, pady=(10, 0))

    top_bar = ctk.CTkFrame(card, fg_color="transparent")
    top_bar.pack(fill="x", padx=15, pady=(15, 0))

    status_lbl = ctk.CTkLabel(top_bar, text="Scanning processes...", fg_color="transparent", font=ctk.CTkFont(size=12, weight="bold"))
    status_lbl.pack(side="left")

    def on_kill_all():
        import tkinter as tk
        from tkinter import messagebox
        if tk.messagebox.askyesno("Confirm", "Kill all Hecos background processes?"):
            killed = kill_all_hecos_processes()
            tk.messagebox.showinfo("Result", f"Killed {killed} processes.")
            ctx.rebuild_tab("processes")

    def on_kill_dupes():
        import tkinter as tk
        from tkinter import messagebox
        killed = kill_duplicate_hecos_processes()
        tk.messagebox.showinfo("Result", f"Killed {killed} duplicate processes.")
        ctx.rebuild_tab("processes")

    btn_dupes = ctk.CTkButton(top_bar, text="Kill Duplicates", fg_color=AMBER, text_color="#000", hover_color="#d97706", width=110, command=on_kill_dupes)
    btn_dupes.pack(side="right", padx=(10,0))
    btn_all = ctk.CTkButton(top_bar, text="Kill All", fg_color=RED, text_color="#fff", hover_color="#b91c1c", width=100, command=on_kill_all)
    btn_all.pack(side="right")

    txt_frame = ctk.CTkFrame(card, fg_color="transparent", corner_radius=0)
    txt_frame.pack(fill="both", expand=True, padx=10, pady=15)
    
    textbox = ctk.CTkTextbox(txt_frame, fg_color=BG, text_color=TEXT, font=ctk.CTkFont("Consolas", size=13), wrap="none")
    textbox.pack(fill="both", expand=True)

    def _refresh_list():
        if ctx.active_tab["key"] != "processes":
            return
        try:
            procs = get_hecos_processes()
            status_lbl.configure(text=f"Total Hecos Processes: {len(procs)}", text_color=ACCENT)
            
            textbox.configure(state="normal")
            textbox.delete("1.0", "end")
            
            if not procs:
                textbox.insert("end", "No processes found.")
            else:
                for p in procs:
                    cmd_short = p['cmd'].replace('\n', ' ')
                    if len(cmd_short) > 130:
                        cmd_short = cmd_short[:127] + "..."
                    line = f"{p['type']:<20} PID: {p['pid']:<8} {cmd_short}\n"
                    textbox.insert("end", line)
            
            textbox.configure(state="disabled")
        except Exception as e:
            status_lbl.configure(text=f"Error scanning: {e}", text_color=RED)

    _refresh_list()
    
    def _loop():
        while ctx.active_tab["key"] == "processes":
            time.sleep(3)
            if ctx.active_tab["key"] == "processes":
                ctx.app.after(0, _refresh_list)
    threading.Thread(target=_loop, daemon=True).start()
