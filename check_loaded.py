import sys
import os
import json
sys.path.append(os.getcwd())

output_path = "check_loaded.json"

try:
    from core.system import plugin_loader
    from app.config import ConfigManager

    # We DON'T call update_capability_registry because we want to see 
    # if it's ALREADY loaded in a clean environment (simulating startup)
    
    # Actually, to simulate startup, we can just call it once
    cfg = ConfigManager().config
    plugin_loader.update_capability_registry(config=cfg)

    data = {
        "loaded_plugins": list(plugin_loader._loaded_plugins.keys()),
        "has_image_gen": "IMAGE_GEN" in plugin_loader._loaded_plugins
    }
    
    if data["has_image_gen"]:
        mod = plugin_loader._loaded_plugins["IMAGE_GEN"]
        data["has_tools"] = hasattr(mod, "tools")
        if data["has_tools"]:
            data["methods"] = [n for n,m in vars(mod.tools.__class__).items() if not n.startswith("_")]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"SUCCESS: {output_path}")

except Exception as e:
    print(f"FAILED: {str(e)}")
