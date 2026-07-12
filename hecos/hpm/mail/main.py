"""
MODULE: Mail Plugin â€” LLM Tools
DESCRIPTION: MailTools class exposing all mail operations as Hecos LLM tools.
             Loaded at boot via plugin manifest (is_class_based: true, on_load: true).
"""

from hecos.core.logging import logger


class MailTools:
    """Hecos Mail plugin â€” exposes email operations as LLM tools."""

    def __init__(self, config=None):
        self._cfg = config or {}
        self.tag  = "MAIL"
        self.desc = "Email plugin â€” send, receive, search and manage emails via SMTP/IMAP."

    # â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _mail_cfg(self) -> dict:
        """Returns the MAIL section of the current config."""
        return self._cfg.get("plugins", {}).get("MAIL", self._cfg)

    def _smtp(self, username: str = "admin"):
        from hecos.hpm.mail.smtp_client import build_smtp_client
        return build_smtp_client(self._mail_cfg(), username)

    def _imap(self, username: str = "admin"):
        from hecos.hpm.mail.imap_client import build_imap_client
        return build_imap_client(self._mail_cfg(), username)

    # â”€â”€ LLM Tools â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def send_email(self, to: str, subject: str, body: str,
                   cc: str = "", bcc: str = "",
                   is_html: bool = False) -> str:
        """Sends an email to one or more recipients."""
        try:
            from hecos.hpm.mail.hooks import resolve_to_addresses
            # Resolve contact names to actual email addresses
            resolved_to  = ", ".join(resolve_to_addresses(to))
            resolved_cc  = ", ".join(resolve_to_addresses(cc))  if cc  else ""
            resolved_bcc = ", ".join(resolve_to_addresses(bcc)) if bcc else ""

            client = self._smtp()
            ok, msg = client.send(
                to=resolved_to, subject=subject, body=body,
                cc=resolved_cc, bcc=resolved_bcc, is_html=is_html
            )
            if ok:
                return f"ðŸ“§ {msg}"
            return f"âš ï¸ {msg}"
        except Exception as e:
            logger.error(f"[MAIL] send_email error: {e}")
            return f"âš ï¸ Error sending email: {e}"

    def read_inbox(self, folder: str = "INBOX", limit: int = 10,
                   unread_only: bool = False) -> str:
        """Reads messages from a mail folder (INBOX, SENT, DRAFTS, TRASH)."""
        try:
            from hecos.hpm.mail import store
            cfg = self._mail_cfg()

            # Try to sync first if configured
            if cfg.get("sync_on_open", True):
                self._do_sync(folder, limit)

            msgs = store.list_folder(folder=folder.upper(), limit=limit,
                                     unread_only=unread_only)
            if not msgs:
                return f"ðŸ“­ No messages found in {folder}."

            lines = [f"ðŸ“§ **{folder} ({len(msgs)} messages):**\n"]
            for m in msgs:
                status = "ðŸ”µ " if not m.get("read") else "   "
                star   = "â­ " if m.get("starred") else ""
                lines.append(
                    f"{status}{star}**{m.get('subject', '(no subject)')}**\n"
                    f"   From: {m.get('from_addr', '?')} | {m.get('date', '')[:10]}\n"
                    f"   {m.get('preview', '')[:100]}\n"
                    f"   _ID: `{m['id'][:8]}`_"
                )
            return "\n\n".join(lines)
        except Exception as e:
            logger.error(f"[MAIL] read_inbox error: {e}")
            return f"âš ï¸ Error reading {folder}: {e}"

    def search_emails(self, query: str, folder: str = None, limit: int = 10) -> str:
        """Searches emails by keyword across subject, sender and body."""
        try:
            from hecos.hpm.mail import store
            msgs = store.search_messages(query=query, folder=folder, limit=limit)
            if not msgs:
                return f"ðŸ“­ No emails found matching '{query}'."

            lines = [f"ðŸ” **Search results for '{query}' ({len(msgs)}):**\n"]
            for m in msgs:
                folder_tag = f"[{m.get('folder', '?')}]"
                lines.append(
                    f"{folder_tag} **{m.get('subject', '(no subject)')}**\n"
                    f"  From: {m.get('from_addr', '?')} | {m.get('date', '')[:10]}\n"
                    f"  {m.get('preview', '')[:100]}\n"
                    f"  _ID: `{m['id'][:8]}`_"
                )
            return "\n\n".join(lines)
        except Exception as e:
            logger.error(f"[MAIL] search_emails error: {e}")
            return f"âš ï¸ Search error: {e}"

    def reply_email(self, message_id: str, body: str, reply_all: bool = False) -> str:
        """Replies to an email."""
        try:
            from hecos.hpm.mail import store
            msg = store.get_message(message_id) or self._find_by_prefix(message_id)
            if not msg:
                return f"âš ï¸ Message ID '{message_id}' not found."

            to_addr = msg.get("from_addr", "")
            subject = msg.get("subject", "")
            if not subject.lower().startswith("re:"):
                subject = "Re: " + subject

            cc = msg.get("to_addrs", "") if reply_all else ""

            client = self._smtp()
            ok, result = client.send(
                to=to_addr, subject=subject, body=body, cc=cc,
                in_reply_to=msg.get("message_id_header", "")
            )
            if ok:
                store.mark_read(msg["id"], True)
                return f"ðŸ“§ Reply sent to **{to_addr}**."
            return f"âš ï¸ Reply failed: {result}"
        except Exception as e:
            logger.error(f"[MAIL] reply_email error: {e}")
            return f"âš ï¸ Error replying: {e}"

    def forward_email(self, message_id: str, to: str, body: str = "") -> str:
        """Forwards an email to other recipients."""
        try:
            from hecos.hpm.mail import store
            from hecos.hpm.mail.hooks import resolve_to_addresses
            msg = store.get_message(message_id) or self._find_by_prefix(message_id)
            if not msg:
                return f"âš ï¸ Message ID '{message_id}' not found."

            subject = msg.get("subject", "")
            if not subject.lower().startswith("fwd:"):
                subject = "Fwd: " + subject

            fwd_body = body + "\n\n---------- Forwarded message ----------\n"
            fwd_body += f"From: {msg.get('from_addr', '')}\n"
            fwd_body += f"Date: {msg.get('date', '')}\n"
            fwd_body += f"Subject: {msg.get('subject', '')}\n\n"
            fwd_body += msg.get("body_text", "")

            resolved = ", ".join(resolve_to_addresses(to))
            client = self._smtp()
            ok, result = client.send(to=resolved, subject=subject, body=fwd_body)
            if ok:
                return f"ðŸ“§ Email forwarded to **{resolved}**."
            return f"âš ï¸ Forward failed: {result}"
        except Exception as e:
            logger.error(f"[MAIL] forward_email error: {e}")
            return f"âš ï¸ Error forwarding: {e}"

    def delete_email(self, message_id: str, permanent: bool = False) -> str:
        """Deletes or trashes an email."""
        try:
            from hecos.hpm.mail import store
            msg = store.get_message(message_id) or self._find_by_prefix(message_id)
            if not msg:
                return f"âš ï¸ Message '{message_id}' not found."

            if permanent:
                store.delete_message(msg["id"])
                return f"ðŸ—‘ï¸ Email **{msg.get('subject', '')}** permanently deleted."
            else:
                store.move_message(msg["id"], "TRASH")
                return f"ðŸ—‘ï¸ Email **{msg.get('subject', '')}** moved to Trash."
        except Exception as e:
            logger.error(f"[MAIL] delete_email error: {e}")
            return f"âš ï¸ Error deleting email: {e}"

    def move_email(self, message_id: str, target_folder: str) -> str:
        """Moves an email to another folder."""
        try:
            from hecos.hpm.mail import store
            msg = store.get_message(message_id) or self._find_by_prefix(message_id)
            if not msg:
                return f"âš ï¸ Message '{message_id}' not found."
            store.move_message(msg["id"], target_folder.upper())
            return f"ðŸ“ Email moved to **{target_folder}**."
        except Exception as e:
            return f"âš ï¸ Error moving email: {e}"

    def save_draft(self, to: str = "", subject: str = "", body: str = "",
                   cc: str = "", bcc: str = "") -> str:
        """Saves an email as a draft."""
        try:
            from hecos.hpm.mail import store
            d = store.save_draft(to_addrs=to, cc=cc, bcc=bcc,
                                 subject=subject, body=body)
            return f"ðŸ’¾ Draft saved. (ID: `{d['id'][:8]}`)"
        except Exception as e:
            return f"âš ï¸ Error saving draft: {e}"

    def sync_inbox(self, folder: str = "INBOX") -> str:
        """Forces a sync of the specified folder from the IMAP server."""
        try:
            count = self._do_sync(folder, self._mail_cfg().get("max_messages", 100))
            return f"ðŸ”„ Inbox synced. {count} new message(s) fetched."
        except Exception as e:
            logger.error(f"[MAIL] sync_inbox error: {e}")
            return f"âš ï¸ Sync error: {e}"

    def get_email_addresses_for_contact(self, name: str) -> str:
        """Looks up email addresses for a contact from the address book."""
        from hecos.hpm.mail.hooks import get_contact_emails
        emails = get_contact_emails(name)
        if not emails:
            return f"ðŸ“‡ No email address found for contact '{name}'."
        formatted = "\n".join(f"  âœ‰ï¸ {e}" for e in emails)
        return f"ðŸ“‡ Email addresses for **{name}**:\n{formatted}"

    # â”€â”€ Internal helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _do_sync(self, folder: str = "INBOX", max_msgs: int = 100) -> int:
        """Performs IMAP sync, returns number of new messages fetched."""
        from hecos.hpm.mail import store
        try:
            client = self._imap()
            ok, err = client.connect()
            if not ok:
                raise ConnectionError(err)
            known = store.get_uid_set(folder.upper())
            messages = client.sync_folder(folder=folder, max_msgs=max_msgs,
                                          known_uids=known)
            client.disconnect()
            count = 0
            for msg in messages:
                store.upsert_message(msg)
                count += 1
            logger.debug(f"[MAIL] Synced {count} new messages in {folder}")
            return count
        except Exception as e:
            logger.warning(f"[MAIL] _do_sync error: {e}")
            return 0

    def _find_by_prefix(self, prefix: str) -> dict | None:
        """Finds a message by 8-char ID prefix."""
        from hecos.hpm.mail import store
        for folder in ("INBOX", "SENT", "DRAFTS", "TRASH"):
            msgs = store.list_folder(folder=folder, limit=200)
            for m in msgs:
                if m["id"].startswith(prefix):
                    return m
        return None


# â”€â”€ Singleton & on_load â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
tools = MailTools()


def on_load(config):
    """Called by module_scanner when the plugin is loaded (on_load: true in manifest)."""
    tools._cfg = config
    logger.debug("MAIL", "Plugin loaded and config injected.")

    # Register API routes (idempotent â€” safe to call even if already registered at boot)
    try:
        from hecos.hpm.mail.api import register_routes
        from hecos.modules.web_ui import get_app
        app = get_app()
        if app:
            register_routes(app)
    except Exception as e:
        logger.debug("MAIL", f"API route registration deferred: {e}")

