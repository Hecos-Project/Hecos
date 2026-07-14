import json
import os
import sqlite3

manifest_path = r'c:\Hecos\hecos\hpm\image_gen\manifest.json'
with open(manifest_path, 'r', encoding='utf-8') as f:
    manifest = json.load(f)

manifest['config_panel'] = {
    'tab_id': 'igen',
    'tab_label': 'Image Gen',
    'category': 'MULTIMEDIA',
    'tab_icon': '<i class="fas fa-image"></i>',
    'template_file': 'web/templates/config_panel.html',
    'js_file': 'web/static/js/igen_panel.js',
    'css_file': 'web/static/css/image_gen.css',
    'config_api_get': '/hecos/api/plugins/image_gen/config',
    'config_api_post': '/hecos/api/plugins/image_gen/config'
}

with open(manifest_path, 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=4)

db_path = r'c:\Hecos\hecos\data\packages.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT manifest_snapshot FROM packages WHERE id = 'image_gen'")
    row = c.fetchone()
    if row:
        snapshot = json.loads(row[0])
        snapshot['config_panel'] = manifest['config_panel']
        c.execute("UPDATE packages SET manifest_snapshot = ? WHERE id = 'image_gen'", (json.dumps(snapshot),))
        conn.commit()
    conn.close()
    print("Database updated.")
else:
    print("packages.db not found, might be a JSON file?")

# Hecos actually might use json instead of sqlite for packages.db depending on the implementation! Let's check.
