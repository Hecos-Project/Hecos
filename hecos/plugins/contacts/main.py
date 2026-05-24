"""
MODULE: Contacts Plugin — LLM Tools
DESCRIPTION: Exposes find_contact, add_contact, update_contact, delete_contact,
             list_contacts, send_whatsapp_to_contact as Hecos LLM tools.
             Loaded at boot via plugin manifest (is_class_based: true, on_load: true).
"""

from hecos.core.logging import logger


class ContactsTools:
    """Hecos Contacts plugin — exposes all address book LLM tools."""

    def __init__(self, config=None):
        self._cfg = config
        self.tag = "CONTACTS"
        self.desc = "Address Book plugin"

    # ── LLM Tools ─────────────────────────────────────────────────────────────

    def find_contact(self, query: str) -> str:
        """Searches the address book and returns matching contacts."""
        from hecos.plugins.contacts import store
        try:
            results = store.search(query)
            if not results:
                return f"📇 No contacts found matching '{query}'."
            lines = [f"📇 **Found {len(results)} contact(s):**"]
            for c in results[:10]:
                lines.append(self._format_contact_summary(c))
            return "\n\n".join(lines)
        except Exception as e:
            logger.debug("CONTACTS", f"find_contact error: {e}")
            return f"⚠️ Error searching contacts: {e}"

    def add_contact(self, first_name: str, last_name: str = None, display_name: str = None,
                    company: str = None, role: str = None, phone: str = None,
                    email: str = None, birthday: str = None, address: str = None,
                    notes: str = None, tags: str = None, label_color: str = None) -> str:
        """Creates a new contact in the address book."""
        from hecos.plugins.contacts import store
        try:
            # Parse birthday if provided
            bday_iso = None
            if birthday:
                bday_iso = self._parse_birthday(birthday)

            c = store.add(
                first_name=first_name, last_name=last_name, display_name=display_name,
                company=company, role=role, birthday=bday_iso,
                address=address, notes=notes, label_color=label_color, tags=tags
            )
            # Add primary phone/email as multi-value fields
            if phone:
                store.add_field(c["id"], "phone", phone, label="mobile", is_primary=True)
            if email:
                store.add_field(c["id"], "email", email, label="personal", is_primary=True)

            dn = c.get("display_name", first_name)
            return (f"📇 Contact **{dn}** added successfully! (ID: `{c['id'][:8]}`)\n"
                    f"{'📞 ' + phone if phone else ''} {'✉️ ' + email if email else ''}").strip()
        except Exception as e:
            logger.debug("CONTACTS", f"add_contact error: {e}")
            return f"⚠️ Failed to add contact: {e}"

    def update_contact(self, id_or_name: str, **kwargs) -> str:
        """Updates fields of an existing contact."""
        from hecos.plugins.contacts import store
        try:
            c = self._resolve(id_or_name)
            if not c:
                return f"⚠️ No contact found matching '{id_or_name}'. Use `find_contact` first."

            # Handle birthday parsing
            if kwargs.get("birthday"):
                kwargs["birthday"] = self._parse_birthday(kwargs["birthday"])

            updated = store.update(c["id"], **kwargs)
            if updated:
                return f"✅ Contact **{c['display_name']}** updated."
            return f"ℹ️ No changes made to **{c['display_name']}**."
        except Exception as e:
            logger.debug("CONTACTS", f"update_contact error: {e}")
            return f"⚠️ Error updating contact: {e}"

    def delete_contact(self, id_or_name: str) -> str:
        """Permanently deletes a contact."""
        from hecos.plugins.contacts import store
        try:
            c = self._resolve(id_or_name)
            if not c:
                return f"⚠️ No contact found matching '{id_or_name}'."
            name = c["display_name"]
            deleted = store.delete(c["id"])
            if deleted:
                return f"🗑️ Contact **{name}** has been deleted."
            return f"⚠️ Could not delete contact '{id_or_name}'."
        except Exception as e:
            logger.debug("CONTACTS", f"delete_contact error: {e}")
            return f"⚠️ Error deleting contact: {e}"

    def list_contacts(self, tag: str = None, limit: int = 20) -> str:
        """Returns a formatted list of contacts, optionally filtered by tag."""
        from hecos.plugins.contacts import store
        try:
            contacts = store.list_all(tag=tag, limit=limit)
            if not contacts:
                msg = f"No contacts with tag '{tag}'." if tag else "Your address book is empty."
                return f"📇 {msg}"
            header = f"📇 **Contacts{' [' + tag + ']' if tag else ''} ({len(contacts)}):**"
            lines = [header]
            for c in contacts:
                lines.append(self._format_contact_summary(c))
            return "\n\n".join(lines)
        except Exception as e:
            logger.debug("CONTACTS", f"list_contacts error: {e}")
            return f"⚠️ Error listing contacts: {e}"

    def send_whatsapp_to_contact(self, name: str, message: str) -> str:
        """Sends a WhatsApp message to a contact via the Messenger plugin."""
        from hecos.plugins.contacts import store, hooks
        try:
            c = store.find_by_name(name)
            if not c:
                return f"⚠️ No contact found matching '{name}'."
            result = hooks.send_whatsapp(c["id"], message)
            return result
        except Exception as e:
            logger.debug("CONTACTS", f"send_whatsapp_to_contact error: {e}")
            return f"⚠️ Error sending WhatsApp: {e}"

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _resolve(self, id_or_name: str):
        """Resolves a contact by ID prefix or display name."""
        from hecos.plugins.contacts import store
        c = store.get_by_id(id_or_name)
        if not c:
            c = store.find_by_name(id_or_name)
        return c

    def _format_contact_summary(self, c: dict) -> str:
        """Formats a single contact as a readable markdown block."""
        lines = [f"**{c.get('display_name', '?')}**"]
        if c.get("company"):
            lines.append(f"  🏢 {c['company']}" + (f" — {c['role']}" if c.get("role") else ""))
        if c.get("birthday"):
            lines.append(f"  🎂 {c['birthday']}")
        if c.get("tags"):
            lines.append(f"  🏷️ {c['tags']}")
        if c.get("address"):
            lines.append(f"  📍 {c['address']}")
        for f in c.get("fields", []):
            icon = {"phone": "📞", "email": "✉️", "whatsapp": "💬",
                    "telegram": "✈️", "instagram": "📸", "linkedin": "💼",
                    "twitter": "🐦"}.get(f["field_type"], "🔗")
            label = f.get("label") or f["field_type"]
            lines.append(f"  {icon} [{label}] {f['value']}")
        if c.get("notes"):
            lines.append(f"  📝 {c['notes']}")
        lines.append(f"  _ID: `{c['id'][:8]}`_")
        return "\n".join(lines)

    def _parse_birthday(self, when: str) -> str | None:
        """Parses a natural language or ISO birthday string to ISO date."""
        if not when:
            return None
        try:
            import dateparser
            dt = dateparser.parse(when, settings={"PREFER_DAY_OF_MONTH": "first",
                                                  "LANGUAGES": ["it", "en"]})
            if dt:
                return dt.strftime("%Y-%m-%d")
        except ImportError:
            pass
        try:
            from datetime import datetime as _dt
            return _dt.fromisoformat(when).strftime("%Y-%m-%d")
        except Exception:
            return when  # Return as-is if unparseable


# ── Singleton & Hooks ──────────────────────────────────────────────────────────
tools = ContactsTools()


def on_load(config):
    """Called by module_scanner when the plugin is loaded."""
    tools._cfg = config
    logger.debug("CONTACTS", "Plugin loaded and config injected.")
