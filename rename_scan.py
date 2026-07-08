import os

filepath = r"C:\Hecos\hecos\core\system\module_scanner.py"
if os.path.exists(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    replacements = {
        "start_plugin": "start_module",
        "plugin_abs_dir": "module_abs_dir",
        "HPM plugin": "HPM module"
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated module_scanner.py")
