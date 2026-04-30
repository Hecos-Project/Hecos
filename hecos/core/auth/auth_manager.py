import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from hecos.core.logging import logger

class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = str(id)
        self.username = username
        self.role = role

class AuthManager:
    """
    Gestisce il database locale SQLite per l'autenticazione degli utenti e la verifica
    delle password tramite hash (PBKDF2).
    Supporta profili utente estesi: display_name, bio_notes, avatar_path, preferred_language.
    """
    def __init__(self):
        # hecos/core/auth/auth_manager.py -> ../../ is hecos/
        hecos_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.db_dir = os.path.join(hecos_dir, "memory")
        self.db_path = os.path.join(self.db_dir, "users.db")
        os.makedirs(self.db_dir, exist_ok=True)
        self._init_db()
        self._migrate_db()

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
                        role TEXT NOT NULL DEFAULT 'guest',
                        display_name TEXT,
                        bio_notes TEXT,
                        avatar_path TEXT,
                        preferred_language TEXT DEFAULT 'it'
                    )
                ''')
                conn.commit()

            # Crea l'admin predefinito se la tabella è vuota
            if not self.get_user_by_username("admin"):
                self.create_user("admin", "hecos", "admin")
                logger.info("[AuthManager] Nessun utente trovato. Creato utente di default 'admin' con password 'hecos'.")
                
        except Exception as e:
            logger.error(f"[AuthManager] Errore inizializzazione DB: {e}")

    def _migrate_db(self):
        """Aggiunge le nuove colonne al DB se l'utente aveva una versione precedente (senza profilo)."""
        new_columns = [
            ("display_name",        "TEXT"),
            ("bio_notes",           "TEXT"),
            ("avatar_path",         "TEXT"),
            ("preferred_language",  "TEXT DEFAULT 'it'"),
        ]
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(users)")
                existing = {row[1] for row in cursor.fetchall()}
                for col_name, col_type in new_columns:
                    if col_name not in existing:
                        cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                        logger.info(f"[AuthManager] Migrata colonna '{col_name}' alla tabella users.")
                conn.commit()
        except Exception as e:
            logger.error(f"[AuthManager] Errore migrazione DB: {e}")

    def create_user(self, username, password, role="guest"):
        """Crea un nuovo utente con password hashata in modo sicuro."""
        user = self.get_user_by_username(username)
        if user:
            return False  # Utente già esistente
            
        password_hash = generate_password_hash(password)
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role, display_name) VALUES (?, ?, ?, ?)",
                    (username, password_hash, role, username)
                )
                conn.commit()
                # Initialize the user's private memory vault
                self._init_user_vault(username)
                return True
        except Exception as e:
            logger.error(f"[AuthManager] Errore creazione utente {username}: {e}")
            return False

    def _init_user_vault(self, username: str):
        """Initialises the private memory vault folder for the user."""
        try:
            from hecos.memory.user_vault_manager import create_user_vault
            create_user_vault(username)
        except Exception as e:
            logger.warning(f"[AuthManager] Could not init vault for {username}: {e}")

    def verify_password(self, username, password) -> bool:
        """Verifica la password convertendola e comparandola con l'hash a database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                if row:
                    return check_password_hash(stored_hash := row[0], password)
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

    def get_profile(self, username: str) -> dict:
        """Returns the full profile dict for a user, including extended fields."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, username, role, display_name, bio_notes, avatar_path, preferred_language "
                    "FROM users WHERE username = ?", (username,)
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "id": row[0], "username": row[1], "role": row[2],
                        "display_name": row[3] or row[1],
                        "bio_notes": row[4] or "",
                        "avatar_path": row[5] or "",
                        "preferred_language": row[6] or "it",
                    }
                return {}
        except Exception as e:
            logger.error(f"[AuthManager] Errore in get_profile: {e}")
            return {}

    def update_profile(self, username: str, fields: dict) -> bool:
        """Updates one or more profile fields for a user (safe: only whitelisted fields)."""
        allowed = {"display_name", "bio_notes", "avatar_path", "preferred_language"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return False
        try:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [username]
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE users SET {set_clause} WHERE username = ?", values)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"[AuthManager] Errore in update_profile per {username}: {e}")
            return False

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
            return False  # Fallback di sicurezza: master admin indestructible
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
