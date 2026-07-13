import os

filepath = r"C:\Hecos\hecos\core\module_bus.py"
if os.path.exists(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    replacements = {
        "HPM plugin subprocesses": "HPM module subprocesses",
        "plugin after": "module after",
        "start_plugin": "start_module",
        "restart_plugin": "restart_module",
        "plugin_dir": "module_dir",
        "[ModuleBus] Plugin": "[ModuleBus] Module",
        "restart_module: '{tag}' not registered": "restart_module: '{tag}' not registered"
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated module_bus.py")
