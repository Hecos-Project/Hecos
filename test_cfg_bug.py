import sys
import os
import json
from zentra.config.schemas.system_schema import SystemConfig
from zentra.app.config import ConfigManager

os.environ["ZENTRA_DIR"] = os.path.join(os.getcwd(), "zentra")
cfg = ConfigManager()
print(f"Current active personality: {cfg.get('ai', 'active_personality')}")

print("Attempting to update via update_config()...")
res = cfg.update_config({"ai": {"active_personality": "Motoko Kusanagi.yaml"}})
print(f"Update Result: {res}")
print(f"New active personality: {cfg.get('ai', 'active_personality')}")
