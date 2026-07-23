import sqlite3
import json

try:
    conn = sqlite3.connect('c:/Hecos/hecos/data/packages.db')
    cur = conn.cursor()
    cur.execute("SELECT manifest_snapshot FROM packages WHERE id='image_gen'")
    row = cur.fetchone()
    if row:
        with open('c:/Hecos/hecos/manifest_dump.json', 'w', encoding='utf-8') as f:
            f.write(row[0])
        print("FOUND AND SAVED")
    else:
        print("Not found")
except Exception as e:
    print(f"Error: {e}")
