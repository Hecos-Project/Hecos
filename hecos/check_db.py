import sqlite3
import json

try:
    conn = sqlite3.connect('c:/Hecos/hecos/data/packages.db')
    cur = conn.cursor()
    cur.execute("SELECT manifest_snapshot FROM packages WHERE id='image_gen'")
    row = cur.fetchone()
    if row:
        print("FOUND MANIFEST SNAPSHOT:")
        print(row[0])
    else:
        print("Not found")
except Exception as e:
    print(f"Error: {e}")
