import customtkinter as ctk
import threading
from hecos.tray.dashboard.theme import CARD, TEXT, MUTED, ACCENT, RED, GREEN, AMBER, BORDER, SURFACE
from hecos.tray.dashboard.ui import title, subtitle
from hecos.tray.network_utils import get_scheme, get_lan_ip, get_public_ip, check_wan_port
from hecos.tray.config import HECOS_PORT

def build_mobile(ctx):
    sc = ctk.CTkScrollableFrame(ctx.content_frame, fg_color="transparent", corner_radius=0)
    sc.pack(fill="both", expand=True, padx=20, pady=20)
    ctx.append_widget(sc)

    title(ctx, sc, "Remote Access")
    subtitle(ctx, sc, "Click a connection to preview its QR code. Drag or right-click the QR to copy/save it.")

    scheme   = get_scheme()
    lan_ip   = get_lan_ip()
    url_local = f"{scheme}://127.0.0.1:{HECOS_PORT}/chat"
    url_lan   = f"{scheme}://{lan_ip}:{HECOS_PORT}/chat"

    # State
    _state = {
        "active_key": "lan",   # which row is selected
        "public_ip": None,
        "url_wan": None,
        "qr_pil": None,        # current PIL image for drag-save
    }

    # ── QR helpers ────────────────────────────────────────────────────────
    def _make_qr_pil(url: str, fill=ACCENT, back=CARD):
        import qrcode
        qr = qrcode.QRCode(box_size=6, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color=fill, back_color=back)
        return img.convert("RGB")

    def _pil_to_ctk(pil_img, size=190):
        ctk_img = ctk.CTkImage(
            light_image=pil_img, dark_image=pil_img,
            size=(size, size)
        )
        return ctk_img

    # ── QR Card ───────────────────────────────────────────────────────────
    qr_outer = ctk.CTkFrame(sc, fg_color=CARD, corner_radius=12)
    qr_outer.pack(pady=(0, 10))

    qr_label = ctk.CTkLabel(qr_outer, text="", image=None)
    qr_label.pack(padx=22, pady=16)

    qr_hint = ctk.CTkLabel(
        qr_outer,
        text="Right-click to copy • Drag to save",
        fg_color="transparent",
        font=ctk.CTkFont(size=9), text_color=MUTED
    )
    qr_hint.pack(pady=(0, 10))

    # ── Drag & Copy logic (uses tkinter canvas trick) ─────────────────────
    _drag_state = {}

    def _on_qr_right_click(event):
        """Copy QR image to clipboard as PNG bytes (Windows only via win32clipboard)."""
        if _state["qr_pil"] is None:
            return
        try:
            import io, win32clipboard, win32con
            buf = io.BytesIO()
            _state["qr_pil"].save(buf, format="BMP")
            bmp_data = buf.getvalue()[14:]   # strip BMP file header
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_DIB, bmp_data)
            win32clipboard.CloseClipboard()
            qr_hint.configure(text="✅ Copied to clipboard!", text_color=GREEN)
            ctx.app.after(2000, lambda: qr_hint.configure(
                text="Right-click to copy • Drag to save", text_color=MUTED))
        except ImportError:
            # Fallback: save to temp file and notify user
            import tempfile
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            _state["qr_pil"].save(tmp.name)
            tmp.close()
            qr_hint.configure(text=f"Saved to {tmp.name}", text_color=AMBER)
            ctx.app.after(3000, lambda: qr_hint.configure(
                text="Right-click to copy • Drag to save", text_color=MUTED))
        except Exception as e:
            qr_hint.configure(text=f"Error: {e}", text_color=RED)
            ctx.app.after(2000, lambda: qr_hint.configure(
                text="Right-click to copy • Drag to save", text_color=MUTED))

    def _on_drag_start(event):
        _drag_state["x"] = event.x
        _drag_state["y"] = event.y

    def _on_drag_motion(event):
        dx = abs(event.x - _drag_state.get("x", event.x))
        dy = abs(event.y - _drag_state.get("y", event.y))
        if dx > 5 or dy > 5:
            qr_hint.configure(text="📁 Release to save QR as PNG…", text_color=ACCENT)

    def _on_drag_release(event):
        if _state["qr_pil"] is None:
            return
        try:
            import tkinter.filedialog as fd
            path = fd.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG Image", "*.png")],
                initialfile="hecos_qr.png",
                title="Save QR Code"
            )
            if path:
                _state["qr_pil"].save(path)
                qr_hint.configure(text=f"✅ Saved!", text_color=GREEN)
                ctx.app.after(2000, lambda: qr_hint.configure(
                    text="Right-click to copy • Drag to save", text_color=MUTED))
            else:
                qr_hint.configure(text="Right-click to copy • Drag to save", text_color=MUTED)
        except Exception as ex:
            qr_hint.configure(text=f"Error: {ex}", text_color=RED)
            ctx.app.after(2000, lambda: qr_hint.configure(
                text="Right-click to copy • Drag to save", text_color=MUTED))

    qr_label.bind("<Button-3>", _on_qr_right_click)
    qr_label.bind("<ButtonPress-1>", _on_drag_start)
    qr_label.bind("<B1-Motion>", _on_drag_motion)
    qr_label.bind("<ButtonRelease-1>", _on_drag_release)

    # ── Update QR display ─────────────────────────────────────────────────
    def _show_qr(url: str, placeholder: bool = False):
        if placeholder:
            qr_label.configure(image=None, text="⏳ Detecting WAN IP…",
                               font=ctk.CTkFont(size=12), text_color=MUTED)
            _state["qr_pil"] = None
            return
        try:
            pil = _make_qr_pil(url)
            ctk_img = _pil_to_ctk(pil)
            qr_label.configure(image=ctk_img, text="")
            _state["qr_pil"] = pil
        except Exception as e:
            qr_label.configure(image=None,
                               text=f"QR unavailable\n(pip install qrcode pillow)\n{e}",
                               font=ctk.CTkFont(size=9), text_color=MUTED)
            _state["qr_pil"] = None

    # ── Connection rows ───────────────────────────────────────────────────
    _row_frames = {}

    LINKS = [
        ("local", "🖥  Localhost",     url_local, None),
        ("lan",   "📡  LAN",           url_lan,   None),
        ("wan",   "🌐  Remote (WAN)",  None,      None),   # URL filled later
    ]

    conn_section = ctk.CTkFrame(sc, fg_color="transparent")
    conn_section.pack(fill="x", pady=(0, 4))

    def _select_row(key: str):
        url = _state.get(f"url_{key}") or {
            "local": url_local, "lan": url_lan
        }.get(key)

        for k, rf in _row_frames.items():
            rf.configure(border_color=ACCENT if k == key else CARD)

        _state["active_key"] = key

        if key == "wan" and _state["url_wan"] is None:
            _show_qr("", placeholder=True)
        elif url:
            _show_qr(url)

    for key, label, url, _ in LINKS:
        # store static URLs
        if key != "wan":
            _state[f"url_{key}"] = url

        row = ctk.CTkFrame(conn_section, fg_color=CARD, corner_radius=10,
                           cursor="hand2", border_width=2, border_color=CARD)
        row.pack(fill="x", pady=3)
        _row_frames[key] = row

        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(side="left", fill="both", expand=True, padx=14, pady=9)

        lbl_title = ctk.CTkLabel(inner, text=label, fg_color="transparent",
                                 font=ctk.CTkFont(size=12, weight="bold"),
                                 text_color=TEXT, anchor="w")
        lbl_title.pack(anchor="w")

        # URL sub-label (dynamic for WAN)
        url_text = url if url else "Detecting…"
        lbl_url = ctk.CTkLabel(inner, text=url_text, fg_color="transparent",
                               font=ctk.CTkFont(size=10), text_color=MUTED, anchor="w")
        lbl_url.pack(anchor="w")

        # Copy button
        copy_btn = ctk.CTkButton(
            row, text="📋", width=32, fg_color="transparent",
            text_color=MUTED, hover_color=BORDER, corner_radius=6
        )
        copy_btn.pack(side="right", padx=8)

        # Status badge (WAN only)
        if key == "wan":
            wan_badge = ctk.CTkLabel(row, text="  ⏳  ", fg_color="transparent", font=ctk.CTkFont(size=11),
                                     text_color=MUTED)
            wan_badge.pack(side="right", padx=(0, 4))
            _state["wan_badge"] = wan_badge
            _state["wan_url_label"] = lbl_url
            _state["wan_copy_btn"] = copy_btn
            copy_btn.configure(state="disabled")
        else:
            v = url
            copy_btn.configure(command=lambda v=v: ctx.app.clipboard_clear() or ctx.app.clipboard_append(v))

        # Bind click on the whole row
        def _make_click(k=key):
            return lambda e: _select_row(k)

        click_fn = _make_click()
        for widget in (row, inner, lbl_title, lbl_url):
            widget.bind("<Button-1>", click_fn)

    # ── WAN Port Check banner ─────────────────────────────────────────────
    port_card = ctk.CTkFrame(sc, fg_color=SURFACE, corner_radius=10, border_width=1,
                             border_color=BORDER)
    port_card.pack(fill="x", pady=(8, 0))

    port_header = ctk.CTkFrame(port_card, fg_color="transparent")
    port_header.pack(fill="x", padx=14, pady=(10, 4))
    ctk.CTkLabel(port_header, text=f"◉  Port {HECOS_PORT} WAN Reachability", fg_color="transparent",
                 font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT,
                 anchor="w").pack(side="left")

    port_status_lbl = ctk.CTkLabel(port_header, text="Checking…", fg_color="transparent",
                                   font=ctk.CTkFont(size=11), text_color=MUTED)
    port_status_lbl.pack(side="right")

    port_detail_lbl = ctk.CTkLabel(port_card, text="", fg_color="transparent",
                                   font=ctk.CTkFont(size=9), text_color=MUTED,
                                   wraplength=420, justify="left")
    port_detail_lbl.pack(anchor="w", padx=14, pady=(0, 10))

    recheck_btn = ctk.CTkButton(
        port_card, text="↻ Re-check", fg_color="transparent", text_color=ACCENT,
        hover_color=BORDER, corner_radius=6, font=ctk.CTkFont(size=10), width=90
    )
    recheck_btn.pack(anchor="e", padx=14, pady=(0, 8))

    # ── Background fetches ────────────────────────────────────────────────
    def _do_wan_fetch():
        """Fetch public IP, then kick off port check — all in background thread."""
        try:
            pub_ip = get_public_ip(timeout=5)
            wan_url = f"{scheme}://{pub_ip}:{HECOS_PORT}/chat"
            _state["public_ip"] = pub_ip
            _state["url_wan"] = wan_url

            def _on_ip(ip=pub_ip, url=wan_url):
                try:
                    _state["wan_url_label"].configure(text=url)
                    _state["wan_badge"].configure(text=" ✅ ", text_color=ACCENT)
                    _state["wan_copy_btn"].configure(
                        state="normal",
                        command=lambda: ctx.app.clipboard_clear() or ctx.app.clipboard_append(url)
                    )
                    if _state["active_key"] == "wan":
                        _show_qr(url)
                except Exception:
                    pass

            ctx.app.after(0, _on_ip)

            # Step 2: check if port is actually reachable
            _do_port_check(pub_ip)

        except Exception as exc:
            def _on_fail():
                try:
                    _state["wan_url_label"].configure(text="Unreachable")
                    _state["wan_badge"].configure(text=" 🔴 ", text_color=RED)
                    port_status_lbl.configure(text="No public IP", text_color=RED)
                    port_detail_lbl.configure(
                        text=f"Could not determine public IP: {exc}")
                except Exception:
                    pass
            ctx.app.after(0, _on_fail)

    def _do_port_check(ip: str):
        """Run port check and update the banner (called from background thread)."""
        result = check_wan_port(ip, port=HECOS_PORT, timeout=10)
        status = result.get("status", "error")
        method = result.get("method", "")
        detail = result.get("detail", "")

        if status == "open":
            badge_txt = "✅ Open"
            col = GREEN
        elif status == "closed":
            badge_txt = "🔴 Closed"
            col = RED
        elif status == "timeout":
            badge_txt = "⚠️ Timeout"
            col = AMBER
        else:
            badge_txt = "⚠️ Unknown"
            col = AMBER

        via = f" · via {method}" if method else ""

        def _upd_port():
            try:
                port_status_lbl.configure(text=badge_txt, text_color=col)
                port_detail_lbl.configure(
                    text=f"{detail}{via}",
                    text_color=MUTED if status in ("open", "closed") else AMBER
                )
            except Exception:
                pass

        ctx.app.after(0, _upd_port)

    def _start_all_checks():
        """(Re-)trigger all background checks."""
        port_status_lbl.configure(text="Checking…", text_color=MUTED)
        port_detail_lbl.configure(text="")
        _state["wan_url_label"].configure(text="Detecting…")
        _state["wan_badge"].configure(text=" ⏳ ", text_color=MUTED)
        _state["wan_copy_btn"].configure(state="disabled")
        threading.Thread(target=_do_wan_fetch, daemon=True).start()

    recheck_btn.configure(command=_start_all_checks)

    # ── Initial state: select LAN row + start background checks ──────────
    _select_row("lan")
    _start_all_checks()
