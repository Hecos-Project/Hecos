"""
MODULE: Chat Session Manager
DESCRIPTION: Manages named chat sessions.
             - 'normal' sessions: persisted in SQLite DB across restarts.
             - 'auto_wipe' sessions: RAM-only (visible while app runs, vanish on restart).
               Messages are kept in memory and available when switching back to the session.
             - 'incognito' sessions: RAM-only, zero writes to disk.
             Both non-normal modes never touch the DB.

Facade module. Implementations are split across:
- session_state.py
- session_db.py
- session_crud.py
- session_maintenance.py
"""

from hecos.memory.session_state import (
    _ram_sessions,
    _is_ram_mode
)

from hecos.memory.session_db import (
    migrate_schema,
    _purge_vault_sessions
)

from hecos.memory.session_crud import (
    create_session,
    get_sessions,
    get_session,
    get_session_messages,
    add_ram_message,
    archive_session,
    rename_session,
    change_session_mode,
    touch_session,
    delete_session
)

from hecos.memory.session_maintenance import (
    delete_all_sessions,
    archive_all_sessions,
    delete_all_archived_sessions,
    wipe_session_messages,
    auto_limit_history
)
