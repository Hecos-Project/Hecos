import os
import sys

sys.path.insert(0, os.path.abspath('C:\\Zentra-Core'))
from zentra_bridge.webui.config_server import _HTML_PANEL

os.makedirs('C:\\Zentra-Core\\zentra_bridge\\webui\\web_config\\templates', exist_ok=True)
with open('C:\\Zentra-Core\\zentra_bridge\\webui\\web_config\\templates\\index.html', 'w', encoding='utf-8') as f:
    f.write(_HTML_PANEL)

print("HTML template successfully extracted!")
