import sys
import os

# Add Hecos root to sys.path
hecos_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if hecos_root not in sys.path:
    sys.path.append(hecos_root)

try:
    from hecos.app.config import ConfigManager
    from hecos.config.schemas.system_schema import SystemConfig
except ImportError as e:
    print(f"FAILED: Import error: {e}")
    sys.exit(1)

def verify():
    print("--- VERIFICATION START ---")
    
    cfg_mgr = ConfigManager()
    
    # Check if new tags exist in schema
    print("Checking schema for new tags...")
    plugins_cfg = cfg_mgr.config.get("plugins", {})
    for tag in ["USER", "CALENDAR", "MEDIA_PLAYER"]:
        if tag in plugins_cfg:
            print(f"✅ Tag {tag} found in config.")
        else:
            print(f"❌ Tag {tag} MISSING from config!")
            
    # Check lazy_load persistence
    print("\nTesting persistence of lazy_load flag...")
    test_tag = "REMINDER"
    current_val = cfg_mgr.get_plugin_config(test_tag, "lazy_load")
    print(f"Current {test_tag} lazy_load: {current_val}")
    
    # Toggle and save
    new_val = not current_val
    print(f"Setting {test_tag} lazy_load to: {new_val}")
    cfg_mgr.set_plugin_config(test_tag, "lazy_load", new_val)
    
    # Reload and check
    cfg_mgr.reload()
    persisted_val = cfg_mgr.get_plugin_config(test_tag, "lazy_load")
    print(f"Persisted {test_tag} lazy_load: {persisted_val}")
    
    if persisted_val == new_val:
        print(f"✅ SUCCESS: {test_tag} lazy_load persisted correctly.")
    else:
        print(f"❌ FAILURE: {test_tag} lazy_load did NOT persist!")
        
    # Test a newly added tag
    print("\nTesting persistence of a newly added tag (USER)...")
    cfg_mgr.set_plugin_config("USER", "lazy_load", True)
    cfg_mgr.reload()
    user_lazy = cfg_mgr.get_plugin_config("USER", "lazy_load")
    if user_lazy == True:
        print("✅ SUCCESS: USER tag persisted correctly.")
    else:
        print("❌ FAILURE: USER tag did NOT persist!")

    print("\n--- VERIFICATION COMPLETE ---")

if __name__ == "__main__":
    verify()
