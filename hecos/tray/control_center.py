"""
hecos/tray/control_center.py
Hecos Tray Dashboard — CustomTkinter Edition (replaces Flet)
Ultra-light: opens in < 400ms, no Flutter/Dart runtime required.

Note: This file is now a lightweight facade. 
The actual dashboard code has been split into hecos/tray/dashboard/ for modularity.
"""

from hecos.tray.dashboard.core import show_control_center, run_dashboard

if __name__ == "__main__":
    run_dashboard()
