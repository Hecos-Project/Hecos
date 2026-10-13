import os
import json
from datetime import datetime
from hecos.core.logging import logger
from hecos.core.constants import LOGS_DIR

# Base directory for all presenter feed files: logs/presenter/
PRESENTER_FEED_DIR = os.path.join(LOGS_DIR, "presenter")


def _get_feed_path(session_id: str = None) -> str:
    """
    Returns the path to the feed file for a given session.
    Structure: logs/presenter/YYYY-MM-DD/<session_id>.jsonl
    Falls back to 'global' if no session_id is provided.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_sid = _sanitize_session_id(session_id) if session_id else "global"
    day_dir = os.path.join(PRESENTER_FEED_DIR, date_str)
    os.makedirs(day_dir, exist_ok=True)
    return os.path.join(day_dir, f"{safe_sid}.jsonl")


def _sanitize_session_id(session_id: str) -> str:
    """Sanitize session_id for safe use as a filename."""
    import re
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', str(session_id))[:64]


def add_feed_entry(event_type: str, text: str, session_id: str = None, persist: bool = True):
    """
    Appends an entry to the presenter feed.

    Args:
        event_type: Event category (e.g. 'coach_advice', 'playbook_violation').
        text: The text content to store and display.
        session_id: The chat session ID. Each session gets its own JSONL file.
                    If None, falls back to 'global' (system-level events).
        persist: Whether to write to disk. If False, only emits via SSE.
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event_name": event_type,
        "session_id": session_id or "global",
        "text": text
    }

    if persist:
        try:
            feed_file = _get_feed_path(session_id)
            with open(feed_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

            # Rotation: keep max_items per session file
            try:
                from hecos.modules.web_ui.extensions.presenter.config.store import load_presenter_config
                cfg = load_presenter_config()
                max_items = cfg.feed.max_items
            except Exception:
                max_items = 200

            with open(feed_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > max_items:
                with open(feed_file, "w", encoding="utf-8") as f:
                    f.writelines(lines[-max_items:])

        except Exception as e:
            logger.error(f"[Presenter] Could not save feed entry: {e}")

    # Emit to frontend via SSE (always, regardless of persist)
    try:
        from hecos.modules.web_ui.server import get_state_manager
        sm = get_state_manager()
        if sm is not None:
            sm.add_event("presenter_feed", entry)
    except Exception as e:
        logger.error(f"[Presenter] SSE push error: {e}")


def get_feed_entries(session_id: str = None, limit: int = 30) -> list:
    """
    Reads feed entries for a specific session from disk.
    Searches all dated subfolders in reverse chronological order.

    Args:
        session_id: Chat session ID to read. Falls back to 'global'.
        limit: Maximum number of entries to return (most recent).

    Returns:
        List of entry dicts, oldest to newest, capped at limit.
    """
    safe_sid = _sanitize_session_id(session_id) if session_id else "global"
    filename = f"{safe_sid}.jsonl"
    entries = []

    if not os.path.isdir(PRESENTER_FEED_DIR):
        return entries

    # Collect all dated subdirectories, sorted oldest-first for chronological order
    try:
        date_dirs = sorted(
            [d for d in os.listdir(PRESENTER_FEED_DIR)
             if os.path.isdir(os.path.join(PRESENTER_FEED_DIR, d)) and len(d) == 10],
            reverse=False
        )
    except Exception:
        return entries

    for date_dir in date_dirs:
        feed_file = os.path.join(PRESENTER_FEED_DIR, date_dir, filename)
        if os.path.exists(feed_file):
            try:
                with open(feed_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                entries.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
            except Exception as e:
                logger.warning(f"[Presenter] Feed read error ({feed_file}): {e}")

    # Return last N entries preserving chronological order
    return entries[-limit:]


def migrate_legacy_feed():
    """
    One-time migration: moves entries from the old monolithic presenter_feed.jsonl
    into the new per-session / global structure under logs/presenter/.
    """
    legacy_file = os.path.join(LOGS_DIR, "presenter_feed.jsonl")
    if not os.path.exists(legacy_file):
        return

    try:
        migrated = 0
        with open(legacy_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts = entry.get("timestamp", "")
                    try:
                        date_str = ts[:10]
                        if len(date_str) != 10:
                            raise ValueError
                    except (ValueError, TypeError):
                        date_str = datetime.now().strftime("%Y-%m-%d")

                    sid = entry.get("session_id", "global")
                    safe_sid = _sanitize_session_id(sid) if sid and sid != "global" else "global"
                    day_dir = os.path.join(PRESENTER_FEED_DIR, date_str)
                    os.makedirs(day_dir, exist_ok=True)
                    target = os.path.join(day_dir, f"{safe_sid}.jsonl")
                    with open(target, "a", encoding="utf-8") as out:
                        out.write(json.dumps(entry) + "\n")
                    migrated += 1
                except Exception:
                    pass

        if migrated > 0:
            os.rename(legacy_file, legacy_file + ".migrated")
            logger.info(f"[Presenter] Migrated {migrated} entries from legacy feed to per-session files.")
    except Exception as e:
        logger.error(f"[Presenter] Legacy feed migration failed: {e}")
