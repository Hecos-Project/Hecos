import os
import sys
import json

hecos_root = r"C:\Hecos"
if hecos_root not in sys.path:
    sys.path.insert(0, hecos_root)

from hecos.app.config import ConfigManager
cfg = ConfigManager()

from hecos.core.system.module_scanner import update_capability_registry
update_capability_registry(cfg.config, debug_log=True)

from hecos.core.system.module_state import get_plugin_module
proxy = get_plugin_module("IMAGE_GEN")

if proxy:
    print("Proxy found:", type(proxy))
    # Test generation (dummy prompt to trigger the plugin)
    print("Sending generate_image...")
    result = proxy.tools.generate_image(prompt="A futuristic city")
    print("Result:")
    print(result)
else:
    print("Proxy NOT found!")
