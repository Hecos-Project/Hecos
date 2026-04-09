import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from zentra.core.logging import logger

class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = str(id)
        self.username = username
        self.role = role

class AuthManager:
    """
    Gestisce il database locale SQLite per l'autenticazione degli utenti e la verifica
    delle password tramite hash (PBKDF2).
    """
    def __init__(self):
        # zentra/core/auth/auth_manager.py -> ../../ is zentra/
        zentra_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.db_dir = os.path.join(zentra_dir, "memory")
        self.db_path = os.path.join(self.db_dir, "users.db")
        os.makedirs(self.db_dir, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Crea le tabelle necessarie se non esistono e popola l'admin di default."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'guest'
                    )
                ''')
                conn.commit()

            # Crea l'admin predefinito se la tabella è vuota
            if not self.get_user_by_username("admin"):
                self.create_user("admin", "zentra", "admin")
                logger.info("[AuthManager] Nessun utente trovato. Creato utente di default 'admin' con password 'zentra'.")
                
        except Exception as e:
            logger.error(f"[AuthManager] Errore inizializzazione DB: {e}")

    def create_user(self, username, password, role="guest"):
        """Crea un nuovo utente con password hashata in modo sicuro."""
        user = self.get_user_by_username(username)
        if user:
            return False # Utente già esistente
            
        password_hash = generate_password_hash(password)
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    (username, password_hash, role)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"[AuthManager] Errore creazione utente {username}: {e}")
            return False

    def verify_password(self, username, password) -> bool:
        """Verifica la password convertendola e comparandola con l'hash a database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                
                if row:
                    stored_hash = row[0]
                    return check_password_hash(stored_hash, password)
                return False
        except Exception as e:
            logger.error(f"[AuthManager] Errore verifica password {username}: {e}")
            return False

    def get_user_by_username(self, username):
        """Ritorna l'oggetto User(UserMixin) se l'utente esiste."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, username, role FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                
                if row:
                    return User(id=row[0], username=row[1], role=row[2])
                return None
        except Exception as e:
            logger.error(f"[AuthManager] Errore in get_user_by_username: {e}")
            return None

    def get_user_by_id(self, user_id):
        """Carica l'utente tramite ID (necessario per Flask-Login session loader)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, username, role FROM users WHERE id = ?", (int(user_id),))
                row = cursor.fetchone()
                
                if row:
                    return User(id=row[0], username=row[1], role=row[2])
                return None
        except Exception as e:
            return None

    def get_all_users(self):
        """Ritorna la lista di tutti gli utenti registrati (id, username, role)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, username, role FROM users ORDER BY id ASC")
                rows = cursor.fetchall()
                return [{"id": r[0], "username": r[1], "role": r[2]} for r in rows]
        except Exception as e:
            logger.error(f"[AuthManager] Errore in get_all_users: {e}")
            return []

    def update_password(self, username, new_password):
        """Aggiorna la password di un utente esistente."""
        try:
            password_hash = generate_password_hash(new_password)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, username))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"[AuthManager] Errore in update_password per {username}: {e}")
            return False

    def delete_user(self, username):
        """Elimina un utente dal sistema (non può eliminare l'admin)."""
        if username == "admin":
            return False # Fallback di sicurezza: master admin indestructible
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE username = ?", (username,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"[AuthManager] Errore in delete_user per {username}: {e}")
            return False

# Istanza statica globale per il sistema
auth_mgr = AuthManager()
