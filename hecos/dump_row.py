import sqlite3
import json

try:
    conn = sqlite3.connect('c:/Hecos/hecos/data/packages.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM packages WHERE id='image_gen'")
    row = cur.fetchone()
    if row:
        d = dict(row)
        with open('c:/Hecos/hecos/image_gen_row.json', 'w', encoding='utf-8') as f:
            json.dump(d, f, indent=2)
        print("SAVED ROW")
    else:
        print("Not found")
except Exception as e:
    print(f"Error: {e}")
