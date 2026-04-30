import sqlite3
from werkzeug.security import generate_password_hash
import os

db_path = r'c:\Hecos\hecos\memory\users.db'

if os.path.exists(db_path):
    try:
        password_hash = generate_password_hash("hecos")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if admin exists
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        row = cursor.fetchone()
        
        if row:
            cursor.execute("UPDATE users SET password_hash = ? WHERE username = 'admin'", (password_hash,))
            print("Successfully updated admin password to 'hecos' in users.db")
        else:
            # Create admin if it doesn't exist (though it should)
            cursor.execute("INSERT INTO users (username, password_hash, role, display_name) VALUES (?, ?, ?, ?)",
                         ('admin', password_hash, 'admin', 'admin'))
            print("Successfully created admin user with password 'hecos' in users.db")
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error updating users.db: {e}")
else:
    print("users.db not found, skipping manual update.")
