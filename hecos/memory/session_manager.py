"""
MODULE: Chat Session Manager
DESCRIPTION: Manages named chat sessions.
             - 'normal' sessions: persisted in SQLite DB across restarts.
             - 'incognito' sessions: RAM-only, zero writes to disk, vanish on restart.
               Messages are kept in memory during the open session for coherent
               multi-turn conversation without leaving traces on disk.

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
    upsert_ram_assistant_message,
    update_ram_last_assistant_meta,
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
