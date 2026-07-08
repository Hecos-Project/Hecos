import os

files_to_modify = [
    r"C:\Hecos\hecos\core\module_bus.py",
    r"C:\Hecos\hecos\core\ipc\proxy.py",
    r"C:\Hecos\hecos\core\system\module_scanner.py",
    r"C:\Hecos-Packages\Hecos_HPM_Builder\modules\scaffold.py",
    r"C:\Hecos\hecos\hpm\image_gen\runner.py",
    r"C:\Hecos-Packages\image_gen_src\plugin\runner.py"
]

replacements = {
    "PluginBus": "ModuleBus",
    "PluginProxy": "ModuleProxy",
    "plugin_bus": "module_bus",
    "Plugin Runner": "Module Runner",
    "Plugin subprocess": "Module subprocess",
    "Plugin has no": "Module has no",
    "Plugin runner ready": "Module runner ready",
    "Plugin '": "Module '",
    "[PluginBus]": "[ModuleBus]",
    "plugin_module.tools": "module.tools",
    "Plugin —": "Module —"
}

for filepath in files_to_modify:
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        continue
        
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original = content
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")
    else:
        print(f"No changes needed for {filepath}")
