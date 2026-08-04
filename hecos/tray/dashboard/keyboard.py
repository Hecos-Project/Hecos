import customtkinter as ctk

class KeyboardNavigator:
    def __init__(self, app: ctk.CTk, sidebar: ctk.CTkFrame, content_frame: ctk.CTkFrame):
        self.app = app
        self.sidebar = sidebar
        self.content_frame = content_frame
        
        self.focusable_types = (
            ctk.CTkButton, ctk.CTkSwitch, ctk.CTkEntry, 
            ctk.CTkOptionMenu, ctk.CTkCheckBox, ctk.CTkSegmentedButton,
            ctk.CTkTextbox
        )
        
        # Strict virtual focus tracking
        self.current_widget = None
        
        # Track the last focused widget in each pane to restore it when switching panes
        self._last_sidebar_widget = None
        self._last_content_widget = None
        
        # Bind the global keys
        self.app.bind("<Up>", self._on_up)
        self.app.bind("<Down>", self._on_down)
        self.app.bind("<Left>", self._on_left)
        self.app.bind("<Right>", self._on_right)
        self.app.bind("<Return>", self._on_enter)
        self.app.bind("<space>", self._on_enter)
        
        # Hijack Tab to ensure it reaches all CTk widgets (which natively lack takefocus)
        self.app.bind("<Tab>", self._on_tab)
        self.app.bind("<Shift-Tab>", self._on_shift_tab)
        
        # Listen to all mouse clicks to keep our virtual focus in sync
        self.app.bind_all("<Button-1>", self._on_click_anywhere, add="+")
        
        self.app.after(300, lambda: self._focus_widget(self._get_widgets(self.sidebar)[0]))

    def _is_typing(self):
        # Allow native typing and text navigation
        if self.current_widget and isinstance(self.current_widget, (ctk.CTkEntry, ctk.CTkTextbox)):
            return True
        return False

    def _get_widgets(self, parent):
        """Recursively find all focusable CTk widgets in a parent frame."""
        found = []
        def _scan(w):
            if isinstance(w, self.focusable_types):
                if w.winfo_ismapped():
                    try:
                        if w.cget("state") == "normal":
                            found.append(w)
                    except Exception:
                        found.append(w)
            for child in w.winfo_children():
                _scan(child)
        _scan(parent)
        # Sort top-to-bottom based on screen coordinates
        found.sort(key=lambda x: x.winfo_rooty())
        return found

    def _get_all_widgets(self):
        """Returns sequential list: Sidebar first, then Content."""
        return self._get_widgets(self.sidebar) + self._get_widgets(self.content_frame)

    def _get_pane_of_widget(self, widget):
        if str(widget).startswith(str(self.sidebar)):
            return "sidebar"
        return "content"

    def _sync_focus_from_native(self):
        """Fallback to sync virtual focus from native Tk focus if possible."""
        current_tk = self.app.focus_get()
        if not current_tk:
            return
        tk_path = str(current_tk)
        for w in self._get_all_widgets():
            if tk_path.startswith(str(w)):
                self.current_widget = w
                pane = self._get_pane_of_widget(w)
                if pane == "sidebar":
                    self._last_sidebar_widget = w
                else:
                    self._last_content_widget = w
                break

    def _focus_widget(self, widget):
        if not widget: return
        self.current_widget = widget
        widget.focus_set()
        
        pane = self._get_pane_of_widget(widget)
        if pane == "sidebar":
            self._last_sidebar_widget = widget
            # Auto-switch tab if it's a main sidebar navigation button
            btn_text = widget.cget("text") if hasattr(widget, "cget") else ""
            if btn_text and btn_text not in ["Open Chat", "Restart Core"]:
                try:
                    cmd = widget.cget("command")
                    if cmd: cmd()
                except Exception:
                    pass
        else:
            self._last_content_widget = widget

    # ── MOUSE SYNC ─────────────────────────────────────────────────────────────
    def _on_click_anywhere(self, event):
        """If the user clicks a widget with the mouse, update our virtual pointer."""
        try:
            clicked_tk = event.widget
            tk_path = str(clicked_tk)
            for w in self._get_all_widgets():
                if tk_path.startswith(str(w)):
                    self.current_widget = w
                    pane = self._get_pane_of_widget(w)
                    if pane == "sidebar":
                        self._last_sidebar_widget = w
                    else:
                        self._last_content_widget = w
                    break
        except Exception:
            pass

    # ── TAB TRAVERSAL ──────────────────────────────────────────────────────────
    def _on_tab(self, event=None):
        all_w = self._get_all_widgets()
        if not all_w: return "break"
        
        if self.current_widget not in all_w:
            self._sync_focus_from_native()
            
        if self.current_widget in all_w:
            idx = all_w.index(self.current_widget)
            next_idx = (idx + 1) % len(all_w)
        else:
            next_idx = 0
            
        self._focus_widget(all_w[next_idx])
        return "break"

    def _on_shift_tab(self, event=None):
        all_w = self._get_all_widgets()
        if not all_w: return "break"
        
        if self.current_widget not in all_w:
            self._sync_focus_from_native()
            
        if self.current_widget in all_w:
            idx = all_w.index(self.current_widget)
            next_idx = (idx - 1) % len(all_w)
        else:
            next_idx = len(all_w) - 1
            
        self._focus_widget(all_w[next_idx])
        return "break"

    # ── 2D ARROW TRAVERSAL ─────────────────────────────────────────────────────
    def _move_vertical(self, direction):
        if self._is_typing(): return
        
        all_w = self._get_all_widgets()
        if self.current_widget not in all_w:
            self._sync_focus_from_native()
            
        if not self.current_widget:
            self._focus_widget(all_w[0] if all_w else None)
            return "break"
            
        pane = self._get_pane_of_widget(self.current_widget)
        pane_widgets = self._get_widgets(self.sidebar if pane == "sidebar" else self.content_frame)
        
        if self.current_widget in pane_widgets:
            idx = pane_widgets.index(self.current_widget)
            next_idx = (idx + direction) % len(pane_widgets)
            self._focus_widget(pane_widgets[next_idx])
        else:
            # Fallback if somehow lost
            self._focus_widget(pane_widgets[0] if pane_widgets else None)
            
        return "break"

    def _on_down(self, event=None): return self._move_vertical(1)
    def _on_up(self, event=None): return self._move_vertical(-1)

    def _on_right(self, event=None):
        if self._is_typing(): return
        if self.current_widget not in self._get_all_widgets():
            self._sync_focus_from_native()
            
        if self.current_widget and self._get_pane_of_widget(self.current_widget) == "sidebar":
            # Jump to content pane
            cw = self._get_widgets(self.content_frame)
            if cw:
                if self._last_content_widget in cw:
                    self._focus_widget(self._last_content_widget)
                else:
                    self._focus_widget(cw[0])
        return "break"

    def _on_left(self, event=None):
        if self._is_typing(): return
        if self.current_widget not in self._get_all_widgets():
            self._sync_focus_from_native()
            
        if self.current_widget and self._get_pane_of_widget(self.current_widget) == "content":
            # Jump to sidebar pane
            sw = self._get_widgets(self.sidebar)
            if sw:
                if self._last_sidebar_widget in sw:
                    self._focus_widget(self._last_sidebar_widget)
                else:
                    self._focus_widget(sw[0])
        return "break"

    def _on_enter(self, event=None):
        if self._is_typing(): return
        
        if self.current_widget not in self._get_all_widgets():
            self._sync_focus_from_native()
            
        curr = self.current_widget
        if curr:
            try:
                if isinstance(curr, ctk.CTkSwitch):
                    curr.toggle()
                    cmd = curr.cget("command")
                    if cmd: cmd()
                elif isinstance(curr, ctk.CTkButton):
                    cmd = curr.cget("command")
                    if cmd: cmd()
            except Exception:
                pass
        return "break"
