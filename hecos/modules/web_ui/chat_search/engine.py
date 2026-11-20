"""
hecos/modules/web_ui/chat_search/engine.py
─────────────────────────────────────────────────────────────────────────────
High-performance, privacy-isolated Chat Search Engine for Hecos.
- Uses SQLite FTS5 (unicode61 remove_diacritics 2) with automatic sync triggers
  on the user's isolated vault DB (`memory/users/<user_id>/history.db`).
- Blends FTS5 BM25 ranking with exact/substring fallback for code identifiers,
  paths, and symbols, plus accent-folded session title matching.
- Strict Privacy Guarantees:
  * Active mode (`archived=False`): ONLY searches active normal sessions.
    Archived sessions are NEVER exposed.
  * Archive mode (`archived=True`): ONLY searches archived normal sessions.
  * Incognito sessions are NEVER indexed on disk and NEVER appear in global
    search; they are searchable ONLY in RAM when explicitly targeting
    `scope="current"` on an open incognito session.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import os
import re
import sqlite3
import threading
import time
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from hecos.core.logging import logger

_FTS_INIT_LOCK = threading.Lock()
_FTS_READY_DBS: set[str] = set()

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_TOKEN_RE = re.compile(r'"([^"]+)"|(\S+)')
_WS_RE = re.compile(r"\s+")


# ── Text Normalization & Query Parsing ────────────────────────────────────────

def _fold_accents(text: str) -> str:
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


def _parse_query(raw_query: str) -> Tuple[List[str], List[str]]:
    """
    Parses raw user query into:
      - phrases: exact quoted phrases (e.g. "control room")
      - terms: individual non-empty tokens
    """
    q = (raw_query or "").strip()
    if not q:
        return [], []
    phrases: List[str] = []
    terms: List[str] = []
    for m in _TOKEN_RE.finditer(q):
        phrase, word = m.group(1), m.group(2)
        if phrase is not None:
            cleaned = phrase.strip()
            if cleaned:
                phrases.append(cleaned)
        elif word:
            cleaned = word.strip()
            if cleaned:
                terms.append(cleaned)
    return phrases, terms


def _build_fts5_match_expr(phrases: List[str], terms: List[str]) -> str:
    """
    Builds a safe FTS5 MATCH expression.
    Every token is double-quote escaped to prevent FTS5 syntax errors on
    characters like '-', '/', ':', '.', '(', ')', '*', etc.
    """
    parts: List[str] = []
    for p in phrases:
        safe = p.replace('"', '""').strip()
        if safe:
            parts.append(f'"{safe}"')
    for t in terms:
        # Strip punctuation-only noise for FTS5 token matching, keep inner word chunks
        word_chunks = re.findall(r"[^\W_]+", t, re.UNICODE)
        if not word_chunks:
            continue
        for chunk in word_chunks:
            safe = chunk.replace('"', '""')
            if len(safe) >= 2:
                parts.append(f'"{safe}"*')
            else:
                parts.append(f'"{safe}"')
    return " AND ".join(parts)


def _needs_substring_fallback(raw_query: str, terms: List[str]) -> bool:
    """
    Returns True when the query contains code/path symbols (e.g. `_`, `/`, `.`, `-`, `:`)
    or short/infix patterns where FTS5 prefix tokenization alone might miss substring hits.
    """
    if re.search(r"[_/.:\-<>@#$%^&*(){}\[\]]", raw_query):
        return True
    if any(len(t) <= 2 for t in terms):
        return True
    return False


def _matches_all_folded(text: str, folded_needles: List[str]) -> bool:
    if not folded_needles:
        return False
    hay = _fold_accents(text)
    return all(n in hay for n in folded_needles)


def _build_snippet(raw_message: str, phrases: List[str], terms: List[str], max_len: int = 165) -> Tuple[str, bool]:
    """
    Builds a clean plain-text contextual snippet centered around the first match.
    Strips <think> blocks unless the match occurs exclusively inside <think>.
    Returns (snippet_text, matched_in_thinking).
    """
    msg = raw_message or ""
    needles = [_fold_accents(x) for x in (phrases + terms) if x.strip()]

    stripped = _THINK_RE.sub("", msg).strip()
    in_thinking = False
    target_text = stripped if stripped else msg

    if stripped and needles:
        folded_stripped = _fold_accents(stripped)
        if not any(n in folded_stripped for n in needles):
            # Match might be inside <think> block
            if any(n in _fold_accents(msg) for n in needles):
                target_text = msg.replace("<think>", "").replace("</think>", "").strip()
                in_thinking = True

    flat = _WS_RE.sub(" ", target_text).strip()
    if not flat:
        return "", in_thinking

    if len(flat) <= max_len:
        return flat, in_thinking

    folded_flat = _fold_accents(flat)
    first_pos = -1
    for n in needles:
        idx = folded_flat.find(n)
        if idx != -1 and (first_pos == -1 or idx < first_pos):
            first_pos = idx

    if first_pos == -1:
        return flat[: max_len - 1].rstrip() + "…", in_thinking

    # Center snippet around the first match (with ~35% lead-in context)
    lead = max(28, int(max_len * 0.32))
    start = max(0, first_pos - lead)
    end = min(len(flat), start + max_len)
    if end - start < max_len and start > 0:
        start = max(0, end - max_len)

    # Nudge start/end to word boundaries when clean
    if start > 0:
        sp = flat.find(" ", start, min(len(flat), start + 18))
        if sp != -1 and sp < first_pos:
            start = sp + 1
    if end < len(flat):
        sp = flat.rfind(" ", max(start, end - 18), end)
        if sp != -1 and sp > first_pos:
            end = sp

    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(flat) else ""
    return f"{prefix}{flat[start:end].strip()}{suffix}", in_thinking


def _cutoff_timestamp(date_range: str) -> Optional[str]:
    now = datetime.now()
    if date_range == "today":
        return now.strftime("%Y-%m-%d 00:00:00")
    if date_range == "7d":
        return (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    if date_range == "30d":
        return (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    return None


def _norm_role(role: str) -> str:
    r = (role or "").strip().lower()
    return "user" if r == "user" else "assistant"


# ── FTS5 Index Management (Non-Intrusive Shadow Table + Triggers) ─────────────

def ensure_fts_index(db_path: str, force_rebuild: bool = False) -> bool:
    """
    Ensures the FTS5 virtual table and sync triggers exist on `db_path`.
    Never alters the existing `history` table schema.
    """
    if not db_path or not os.path.exists(db_path):
        return False

    if not force_rebuild and db_path in _FTS_READY_DBS:
        return True

    with _FTS_INIT_LOCK:
        if not force_rebuild and db_path in _FTS_READY_DBS:
            return True
        try:
            with sqlite3.connect(db_path, timeout=15) as conn:
                cur = conn.cursor()
                # Check history table exists
                has_hist = cur.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='history'"
                ).fetchone()
                if not has_hist:
                    return False

                fts_existed = cur.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='history_fts'"
                ).fetchone() is not None

                cur.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS history_fts USING fts5(
                        message,
                        content='history',
                        content_rowid='id',
                        tokenize='unicode61 remove_diacritics 2'
                    )
                """)

                # Auto-sync triggers keep FTS5 fresh on every insert/delete/update
                cur.execute("""
                    CREATE TRIGGER IF NOT EXISTS history_fts_ai AFTER INSERT ON history BEGIN
                        INSERT INTO history_fts(rowid, message) VALUES (new.id, COALESCE(new.message, ''));
                    END
                """)
                cur.execute("""
                    CREATE TRIGGER IF NOT EXISTS history_fts_ad AFTER DELETE ON history BEGIN
                        INSERT INTO history_fts(history_fts, rowid, message)
                        VALUES('delete', old.id, COALESCE(old.message, ''));
                    END
                """)
                cur.execute("""
                    CREATE TRIGGER IF NOT EXISTS history_fts_au AFTER UPDATE OF message ON history BEGIN
                        INSERT INTO history_fts(history_fts, rowid, message)
                        VALUES('delete', old.id, COALESCE(old.message, ''));
                        INSERT INTO history_fts(rowid, message)
                        VALUES (new.id, COALESCE(new.message, ''));
                    END
                """)

                # Populate index if newly created or explicit rebuild requested
                if not fts_existed or force_rebuild:
                    cur.execute("INSERT INTO history_fts(history_fts) VALUES('rebuild')")
                    logger.info(f"[CHAT_SEARCH] FTS5 index built for {os.path.basename(os.path.dirname(db_path))}/history.db")

                # Helpful covering index for fast msg_index calculation and session lookup
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_history_session_id ON history(session_id, id)"
                )
                conn.commit()
            _FTS_READY_DBS.add(db_path)
            return True
        except Exception as e:
            logger.warning(f"[CHAT_SEARCH] FTS5 setup fallback (will use SQL/Python scan): {e}")
            return False


