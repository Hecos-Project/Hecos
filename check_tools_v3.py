import sys
import os
import json
sys.path.append(os.getcwd())

output_path = "debug_tools_check.json"

try:
    from core.system import plugin_loader
    from app.config import ConfigManager

    # Force a rescan
    cfg = ConfigManager().config
    skills = plugin_loader.update_capability_registry(config=cfg)

    tools = plugin_loader.get_tools_schema()
    
    data = {
        "skills_map_keys": list(skills.keys()),
        "tools_schema": tools,
        "loaded_plugins": list(plugin_loader._loaded_plugins.keys())
    }
    
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"DONE. Result in {output_path}")

except Exception as e:
    print(f"FAILED. Error: {str(e)}")
