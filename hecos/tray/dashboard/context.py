import customtkinter as ctk

class DashboardContext:
    """
    Holds shared state and dependencies for the Hecos Tray Dashboard.
    Passed to UI components and Tab builders to avoid global variables.
    """
    def __init__(self, app: ctk.CTk, content_frame: ctk.CTkFrame, content_widgets: list,
                 active_tab: dict, rebuild_tab_fn, switch_tab_fn):
        self.app = app
        self.content_frame = content_frame
        self.content_widgets = content_widgets
        self.active_tab = active_tab
        self.rebuild_tab = rebuild_tab_fn
        self.switch_tab = switch_tab_fn

    def append_widget(self, widget):
        """Track a widget so it gets destroyed on tab switch."""
        self.content_widgets.append(widget)

    def extend_widgets(self, widgets):
        """Track multiple widgets."""
        self.content_widgets.extend(widgets)
