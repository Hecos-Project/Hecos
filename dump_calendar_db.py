import sqlite3
import json

try:
    c = sqlite3.connect('C:/Hecos/hecos/data/packages.db')
    row = c.execute('SELECT manifest_snapshot FROM packages WHERE id="calendar"').fetchone()
    if row:
        manifest = json.loads(row[0])
        print("TAG:", manifest.get('tag'))
        print("CONFIG_PANEL:", manifest.get('config_panel'))
    else:
        print("Calendar not found in DB")
except Exception as e:
    print("Error:", e)
