import sys
import os
import traceback

# Setup paths
project_root = r'c:\Zentra-Core'
sys.path.insert(0, project_root)

try:
    print("[DEBUG] Importing core components...")
    from zentra.app.config import ConfigManager
    from zentra.app.state_manager import StateManager
    from zentra.app.model_manager import ModelManager
    from zentra.app.personality_manager import PersonalityManager
    from zentra.app.menu_handler import MenuHandler

    print("[DEBUG] Initializing managers...")
    config_manager = ConfigManager()
    state_manager = StateManager()
    model_manager = ModelManager(config_manager)
    personality_manager = PersonalityManager(config_manager)
    
    print("[DEBUG] Initializing MenuHandler...")
    mh = MenuHandler(config_manager, state_manager, model_manager, personality_manager)
    
    print("[DEBUG] Simulating F6 key press...")
    mh.handle_function_key("F6")
    print("[DEBUG] F6 test completed successfully.")

except Exception as e:
    print("[CRASH DETECTED]")
    traceback.print_exc()
    with open(r'c:\Zentra-Core\f6_crash_log.txt', 'w') as f:
        traceback.print_exc(file=f)
