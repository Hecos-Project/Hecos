"""
image_gen HPM plugin - root entry point.
The module_scanner looks for main.py at the plugin root.
We re-export everything from plugin/main.py so the scanner finds the tools object.
"""
from .plugin.main import tools, info, status
