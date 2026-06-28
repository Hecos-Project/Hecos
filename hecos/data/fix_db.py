import sqlite3

def run():
    db_path = r"c:\Hecos\hecos\data\packages.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM packages WHERE id='reminder'")
    conn.commit()
    conn.close()
    print("Deleted 'reminder' from packages.db")

if __name__ == "__main__":
    run()
