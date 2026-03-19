#!/usr/bin/env python
"""
Avvio standalone dell'editor di configurazione.
Utilizzo: python config_tool.py
"""

from ui.config_editor.core import ConfigEditor

if __name__ == "__main__":
    editor = ConfigEditor()
    editor.run()