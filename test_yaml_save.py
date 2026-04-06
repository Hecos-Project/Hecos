import sys
from app.config import ConfigManager

try:
    cfg = ConfigManager()
    cfg.save_config()
    print("Config saved successfully.")
except Exception as e:
    print(f"Error: {e}")
