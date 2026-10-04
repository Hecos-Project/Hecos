import sqlite3
import json
c = sqlite3.connect(r'c:\Hecos\hecos\data\packages.db')
res = c.execute('SELECT manifest_snapshot FROM packages WHERE id="pc_automation"').fetchone()
if res and res[0]:
    manifest = json.loads(res[0])
    print(manifest.get('config_panel'))
