import sqlite3

conn = sqlite3.connect(r'c:\Hecos\hecos\data\packages.db')
cur = conn.cursor()
cur.execute("SELECT id, name, version, type, manifest_snapshot FROM packages")
for row in cur.fetchall():
    print(f"ID: {row[0]} | NAME: {row[1]} | TYPE: {row[3]}")
