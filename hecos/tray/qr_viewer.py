try:
    import tkinter as tk
    from tkinter import messagebox, filedialog
except ImportError:
    tk = None
    messagebox = None
    filedialog = None

try:
    from PIL import ImageTk
except ImportError:
    ImageTk = None

def show_qr_popup(scheme: str, lan_ip: str, port: int):
    url = f"{scheme}://{lan_ip}:{port}/chat"
    if not tk or not ImageTk:
        print("[TRAY] Tkinter o PIL ImageTk non disponibile.")
        return
    try:
        import qrcode
    except ImportError:
        print("[TRAY] qrcode library not found. Install with: pip install qrcode[pil]")
        return

    root = tk.Tk()
    root.title("Hecos - Mobile Connection")
    root.geometry("350x480")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    bg_color = "#0d0e14"
    fg_color = "#ffffff"
    root.configure(bg=bg_color)

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img_qr_pil = qr.make_image(fill_color="black", back_color="white")

    tk.Label(root, text="SCAN TO CONNECT", font=("Consolas", 12, "bold"), bg=bg_color, fg="#00e676").pack(pady=(20, 5))
    tk.Label(root, text=f"URL: {url}", font=("Consolas", 8), bg=bg_color, fg="#aaaaaa", wraplength=300).pack(pady=5)

    preview_img = img_qr_pil.resize((250, 250))
    img_tk = ImageTk.PhotoImage(preview_img)
    panel = tk.Label(root, image=img_tk, bg="white", bd=0)
    panel.image = img_tk
    panel.pack(pady=10)

    def copy_url():
        root.clipboard_clear()
        root.clipboard_append(url)
        messagebox.showinfo("Copiato", "Indirizzo copiato negli appunti!")

    def save_qr():
        fpath = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")],
            initialfile="hecos_mobile_connect.png"
        )
        if fpath:
            img_qr_pil.save(fpath)
            messagebox.showinfo("Salvato", f"QR Code salvato in:\n{fpath}")

    btn_frame = tk.Frame(root, bg=bg_color)
    btn_frame.pack(pady=10)
    tk.Button(btn_frame, text="📋 Copy URL", command=copy_url, bg="#1e1f26", fg=fg_color, bd=0, padx=10, pady=5).pack(side="left", padx=5)
    tk.Button(btn_frame, text="💾 Save PNG", command=save_qr, bg="#1e1f26", fg=fg_color, bd=0, padx=10, pady=5).pack(side="left", padx=5)
    tk.Button(root, text="Close", command=root.destroy, bg="#333", fg=fg_color, bd=0, padx=20).pack(pady=10)
    
    # Needs to be brought to front then kept topmost
    root.lift()
    root.attributes('-topmost',True)
    root.after_idle(root.attributes,'-topmost',False)
    
    root.mainloop()
