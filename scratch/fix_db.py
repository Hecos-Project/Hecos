import sqlite3
import json

conn = sqlite3.connect(r'C:\Hecos\hecos\data\packages.db')
c = conn.cursor()
c.execute("SELECT manifest_snapshot FROM packages WHERE id='builder_studio';")
row = c.fetchone()
if row and row[0]:
    man = json.loads(row[0])
    man['config_panel']['js_files'] = [
        "builder_studio/static/js/builder_core.js",
        "builder_studio/static/js/builder_ui.js",
        "builder_studio/static/js/builder_batch.js",
        "builder_studio/static/js/builder_info_sheets.js",
        "builder_studio/static/js/builder_wizard.js",
        "builder_studio/static/js/builder_io.js",
        "builder_studio/static/js/builder_compiler.js"
    ]
    c.execute("UPDATE packages SET manifest_snapshot = ? WHERE id = 'builder_studio'", (json.dumps(man),))
    conn.commit()
    print("Fixed manifest_snapshot in DB!")
else:
    print("Not found in DB")
