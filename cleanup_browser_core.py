import os
import shutil

# 1. Delete hecos/modules/browser
browser_dir = r'c:\Hecos\hecos\modules\browser'
if os.path.exists(browser_dir):
    shutil.rmtree(browser_dir)

# 2. Delete config_browser.html
config_html = r'c:\Hecos\hecos\modules\web_ui\templates\modules\config_browser.html'
if os.path.exists(config_html):
    os.remove(config_html)

# 3. Update plugins_schema.py
schema_file = r'c:\Hecos\hecos\config\schemas\plugins_schema.py'
if os.path.exists(schema_file):
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema_content = f.read()
    
    # We remove PluginBrowser
    # It is located between PluginMCPBridge and PluginUsers.
    import re
    # Remove the PluginBrowser class definition
    schema_content = re.sub(r'class PluginBrowser\(BaseModel\):.*?cdp_port: int = 9222\n+', '', schema_content, flags=re.DOTALL)
    # Remove from PluginsConfig
    schema_content = re.sub(r'\s*BROWSER: PluginBrowser = Field\(default_factory=PluginBrowser\)', '', schema_content)
    
    with open(schema_file, 'w', encoding='utf-8') as f:
        f.write(schema_content)

# 4. Update routes_system_diagnostic.py
diag_file = r'c:\Hecos\hecos\modules\web_ui\routes_system_diagnostic.py'
if os.path.exists(diag_file):
    with open(diag_file, 'r', encoding='utf-8') as f:
        diag_content = f.read()
    
    # Remove the route
    diag_content = re.sub(r'\s*@app\.route\("/api/browser/launch_external", methods=\["POST"\]\)\s*def browser_launch_external\(\):.*?return jsonify\(\{"ok": False, "error": str\(exc\)\}\), 500\n+', '\n', diag_content, flags=re.DOTALL)
    
    with open(diag_file, 'w', encoding='utf-8') as f:
        f.write(diag_content)

# 5. Update routes_config_core.py
routes_core = r'c:\Hecos\hecos\modules\web_ui\routes_config_core.py'
if os.path.exists(routes_core):
    with open(routes_core, 'r', encoding='utf-8') as f:
        core_content = f.read()
    
    core_content = re.sub(r'\s*\'browser\':\s*\'modules/config_browser\.html\',', '', core_content)
    
    with open(routes_core, 'w', encoding='utf-8') as f:
        f.write(core_content)

# 6. Update config_manifest.js
manifest_js = r'c:\Hecos\hecos\modules\web_ui\static\js\config_manifest.js'
if os.path.exists(manifest_js):
    with open(manifest_js, 'r', encoding='utf-8') as f:
        manifest_content = f.read()
    
    manifest_content = re.sub(r'\s*\{\s*id:\s*\'browser\',.*?\},', '', manifest_content, flags=re.DOTALL)
    
    with open(manifest_js, 'w', encoding='utf-8') as f:
        f.write(manifest_content)

# 7. Update browser_manager.py
manager = r'c:\Hecos\hecos\tray\browser_manager.py'
if os.path.exists(manager):
    with open(manager, 'r', encoding='utf-8') as f:
        manager_content = f.read()
    
    manager_content = manager_content.replace('from hecos.modules.browser import engine', 'from hecos.hpm.browser_automation.plugin import engine')
    
    with open(manager, 'w', encoding='utf-8') as f:
        f.write(manager_content)
