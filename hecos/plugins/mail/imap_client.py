"""
MODULE: Mail IMAP Client
DESCRIPTION: Fetches and syncs email from an IMAP server.
             Supports SSL (993) and STARTTLS (143).
             Resolves credentials from the user profile.
"""

import imaplib
import email as _email_lib
import email.header
import email.utils
import os
import uuid
from datetime import datetime
from hecos.core.logging import logger


# ── Folder name mapping ────────────────────────────────────────────────────────
# Maps our canonical names to IMAP folder names (provider-specific)
_FOLDER_ALIASES = {
    "INBOX":   ["INBOX"],
    "SENT":    ["Sent", "[Gmail]/Sent Mail", "Sent Items", "Sent Messages"],
    "DRAFTS":  ["Drafts", "[Gmail]/Drafts"],
    "TRASH":   ["Trash", "[Gmail]/Trash", "Deleted Items", "Deleted Messages"],
    "SPAM":    ["Spam", "[Gmail]/Spam", "Junk", "Junk Email"],
    "STARRED": ["[Gmail]/Starred", "Flagged"],
}


def _decode_header(value: str | bytes) -> str:
    if not value:
        return ""
    try:
        parts = email.header.decode_header(value)
        decoded = []
        for part, charset in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                decoded.append(str(part))
        return " ".join(decoded)
    except Exception:
        return str(value)


def _get_body(msg) -> tuple[str, str]:
    """Extracts plain-text and HTML body from a Message object."""
    plain = ""
    html  = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp  = str(part.get("Content-Disposition", ""))
            if "attachment" in disp:
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if ctype == "text/plain" and not plain:
                plain = text
            elif ctype == "text/html" and not html:
                html = text
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            content = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/html":
                html = content
            else:
                plain = content
    return plain, html


def _has_attachments(msg) -> bool:
    for part in msg.walk():
        disp = str(part.get("Content-Disposition", ""))
        if "attachment" in disp:
            return True
    return False


def _parse_msg(uid: int, raw: bytes, folder: str) -> dict:
    """Parses a raw IMAP message into a store-compatible dict."""
    msg = _email_lib.message_from_bytes(raw)

    subject  = _decode_header(msg.get("Subject", ""))
    from_raw = _decode_header(msg.get("From", ""))
    to_raw   = _decode_header(msg.get("To",   ""))
    cc_raw   = _decode_header(msg.get("Cc",   ""))
    reply_to = _decode_header(msg.get("Reply-To", ""))
    msg_id   = (msg.get("Message-ID") or "").strip()
    in_reply  = (msg.get("In-Reply-To") or "").strip()

    # Parse date
    date_raw = msg.get("Date", "")
    try:
        parsed_date = email.utils.parsedate_to_datetime(date_raw)
        date_str = parsed_date.isoformat()
    except Exception:
        date_str = date_raw

    plain, html = _get_body(msg)
    preview     = plain[:200].replace("\n", " ") if plain else ""

    # Flags from IMAP (will be updated by caller if available)
    mid = str(uuid.uuid4())

    return {
        "id":               mid,
        "uid":              uid,
        "folder":           folder,
        "subject":          subject,
        "from_addr":        from_raw,
        "to_addrs":         to_raw,
        "cc":               cc_raw,
        "reply_to":         reply_to,
        "body_text":        plain,
        "body_html":        html,
        "date":             date_str,
        "flags":            "",
        "read":             False,
        "starred":          False,
        "message_id_header": msg_id,
        "in_reply_to":      in_reply,
        "thread_id":        in_reply or msg_id or mid,
        "has_attachments":  _has_attachments(msg),
        "preview":          preview,
    }


