import sys, json, sqlite3, os

manifest_content = """id = "builder_studio"
manifest_version = "1"
name = "Builder Studio"
version = "1.0.0"
author = "Hecos Community"
license = "GPL-3.0"
description = "Visual IDE for building, compiling, inspecting and managing Hecos packages (.hpkg)."
icon = "fas fa-hammer"
icon_url = ""
screenshots = []
category = "SYSTEM"
plugin_tag = "BUILDER"
is_class_based = false
type = "system_app"
pip_isolation = "shared"
plugin_dir = "builder_studio"
lazy_load = false
readme = "README.md"
dependencies = []
pip_requirements = ["tomli_w"]
python_requires = ">=3.11"

[config_panel]
tab_id = "builder"
tab_label = "Builder Studio"
tab_icon = "fas fa-hammer"
template_file = "builder_studio/templates/config_builder.html"
js_files = [
    "builder_studio/static/js/builder_core.js",
    "builder_studio/static/js/builder_ui.js",
    "builder_studio/static/js/builder_io.js",
    "builder_studio/static/js/builder_compiler.js"
]
api_routes_file = "builder_studio/routes.py"
category = "SISTEMA"

[capabilities]
llm_tools = []
slash_commands = []
has_widget = false
has_config_panel = true
has_api_routes = true
has_system_calls = true
syscall_notes = "Executes subprocess calls to Hecos_HPM_Builder CLI for compilation, key generation, and capabilities scanning."
notes = "Full package development studio. Build, inspect, sign, and publish .hpkg packages."
"""

# write proper utf-8 file to replace the broken one
with open(r'C:\Hecos\hecos\hpm\builder_studio\hpkg_manifest.toml', 'w', encoding='utf-8') as f:
    f.write(manifest_content)
with open(r'C:\Hecos-Packages\sources\apps\builder_studio_src\hpkg_manifest.toml', 'w', encoding='utf-8') as f:
    f.write(manifest_content)

db_path = r'C:\Hecos\hecos\data\packages.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
    
try:
    import tomllib
except ImportError:
    import tomli as tomllib
    
manifest = tomllib.loads(manifest_content)

cursor.execute('SELECT * FROM packages WHERE id = ?', ('builder_studio',))
existing = cursor.fetchone()
if existing:
    print('builder_studio is already in the registry. Updating it just in case.')
    cursor.execute('UPDATE packages SET manifest_snapshot = ? WHERE id = ?', (json.dumps(manifest), 'builder_studio'))
else:
    cursor.execute('''
        INSERT INTO packages (
            id, name, version, type, author, description, 
            status, install_path, installed_at, manifest_snapshot, 
            config_panel_tab, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, CURRENT_TIMESTAMP)
    ''', (
        manifest.get('id'),
        manifest.get('name'),
        manifest.get('version'),
        manifest.get('type'),
        manifest.get('author'),
        manifest.get('description'),
        'active',
        r'C:\Hecos\hecos\hpm\builder_studio',
        json.dumps(manifest),
        'builder'
    ))
conn.commit()
print('Successfully registered builder_studio in packages.db registry.')
