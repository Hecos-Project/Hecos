import sqlite3, json

conn = sqlite3.connect(r'c:\Hecos\hecos\data\packages.db')
cur = conn.cursor()
for pkg_id in ['drive', 'flows', 'browser_automation', 'net_search']:
    cur.execute("SELECT id, name, manifest_snapshot FROM packages WHERE id = ?", (pkg_id,))
    row = cur.fetchone()
    if row:
        print(f"=== {row[0]} ===")
        manifest = json.loads(row[2])
        print("name:", manifest.get("name"))
        print("icon:", manifest.get("icon"))
        print("icon_url:", manifest.get("icon_url"))
        print("screenshots:", manifest.get("screenshots"))
