import sqlite3
import json
conn = sqlite3.connect('c:\\Hecos\\hecos\\data\\packages.db')
cur = conn.cursor()
cur.execute('SELECT files FROM packages WHERE id="webcam_widget"')
row = cur.fetchone()
if row:
    print('\n'.join(json.loads(row[0])))