# ── Session Metadata Lookup (Strict Active vs Archived Isolation) ─────────────

def _load_allowed_sessions(archived: bool, scope: str, current_session_id: Optional[str]) -> Dict[str, dict]:
    """
    Loads ONLY normal DB sessions matching `is_archived = (1 if archived else 0)`.
    Strictly excludes Incognito sessions from disk searches.
    """
    from hecos.memory.session_state import PATH_DB

    if not os.path.exists(PATH_DB):
        return {}

    allowed: Dict[str, dict] = {}
    arch_flag = 1 if archived else 0
    try:
        with sqlite3.connect(PATH_DB, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            if scope == "current" and current_session_id:
                rows = cur.execute(
                    """
                    SELECT id, title, created_at, updated_at, privacy_mode, is_archived
                    FROM sessions
                    WHERE id = ? AND privacy_mode = 'normal' AND is_archived = ?
                    """,
                    (current_session_id, arch_flag),
                ).fetchall()
            else:
                rows = cur.execute(
                    """
                    SELECT id, title, created_at, updated_at, privacy_mode, is_archived
                    FROM sessions
                    WHERE privacy_mode = 'normal' AND is_archived = ?
                    ORDER BY updated_at DESC
                    """,
                    (arch_flag,),
                ).fetchall()
            for r in rows:
                d = dict(r)
                allowed[d["id"]] = d
    except Exception as e:
        logger.error(f"[CHAT_SEARCH] Failed loading sessions metadata: {e}")

    return allowed


# ── RAM Search (Strictly Current Open Incognito Session Only) ─────────────────

def _search_ram_current_session(
    session_id: str,
    phrases: List[str],
    terms: List[str],
    role_filter: str,
    cutoff_ts: Optional[str],
    limit: int,
) -> Dict[str, Any]:
    from hecos.memory.session_state import _ram_sessions

    sess = _ram_sessions.get(session_id)
    if not sess:
        return {"groups": [], "total_matches": 0, "total_sessions": 0, "is_incognito_scope": True}

    folded_needles = [_fold_accents(x) for x in (phrases + terms) if x.strip()]
    messages = sess.get("messages") or []
    hits = []
    for idx, m in enumerate(messages):
        m_role = _norm_role(m.get("role", ""))
        if role_filter != "all" and m_role != role_filter:
            continue
        ts = m.get("timestamp") or ""
        if cutoff_ts and ts and ts < cutoff_ts:
            continue
        msg_text = m.get("message") or ""
        if _matches_all_folded(msg_text, folded_needles):
            snippet, in_thinking = _build_snippet(msg_text, phrases, terms)
            hits.append({
                "message_id": m.get("id"),
                "session_id": session_id,
                "msg_index": idx,
                "role": m_role,
                "timestamp": ts,
                "snippet": snippet,
                "in_thinking": in_thinking,
            })

    total_matches = len(hits)
    if not hits:
        return {"groups": [], "total_matches": 0, "total_sessions": 0, "is_incognito_scope": True}

    group = {
        "session_id": session_id,
        "title": sess.get("title") or "Incognito Chat",
        "updated_at": sess.get("updated_at") or sess.get("created_at") or "",
        "is_archived": False,
        "is_incognito": True,
        "title_matched": _matches_all_folded(sess.get("title") or "", folded_needles),
        "match_count": total_matches,
        "hits": hits[:limit],
    }
    return {
        "groups": [group],
        "total_matches": total_matches,
        "total_sessions": 1,
        "is_incognito_scope": True,
    }


# ── Main Search Entry Point ───────────────────────────────────────────────────

def search_chats(
    query: str,
    user_id: str = "admin",
    scope: str = "all",
    session_id: Optional[str] = None,
    archived: bool = False,
    role_filter: str = "all",
    date_range: str = "all",
    limit: int = 60,
    max_per_session: int = 4,
) -> Dict[str, Any]:
    """
    Executes a fast, privacy-isolated search across the user's chats.
    """
    t0 = time.perf_counter()
    raw_q = (query or "").strip()
    scope = "current" if scope == "current" else "all"
    role_filter = role_filter if role_filter in ("all", "user", "assistant") else "all"
    date_range = date_range if date_range in ("all", "today", "7d", "30d") else "all"
    limit = max(1, min(int(limit or 60), 150))
    max_per_session = max(1, min(int(max_per_session or 4), 100))

    phrases, terms = _parse_query(raw_q)
    matched_terms = list(dict.fromkeys([*(phrases), *(terms)]))

    if not matched_terms:
        return {
            "ok": True,
            "query": raw_q,
            "matched_terms": [],
            "scope": scope,
            "archived": bool(archived),
            "is_incognito_scope": False,
            "groups": [],
            "total_matches": 0,
            "total_sessions": 0,
            "elapsed_ms": 0.0,
        }

    cutoff_ts = _cutoff_timestamp(date_range)

    # Special case: explicit search inside an open Incognito RAM session
    if scope == "current" and session_id:
        from hecos.memory.session_state import _ram_sessions
        if session_id in _ram_sessions:
            ram_res = _search_ram_current_session(
                session_id=session_id,
                phrases=phrases,
                terms=terms,
                role_filter=role_filter,
                cutoff_ts=cutoff_ts,
                limit=limit,
            )
            elapsed = round((time.perf_counter() - t0) * 1000, 1)
            return {
                "ok": True,
                "query": raw_q,
                "matched_terms": matched_terms,
                "scope": scope,
                "archived": False,
                "elapsed_ms": elapsed,
                **ram_res,
            }

    # Normal DB sessions (strictly active OR strictly archived, never mixed)
    allowed_sessions = _load_allowed_sessions(archived=bool(archived), scope=scope, current_session_id=session_id)
    if not allowed_sessions:
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        return {
            "ok": True,
            "query": raw_q,
            "matched_terms": matched_terms,
            "scope": scope,
            "archived": bool(archived),
            "is_incognito_scope": False,
            "groups": [],
            "total_matches": 0,
            "total_sessions": 0,
            "elapsed_ms": elapsed,
        }

    folded_needles = [_fold_accents(x) for x in matched_terms]

    # 1. Check matching session titles (accent-folded)
    title_matches: Dict[str, dict] = {}
    for sid, sinfo in allowed_sessions.items():
        if cutoff_ts and (sinfo.get("updated_at") or "") < cutoff_ts:
            continue
        if _matches_all_folded(sinfo.get("title") or "", folded_needles):
            title_matches[sid] = sinfo

    # 2. Query user vault history.db
    from hecos.memory.brain_interface import _db_path
    db_path = _db_path(user_id)

    matched_rows: Dict[int, dict] = {}  # keyed by history.id to dedup FTS + substring hits
    if os.path.exists(db_path):
        fts_ok = ensure_fts_index(db_path)
        allowed_ids = list(allowed_sessions.keys())
        placeholders = ",".join("?" for _ in allowed_ids)

        role_sql = ""
        if role_filter == "user":
            role_sql = " AND LOWER(h.role) = 'user'"
        elif role_filter == "assistant":
            role_sql = " AND LOWER(h.role) != 'user'"

        date_sql = ""
        date_params: List[Any] = []
        if cutoff_ts:
            date_sql = " AND h.timestamp >= ?"
            date_params.append(cutoff_ts)

        try:
            with sqlite3.connect(db_path, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()

                # 2a. Primary fast SQLite FTS5 BM25 query
                fts_expr = _build_fts5_match_expr(phrases, terms)
                if fts_ok and fts_expr:
                    try:
                        sql_fts = f"""
                            SELECT
                                h.id,
                                h.session_id,
                                h.role,
                                h.message,
                                h.timestamp,
                                bm25(history_fts) AS score,
                                (SELECT COUNT(*) FROM history h2 WHERE h2.session_id = h.session_id AND h2.id < h.id) AS msg_index
                            FROM history_fts
                            JOIN history h ON h.id = history_fts.rowid
                            WHERE history_fts MATCH ?
                              AND h.session_id IN ({placeholders})
                              {role_sql}
                              {date_sql}
                            ORDER BY score ASC, h.id DESC
                            LIMIT ?
                        """
                        params = [fts_expr, *allowed_ids, *date_params, limit * 3]
                        for r in cur.execute(sql_fts, params).fetchall():
                            d = dict(r)
                            matched_rows[d["id"]] = d
                    except sqlite3.OperationalError as fts_err:
                        logger.debug(f"[CHAT_SEARCH] FTS5 query fallback for '{raw_q}': {fts_err}")

                # 2b. Substring fallback (for symbols/code/paths or when FTS5 unavailable/empty)
                if (not fts_ok) or _needs_substring_fallback(raw_q, terms) or (not matched_rows):
                    # First narrow with case-insensitive LIKE on longest ASCII chunk when possible
                    like_clauses = []
                    like_params: List[Any] = []
                    for needle in matched_terms:
                        # Only add SQL LIKE when purely ASCII so accented chars aren't missed by SQLite ASCII-only LOWER()
                        if needle.isascii():
                            escaped = needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                            like_clauses.append("h.message LIKE ? ESCAPE '\\'")
                            like_params.append(f"%{escaped}%")
                    like_sql = (" AND " + " AND ".join(like_clauses)) if like_clauses else ""

                    sql_sub = f"""
                        SELECT
                            h.id,
                            h.session_id,
                            h.role,
                            h.message,
                            h.timestamp,
                            0.0 AS score,
                            (SELECT COUNT(*) FROM history h2 WHERE h2.session_id = h.session_id AND h2.id < h.id) AS msg_index
                        FROM history h
                        WHERE h.session_id IN ({placeholders})
                          {role_sql}
                          {date_sql}
                          {like_sql}
                        ORDER BY h.id DESC
                        LIMIT ?
                    """
                    scan_cap = max(limit * 4, 400) if not like_clauses else limit * 3
                    params = [*allowed_ids, *date_params, *like_params, scan_cap]
                    for r in cur.execute(sql_sub, params).fetchall():
                        d = dict(r)
                        if d["id"] in matched_rows:
                            continue
                        if _matches_all_folded(d.get("message") or "", folded_needles):
                            matched_rows[d["id"]] = d
        except Exception as e:
            logger.error(f"[CHAT_SEARCH] DB query error: {e}")

    # 3. Group hits by session and rank
    grouped: Dict[str, dict] = {}

    for row in matched_rows.values():
        sid = row["session_id"]
        sinfo = allowed_sessions.get(sid)
        if not sinfo:
            continue
        if sid not in grouped:
            grouped[sid] = {
                "session_id": sid,
                "title": sinfo.get("title") or "Chat senza titolo",
                "updated_at": sinfo.get("updated_at") or sinfo.get("created_at") or "",
                "is_archived": bool(sinfo.get("is_archived", 0)),
                "is_incognito": False,
                "title_matched": sid in title_matches,
                "best_score": float(row.get("score") or 0.0),
                "all_hits": [],
            }
        else:
            sc = float(row.get("score") or 0.0)
            if sc < grouped[sid]["best_score"]:
                grouped[sid]["best_score"] = sc

        snippet, in_thinking = _build_snippet(row.get("message") or "", phrases, terms)
        grouped[sid]["all_hits"].append({
            "message_id": row["id"],
            "session_id": sid,
            "msg_index": int(row["msg_index"]),
            "role": _norm_role(row.get("role", "")),
            "timestamp": row.get("timestamp") or "",
            "snippet": snippet,
            "in_thinking": in_thinking,
            "_score": float(row.get("score") or 0.0),
        })

    # Include title-only matches (sessions whose title matched even with 0 message hits under current role filter)
    if role_filter == "all":
        for sid, sinfo in title_matches.items():
            if sid not in grouped:
                grouped[sid] = {
                    "session_id": sid,
                    "title": sinfo.get("title") or "Chat senza titolo",
                    "updated_at": sinfo.get("updated_at") or sinfo.get("created_at") or "",
                    "is_archived": bool(sinfo.get("is_archived", 0)),
                    "is_incognito": False,
                    "title_matched": True,
                    "best_score": -10.0,  # Title matches rank high
                    "all_hits": [],
                }

    # Sort hits inside each group: chronological in 'current' scope, relevance+recency in 'all'
    per_sess_cap = limit if scope == "current" else max_per_session
    groups_list = []
    total_matches = 0
    for g in grouped.values():
        if scope == "current":
            g["all_hits"].sort(key=lambda h: h["msg_index"])
        else:
            g["all_hits"].sort(key=lambda h: (h["_score"], -(h["message_id"] or 0)))

        cnt = len(g["all_hits"])
        total_matches += cnt if cnt > 0 else (1 if g["title_matched"] else 0)
        clean_hits = [{k: v for k, v in h.items() if k != "_score"} for h in g["all_hits"][:per_sess_cap]]

        groups_list.append({
            "session_id": g["session_id"],
            "title": g["title"],
            "updated_at": g["updated_at"],
            "is_archived": g["is_archived"],
            "is_incognito": g["is_incognito"],
            "title_matched": g["title_matched"],
            "match_count": cnt,
            "hits": clean_hits,
            "_sort_key": (
                0 if g["title_matched"] else 1,
                g["best_score"],
                g["updated_at"],
            ),
        })

    # Rank groups: 1) title matches first, 2) best BM25 score (more negative = stronger),
    # 3) most recently updated (stable sort from least to most significant key)
    groups_list.sort(key=lambda x: x["updated_at"], reverse=True)
    groups_list.sort(key=lambda x: (0 if x["title_matched"] else 1, round(x["_sort_key"][1], 3)))

    final_groups = []
    for g in groups_list[:limit]:
        g.pop("_sort_key", None)
        final_groups.append(g)

    elapsed = round((time.perf_counter() - t0) * 1000, 1)
    return {
        "ok": True,
        "query": raw_q,
        "matched_terms": matched_terms,
        "scope": scope,
        "archived": bool(archived),
        "is_incognito_scope": False,
        "groups": final_groups,
        "total_matches": total_matches,
        "total_sessions": len(final_groups),
        "elapsed_ms": elapsed,
    }
