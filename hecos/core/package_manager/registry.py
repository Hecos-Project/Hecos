"""
registry.py
─────────────────────────────────────────────────────────────────────────────
Hecos Package Manager — Installed Package Registry

SQLite-backed registry that tracks every package installed via HPM.
The DB is stored at: hecos/data/packages.db

Responsibilities:
  - Register/unregister installed packages
  - Query installed packages (list, get by id)
  - Store manifest snapshot at install time for safe uninstallation
  - Track status: installed | disabled | broken
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import os
import json
import sqlite3
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any

from hecos.core.logging import logger

_DB_FILENAME = "packages.db"


class PackageRegistry:
    """
    Thread-safe SQLite registry of installed HPM packages.

    Usage:
        registry = PackageRegistry(data_dir="/path/to/hecos/data")
        registry.register(manifest_dict, install_path="/path/to/hecos/plugins/my_plugin")
        packages = registry.list_all()
        registry.unregister("my_plugin")
    """

    def __init__(self, data_dir: str):
        self._db_path = os.path.join(data_dir, _DB_FILENAME)
        self._lock = threading.Lock()
        os.makedirs(data_dir, exist_ok=True)
        self._init_db()

    # ── DB Init ──────────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        """Create the packages table if it doesn't exist."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS packages (
                    id                TEXT PRIMARY KEY,
                    name              TEXT NOT NULL,
                    version           TEXT NOT NULL,
                    type              TEXT NOT NULL DEFAULT 'plugin',
                    author            TEXT NOT NULL DEFAULT 'Unknown',
                    description       TEXT NOT NULL DEFAULT '',
                    status            TEXT NOT NULL DEFAULT 'installed',
                    install_path      TEXT NOT NULL,
                    installed_at      TEXT NOT NULL,
                    updated_at        TEXT,
                    previous_version  TEXT,
                    manifest_snapshot TEXT NOT NULL,
                    config_panel_tab  TEXT
                )
            """)
            # Migrate: add new columns to existing databases gracefully
            for col, col_def in [
                ("updated_at",       "TEXT"),
                ("previous_version", "TEXT"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE packages ADD COLUMN {col} {col_def}")
                except Exception:
                    pass  # Column already exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS installed_files (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    pkg_id   TEXT NOT NULL,
                    filepath TEXT NOT NULL,
                    FOREIGN KEY(pkg_id) REFERENCES packages(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # ── Write Operations ─────────────────────────────────────────────────────

    def register(
        self,
        manifest: Dict[str, Any],
        install_path: str,
        installed_files: Optional[List[str]] = None,
    ) -> bool:
        """
        Register a successfully installed package.
        If the package already exists (update scenario), the previous version
        is preserved in `previous_version` and `updated_at` is stamped.
        """
        pkg_id = manifest.get("id", "")
        if not pkg_id:
            logger.error("[HPM:Registry] Cannot register: manifest has no 'id' field.")
            return False

        config_panel_tab = None
        if manifest.get("config_panel"):
            cp = manifest["config_panel"]
            if isinstance(cp, dict):
                config_panel_tab = cp.get("tab_id")

        now = datetime.utcnow().isoformat()

        with self._lock:
            try:
                with self._connect() as conn:
                    # Check if this is an update (package already exists)
                    existing = conn.execute(
                        "SELECT version, installed_at FROM packages WHERE id = ?", (pkg_id,)
                    ).fetchone()

                    if existing:
                        # UPDATE path — preserve original install timestamp, bump updated_at
                        conn.execute("""
                            UPDATE packages SET
                                name=?, version=?, type=?, author=?, description=?,
                                status='installed', install_path=?,
                                updated_at=?, previous_version=?,
                                manifest_snapshot=?, config_panel_tab=?
                            WHERE id=?
                        """, (
                            manifest.get("name", pkg_id),
                            manifest.get("version", "0.0.0"),
                            manifest.get("type", "plugin"),
                            manifest.get("author", "Unknown"),
                            manifest.get("description", ""),
                            install_path,
                            now,
                            existing["version"],  # previous_version = old version
                            json.dumps(manifest, ensure_ascii=False),
                            config_panel_tab,
                            pkg_id,
                        ))
                        logger.info(
                            f"[HPM:Registry] Package '{pkg_id}' updated "
                            f"from v{existing['version']} to v{manifest.get('version')}."
                        )
                    else:
                        # FRESH install path
                        conn.execute("""
                            INSERT INTO packages
                                (id, name, version, type, author, description,
                                 status, install_path, installed_at, updated_at,
                                 previous_version, manifest_snapshot, config_panel_tab)
                            VALUES (?, ?, ?, ?, ?, ?, 'installed', ?, ?, NULL, NULL, ?, ?)
                        """, (
                            pkg_id,
                            manifest.get("name", pkg_id),
                            manifest.get("version", "0.0.0"),
                            manifest.get("type", "plugin"),
                            manifest.get("author", "Unknown"),
                            manifest.get("description", ""),
                            install_path,
                            now,
                            json.dumps(manifest, ensure_ascii=False),
                            config_panel_tab,
                        ))
                        logger.info(
                            f"[HPM:Registry] Package '{pkg_id}' v{manifest.get('version')} registered."
                        )

                    # Store file list for atomic uninstallation
                    if installed_files:
                        conn.execute("DELETE FROM installed_files WHERE pkg_id = ?", (pkg_id,))
                        conn.executemany(
                            "INSERT INTO installed_files (pkg_id, filepath) VALUES (?, ?)",
                            [(pkg_id, fp) for fp in installed_files]
                        )
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"[HPM:Registry] Failed to register '{pkg_id}': {e}")
                return False

    def unregister(self, pkg_id: str) -> bool:
        """Remove a package record from the registry."""
        with self._lock:
            try:
                with self._connect() as conn:
                    conn.execute("DELETE FROM packages WHERE id = ?", (pkg_id,))
                    conn.execute("DELETE FROM installed_files WHERE pkg_id = ?", (pkg_id,))
                    conn.commit()
                logger.info(f"[HPM:Registry] Package '{pkg_id}' unregistered.")
                return True
            except Exception as e:
                logger.error(f"[HPM:Registry] Failed to unregister '{pkg_id}': {e}")
                return False

    def set_status(self, pkg_id: str, status: str) -> bool:
        """Set the status of a package: 'installed', 'disabled', 'broken'."""
        valid_statuses = {"installed", "disabled", "broken"}
        if status not in valid_statuses:
            logger.error(f"[HPM:Registry] Invalid status '{status}'. Must be one of {valid_statuses}.")
            return False
        with self._lock:
            try:
                with self._connect() as conn:
                    conn.execute("UPDATE packages SET status = ? WHERE id = ?", (status, pkg_id))
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"[HPM:Registry] Failed to set status for '{pkg_id}': {e}")
                return False

    # ── Read Operations ──────────────────────────────────────────────────────

    def get(self, pkg_id: str) -> Optional[Dict[str, Any]]:
        """Return a package record by id, or None if not found."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM packages WHERE id = ?", (pkg_id,)
                ).fetchone()
                if row:
                    return self._row_to_dict(row)
        except Exception as e:
            logger.error(f"[HPM:Registry] Failed to get '{pkg_id}': {e}")
        return None

    def is_installed(self, pkg_id: str) -> bool:
        """Return True if a package with this id exists in the registry."""
        return self.get(pkg_id) is not None

    def list_all(self) -> List[Dict[str, Any]]:
        """Return all registered packages, ordered by name."""
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM packages ORDER BY name ASC"
                ).fetchall()
                return [self._row_to_dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[HPM:Registry] Failed to list packages: {e}")
            return []

    def get_installed_files(self, pkg_id: str) -> List[str]:
        """Return the list of files installed on disk for this package."""
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT filepath FROM installed_files WHERE pkg_id = ?", (pkg_id,)
                ).fetchall()
                return [r["filepath"] for r in rows]
        except Exception as e:
            logger.error(f"[HPM:Registry] Failed to get file list for '{pkg_id}': {e}")
            return []

    def get_manifest(self, pkg_id: str) -> Optional[Dict[str, Any]]:
        """Return the manifest snapshot stored at install time."""
        record = self.get(pkg_id)
        if record and record.get("manifest_snapshot"):
            try:
                return json.loads(record["manifest_snapshot"])
            except Exception:
                pass
        return None

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        # Deserialize manifest snapshot for API consumption
        if d.get("manifest_snapshot"):
            try:
                d["manifest_snapshot"] = json.loads(d["manifest_snapshot"])
            except Exception:
                pass
        return d
