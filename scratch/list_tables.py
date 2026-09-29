import sqlite3
import json
conn = sqlite3.connect(r'C:\Hecos\data\packages.db')
c = conn.cursor()
c.execute("PRAGMA table_info(packages);")
print("Columns:", [col[1] for col in c.fetchall()])
