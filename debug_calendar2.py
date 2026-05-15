import sys
import logging
from hecos.app.config import ConfigManager

def main():
    cm = ConfigManager()
    
    with open("c:\\Hecos\\debug_out.txt", "w") as f:
        f.write("Initial day_colors: " + str(cm.config.get("extensions", {}).get("calendar", {}).get("day_colors")) + "\n")
        
        cm.update_config({
            "extensions": {
                "calendar": {
                    "day_colors": ["transparent", "transparent", "transparent", "transparent", "transparent", "transparent", "transparent"],
                    "bg_color": "",
                    "bg_image": ""
                }
            }
        })
        
        f.write("After update, in memory: " + str(cm.config.get("extensions", {}).get("calendar", {}).get("day_colors")) + "\n")

if __name__ == "__main__":
    main()
