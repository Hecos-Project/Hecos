import sqlite3
import json

conn = sqlite3.connect(r'C:\Hecos\hecos\data\packages.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT id, status, manifest_snapshot FROM packages')
disabled_exts = set()
for r in cur.fetchall():
    print(f"[{r['id']}] status: {r['status']}")
    if r['status'] not in ('installed', 'active'):
        snap = r['manifest_snapshot']
        if snap:
            if isinstance(snap, str):
                try: snap = json.loads(snap)
                except: snap = {}
            for w in snap.get('widgets', []):
                epath = w.get('extension_path', '').rstrip('/')
                if epath:
                    ext_id = epath.split('/')[-1].split('\\')[-1]
                    disabled_exts.add(ext_id)

print('Disabled widgets set:', disabled_exts)
conn.close()
