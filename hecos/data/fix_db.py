import sqlite3, shutil, os

db_path = r"c:\Hecos\hecos\data\packages.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("DELETE FROM packages WHERE id='reminder'")
conn.commit()
conn.close()
print("Removed from DB")

# Remove installed plugin code
plugin_dir = r"c:\Hecos\hecos\plugins\reminder"
if os.path.exists(plugin_dir):
    shutil.rmtree(plugin_dir)
    print(f"Removed {plugin_dir}")

# Remove any stale extension
ext_dir = r"c:\Hecos\hecos\modules\web_ui\extensions\reminder"
if os.path.exists(ext_dir):
    shutil.rmtree(ext_dir)
    print(f"Removed {ext_dir}")

print("Clean done - ready for fresh install")
