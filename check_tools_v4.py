import sys
import os
import json
sys.path.append(os.getcwd())

output_path = os.path.join(os.getcwd(), "debug_tools_check.json")

try:
    from core.system import plugin_loader
    from app.config import ConfigManager

    cfg_mgr = ConfigManager()
    cfg = cfg_mgr.config
    
    # Force rescan
    skills = plugin_loader.update_capability_registry(config=cfg)

    tools = plugin_loader.get_tools_schema()
    
    data = {
        "skills_map_keys": list(skills.keys()),
        "tools_schema": tools,
        "loaded_plugins": list(plugin_loader._loaded_plugins.keys())
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"SUCCESS: {output_path}")

except Exception as e:
    with open("debug_error.txt", "w") as f:
        f.write(str(e))
    print(f"FAILED: {str(e)}")
