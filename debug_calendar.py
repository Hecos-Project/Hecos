import sys
import logging
from hecos.app.config import ConfigManager

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

def main():
    cm = ConfigManager()
    print("Initial day_colors:", cm.config.get("extensions", {}).get("calendar", {}).get("day_colors"))
    cm.update_config({
        "extensions": {
            "calendar": {
                "day_colors": ["transparent", "transparent", "transparent", "transparent", "transparent", "transparent", "transparent"],
                "bg_color": "",
                "bg_image": ""
            }
        }
    })
    print("After update, in memory:", cm.config.get("extensions", {}).get("calendar", {}).get("day_colors"))

    # Reload from disk to verify persistence
    cm2 = ConfigManager()
    print("After reload, day_colors:", cm2.config.get("extensions", {}).get("calendar", {}).get("day_colors"))

if __name__ == "__main__":
    main()
