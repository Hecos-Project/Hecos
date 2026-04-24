import sys
import os
import traceback
import time

# Setup paths
project_root = r'c:\Zentra-Core'
sys.path.insert(0, project_root)

def debug_log(msg):
    print(f"[DEBUG] {msg}")
    sys.stdout.flush()

try:
    debug_log("Stage 1: Imports...")
    from zentra.app.config import ConfigManager
    from zentra.app.state_manager import StateManager
    from zentra.app.application import ZentraApplication
    from zentra.core.logging import logger
    
    debug_log("Stage 2: Initializing Application...")
    app = ZentraApplication()
    
    debug_log("Stage 3: Running Bootstrapper...")
    # Simulate bootstrapper.initialize()
    app.bootstrapper.initialize()
    
    debug_log("Stage 4: Initial UI...")
    # Simulate first part of app.run()
    config = app.config_manager.config
    from zentra.ui import interface
    interface.show_complete_ui(
        config,
        app.state_manager.voice_status,
        app.state_manager.listening_status,
        app.state_manager.system_status,
        ptt_status=app.state_manager.push_to_talk
    )
    
    debug_log("Stage 5: Welcome Sequence...")
    app.bootstrapper.show_welcome()
    
    debug_log("Stage 6: Starting Threads...")
    from zentra.app.threads import AscoltoThread
    ascolto_thread = AscoltoThread(app.state_manager)
    ascolto_thread.start()
    
    debug_log("Stage 7: Entering Main Loop (Simulated)...")
    # Just run 2 seconds of loop
    start_t = time.time()
    while time.time() - start_t < 2:
        evento, input_utente = app.input_handler.handle_keyboard_input("--> ", "")
        time.sleep(0.1)
        
    debug_log("TEST COMPLETED SUCCESSFULLY.")

except Exception as e:
    debug_log("CRASH DETECTED!")
    traceback.print_exc()
    with open(r'c:\Zentra-Core\startup_crash_log.txt', 'w') as f:
        traceback.print_exc(file=f)
    sys.exit(1)