class ImapClient:
    """IMAP client supporting SSL and STARTTLS."""

    def __init__(self, host: str, port: int, security: str,
                 username: str, password: str):
        self.host     = host
        self.port     = int(port)
        self.security = (security or "SSL").upper()
        self.username = username
        self.password = password
        self._conn    = None

    def connect(self) -> tuple[bool, str]:
        """Opens and authenticates the IMAP connection."""
        try:
            if self.security == "SSL":
                self._conn = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                self._conn = imaplib.IMAP4(self.host, self.port)
                self._conn.starttls()
            self._conn.login(self.username, self.password)
            return True, "OK"
        except imaplib.IMAP4.error as e:
            return False, f"IMAP auth error: {e}"
        except Exception as e:
            return False, f"IMAP connection error: {e}"

    def disconnect(self):
        try:
            if self._conn:
                self._conn.logout()
        except Exception:
            pass
        self._conn = None

    def resolve_folder(self, canonical: str) -> str:
        """Tries to map a canonical folder name to the actual IMAP folder name."""
        aliases = _FOLDER_ALIASES.get(canonical.upper(), [canonical])
        try:
            _, folders = self._conn.list()
            available = []
            for f in folders:
                decoded = f.decode() if isinstance(f, bytes) else f
                # Extract the folder name (last quoted or unquoted token)
                parts = decoded.split('"')
                name  = parts[-1].strip() if len(parts) > 1 else decoded.split()[-1]
                available.append(name)
            for alias in aliases:
                for avail in available:
                    if alias.lower() == avail.lower():
                        return avail
        except Exception:
            pass
        return aliases[0]  # fallback to first alias

    def sync_folder(self, folder: str = "INBOX", max_msgs: int = 100,
                    known_uids: set = None) -> list:
        """
        Fetches up to max_msgs messages from the folder.
        If known_uids is provided, skips already-cached messages (incremental sync).
        Returns a list of message dicts.
        """
        if not self._conn:
            ok, err = self.connect()
            if not ok:
                raise ConnectionError(err)

        real_folder = self.resolve_folder(folder)
        try:
            status, _ = self._conn.select(f'"{real_folder}"', readonly=True)
            if status != "OK":
                logger.warning(f"[MAIL] Cannot select folder: {real_folder}")
                return []

            _, data = self._conn.search(None, "ALL")
            uid_list = data[0].split() if data and data[0] else []
            if not uid_list:
                return []

            # Take the latest max_msgs UIDs
            uids_to_fetch = uid_list[-max_msgs:]
            messages = []

            for uid_bytes in reversed(uids_to_fetch):
                uid = int(uid_bytes)
                if known_uids and uid in known_uids:
                    continue

                _, raw_data = self._conn.fetch(uid_bytes, "(RFC822 FLAGS)")
                if not raw_data or raw_data[0] is None:
                    continue

                raw_email = None
                flags_str = ""
                for part in raw_data:
                    if isinstance(part, tuple):
                        flags_info = part[0].decode() if isinstance(part[0], bytes) else str(part[0])
                        if "FLAGS" in flags_info:
                            flags_str = flags_info
                        raw_email = part[1]

                if raw_email is None:
                    continue

                try:
                    parsed = _parse_msg(uid, raw_email, folder)
                    parsed["flags"] = flags_str
                    parsed["read"] = "\\Seen" in flags_str
                    parsed["starred"] = "\\Flagged" in flags_str
                    messages.append(parsed)
                except Exception as e:
                    logger.warning(f"[MAIL] Error parsing UID {uid}: {e}")

            return messages
        except Exception as e:
            logger.error(f"[MAIL] sync_folder error ({folder}): {e}")
            return []

    def fetch_message(self, uid: int, folder: str = "INBOX") -> dict | None:
        """Fetches a single message by UID."""
        if not self._conn:
            ok, err = self.connect()
            if not ok:
                return None

        real_folder = self.resolve_folder(folder)
        try:
            self._conn.select(f'"{real_folder}"', readonly=True)
            _, raw_data = self._conn.fetch(str(uid).encode(), "(RFC822 FLAGS)")
            if not raw_data or raw_data[0] is None:
                return None

            raw_email = None
            flags_str = ""
            for part in raw_data:
                if isinstance(part, tuple):
                    flags_info = part[0].decode() if isinstance(part[0], bytes) else str(part[0])
                    if "FLAGS" in flags_info:
                        flags_str = flags_info
                    raw_email = part[1]

            if raw_email is None:
                return None

            parsed = _parse_msg(uid, raw_email, folder)
            parsed["flags"] = flags_str
            parsed["read"]  = "\\Seen" in flags_str
            return parsed
        except Exception as e:
            logger.error(f"[MAIL] fetch_message UID={uid} error: {e}")
            return None

    def mark_seen(self, uid: int, folder: str = "INBOX", seen: bool = True):
        """Marks a message as read/unread on the server."""
        try:
            real_folder = self.resolve_folder(folder)
            self._conn.select(f'"{real_folder}"')
            flag = "+FLAGS" if seen else "-FLAGS"
            self._conn.store(str(uid).encode(), flag, "\\Seen")
        except Exception as e:
            logger.warning(f"[MAIL] mark_seen error: {e}")

    def test_connection(self) -> tuple[bool, str]:
        """Tests the IMAP connection."""
        if not self.host:
            return False, "IMAP host not configured."
        ok, msg = self.connect()
        if ok:
            self.disconnect()
            return True, f"IMAP connection OK ({self.host}:{self.port} / {self.security})"
        return False, msg

    def list_folders(self) -> list:
        """Returns a list of available IMAP folders on the server."""
        try:
            if not self._conn:
                self.connect()
            _, folders = self._conn.list()
            result = []
            for f in (folders or []):
                decoded = f.decode() if isinstance(f, bytes) else f
                parts = decoded.split('"')
                name = parts[-1].strip() if len(parts) > 1 else decoded.split()[-1]
                result.append(name)
            return result
        except Exception as e:
            logger.warning(f"[MAIL] list_folders error: {e}")
            return []


def build_imap_client(cfg: dict, username: str = "admin") -> ImapClient:
    """Factory: builds an ImapClient from resolved settings."""
    from hecos.plugins.mail.credential_helper import resolve_mail_settings
    s = resolve_mail_settings(cfg, username)
    return ImapClient(
        host=s.get("imap_host", ""),
        port=s.get("imap_port", 993),
        security=s.get("imap_security", "SSL"),
        username=s.get("email", ""),
        password=s.get("password", ""),
    )
