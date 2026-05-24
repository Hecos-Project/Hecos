"""
MODULE: Contacts Hooks
DESCRIPTION: Bridge layer between the Contacts plugin and other Hecos modules.
             - Messenger: WhatsApp/Telegram dispatch
             - Calendar:  Birthday reminder injection
             - Mail:      Future email module bridge (stub ready)
"""

from hecos.core.logging import logger


# ── WhatsApp / Messenger Bridge ───────────────────────────────────────────────

def send_whatsapp(contact_id: str, message: str) -> str:
    """
    Sends a WhatsApp message to a contact by looking up their WhatsApp number.
    Delegates to hecos.plugins.messenger. Returns a human-readable result string.
    """
    from hecos.plugins.contacts import store
    number = store.get_primary_field(contact_id, "whatsapp")
    if not number:
        # Fall back to primary phone number
        number = store.get_primary_field(contact_id, "phone")
    if not number:
        c = store.get_by_id(contact_id)
        name = c.get("display_name", contact_id) if c else contact_id
        return (f"⚠️ No WhatsApp number found for **{name}**. "
                f"Add one via the address book or use the `add_field` API.")
    try:
        from hecos.core.system.module_state import get_plugin_module
        messenger_module = get_plugin_module("MESSENGER")
        if not messenger_module or not hasattr(messenger_module, "tools"):
            return "⚠️ Messenger plugin is not available or not enabled."
        
        result = messenger_module.tools.send_message(to=number, text=message, platform="whatsapp")
        if result and result.startswith("❌"):
            return result
        c = store.get_by_id(contact_id)
        name = c.get("display_name", contact_id) if c else contact_id
        return f"💬 WhatsApp message sent to **{name}** ({number})."
    except ImportError:
        return "⚠️ Messenger plugin is not available or not enabled."
    except Exception as e:
        logger.debug("CONTACTS", f"send_whatsapp error: {e}")
        return f"⚠️ Failed to send WhatsApp: {e}"


def send_telegram(contact_id: str, message: str) -> str:
    """Sends a Telegram message to a contact by looking up their Telegram handle."""
    from hecos.plugins.contacts import store
    handle = store.get_primary_field(contact_id, "telegram")
    if not handle:
        c = store.get_by_id(contact_id)
        name = c.get("display_name", contact_id) if c else contact_id
        return f"⚠️ No Telegram handle found for **{name}**."
    try:
        from hecos.core.system.module_state import get_plugin_module
        messenger_module = get_plugin_module("MESSENGER")
        if not messenger_module or not hasattr(messenger_module, "tools"):
            return "⚠️ Messenger plugin is not available or not enabled."
        
        result = messenger_module.tools.send_message(to=handle, text=message, platform="telegram")
        if result and result.startswith("❌"):
            return result
        c = store.get_by_id(contact_id)
        name = c.get("display_name", contact_id) if c else contact_id
        return f"✈️ Telegram message sent to **{name}** (@{handle})."
    except ImportError:
        return "⚠️ Messenger plugin is not available or not enabled."
    except Exception as e:
        logger.debug("CONTACTS", f"send_telegram error: {e}")
        return f"⚠️ Failed to send Telegram: {e}"


# ── Mail Bridge (stub — ready for future Mail plugin) ─────────────────────────

def get_primary_email(contact_id: str) -> str | None:
    """Returns the primary email for a contact (used by a future Mail plugin)."""
    from hecos.plugins.contacts import store
    return store.get_primary_field(contact_id, "email")


def send_email(contact_id: str, subject: str, body: str) -> str:
    """Stub: sends an email to a contact. Requires a future Mail plugin."""
    email = get_primary_email(contact_id)
    if not email:
        return "⚠️ No email address found for this contact."
    try:
        from hecos.plugins.mail.dispatcher import send_mail  # Future module
        send_mail(to=email, subject=subject, body=body)
        return f"✉️ Email sent to {email}."
    except ImportError:
        return "⚠️ Mail plugin is not yet available. Stay tuned!"
    except Exception as e:
        return f"⚠️ Failed to send email: {e}"


# ── Calendar Birthday Bridge ───────────────────────────────────────────────────

def check_birthdays_today() -> list:
    """
    Returns a list of contacts whose birthday is today.
    Called by Calendar or a scheduler to generate reminders.
    """
    from hecos.plugins.contacts.store import get_birthdays_today
    return get_birthdays_today()


def inject_birthday_reminders(days_ahead: int = 7) -> list:
    """
    Injects upcoming birthday events into the Calendar plugin.
    Returns a list of contact display_names that had events created.
    """
    from hecos.plugins.contacts.store import get_birthdays_upcoming
    from datetime import datetime, timedelta
    injected = []
    try:
        from hecos.plugins.calendar import store as cal_store
    except ImportError:
        return []

    upcoming = get_birthdays_upcoming(days=days_ahead)
    for c in upcoming:
        days_left = c.get("days_until_birthday", 0)
        bday_dt   = datetime.utcnow() + timedelta(days=days_left)
        bday_iso  = bday_dt.strftime("%Y-%m-%dT00:00:00")
        name      = c.get("display_name", "?")
        # Check if already injected
        existing = cal_store.get_range(bday_iso, bday_iso + "Z")
        if any(e.get("title") == f"🎂 {name}" for e in existing):
            continue
        cal_store.add(
            title=f"🎂 {name}",
            start_iso=bday_iso,
            all_day=True,
            notes=f"Birthday of {name} — from Contacts plugin",
            color="#f472b6",  # Pink
            sync_source="contacts_birthday"
        )
        injected.append(name)
        logger.debug("CONTACTS", f"Birthday reminder injected for {name} on {bday_iso[:10]}")
    return injected
