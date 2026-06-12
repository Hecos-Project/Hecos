import sys, sqlite3
sys.path.append('c:/Hecos')
from hecos.plugins.lists.store import _get_db_path

db = _get_db_path()
conn = sqlite3.connect(db)
conn.execute("UPDATE lists SET icon='<i class=\"fas fa-list-check\"></i>' WHERE icon='📋'")
conn.commit()
conn.close()
