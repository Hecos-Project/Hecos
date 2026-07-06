"""
MODULE: Lists Widget
DESCRIPTION: WebUI sidebar widget for the Lists plugin.
"""

from hecos.core.logging import logger

try:
    from hecos.core.i18n import translator
except ImportError:
    class _DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = _DummyTranslator()


class ListsWidgetExtension:
    def __init__(self):
        self.id = "lists_widget"
        self._cfg = None

    def render_sidebar_widget(self) -> str:
        """Returns the HTML for the Control Room sidebar widget."""
        from flask import render_template
        from hecos.plugins.lists import store
        
        try:
            lists = store.get_lists(include_archived=False)
            return render_template("lists_widget_widget.html", lists=lists, t=translator.t)
        except Exception as e:
            logger.error(f"[LISTS_WIDGET] render error: {e}")
            return f"<div class='widget-error'>Lists Widget Error</div>"


# ── Singleton & Hooks ──────────────────────────────────────────────────────────
extension = ListsWidgetExtension()

def on_load(config: dict):
    extension._cfg = config
    logger.debug("LISTS_WIDGET", "Widget loaded.")

def render_sidebar_widget() -> str:
    return extension.render_sidebar_widget()
