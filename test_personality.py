import os
import sys

print("--- DEBUG START ---", flush=True)

try:
    # Aggiungi zentra al path
    sys.path.append(os.getcwd())
    print(f"Working directory: {os.getcwd()}", flush=True)

    from zentra.app.config import ConfigManager
    print("ConfigManager imported", flush=True)
    
    cm = ConfigManager()
    print(f"Config Manager loaded. Path: {cm._yaml_path}", flush=True)
    personalita_corrente = cm.get('ai', 'active_personality')
    print(f"Config Manager active_personality: {personalita_corrente}", flush=True)
    
    # Simula caricamento brain
    config = cm.config
    personality_name = config.get('ai', {}).get('active_personality', 'zentra.txt')
    print(f"Brain will try to load: {personality_name}", flush=True)
    
    clean_name = personality_name.replace(".txt", "").replace("_", " ") if personality_name else "Zentra"
    print(f"Clean name for context: {clean_name}", flush=True)
    
    from zentra.memory import brain_interface
    print("brain_interface imported", flush=True)
    
    context = brain_interface.get_context(config, dynamic_name=clean_name)
    print("\n--- Context Injected ---", flush=True)
    print(context, flush=True)
    print("------------------------", flush=True)

except Exception as e:
    print(f"CRITICAL ERROR: {e}", flush=True)
    import traceback
    traceback.print_exc()

print("--- DEBUG END ---", flush=True)
