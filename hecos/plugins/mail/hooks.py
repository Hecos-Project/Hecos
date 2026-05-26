"""
MODULE: Mail Hooks
DESCRIPTION: Integration helpers between the Mail plugin and other Hecos plugins.
             Provides contact email resolution via the Contacts plugin.
"""

from hecos.core.logging import logger


def get_contact_emails(name: str) -> list[str]:
    """
    Searches the Contacts plugin for email addresses belonging to a contact.
    Returns a list of email address strings.
    """
    try:
        from hecos.plugins.contacts import store as contacts_store
        results = contacts_store.search(name)
        emails = []
        for contact in results:
            for field in contact.get("fields", []):
                if field.get("field_type") == "email" and field.get("value"):
                    emails.append(field["value"])
        # Also check primary email if stored
        for contact in results:
            primary = contacts_store.get_primary_field(contact["id"], "email")
            if primary and primary not in emails:
                emails.append(primary)
        return list(dict.fromkeys(emails))  # deduplicate, preserve order
    except Exception as e:
        logger.debug("MAIL", f"get_contact_emails error: {e}")
        return []


def send_mail_to_contact(name: str, subject: str, body: str,
                          cfg: dict = None, username: str = "admin") -> str:
    """
    Sends an email to a contact looked up by name from the Contacts plugin.
    Returns a user-friendly LLM result string.
    """
    emails = get_contact_emails(name)
    if not emails:
        return f"⚠️ No email address found for contact '{name}'. Check the address book."

    from hecos.plugins.mail.smtp_client import build_smtp_client
    client = build_smtp_client(cfg or {}, username)
    ok, msg = client.send(to=emails[0], subject=subject, body=body)
    if ok:
        return f"📧 Email sent to **{name}** ({emails[0]}): _{subject}_"
    return f"⚠️ Failed to send email to {name}: {msg}"


def resolve_to_addresses(to_raw: str, username: str = "admin") -> list[str]:
    """
    Resolves a 'to' string to a list of actual email addresses.
    If a token is not a valid email, tries to look it up in the Contacts plugin.
    """
    import re
    tokens = [t.strip() for t in to_raw.split(",") if t.strip()]
    resolved = []
    for token in tokens:
        if re.match(r"[^@]+@[^@]+\.[^@]+", token):
            resolved.append(token)
        else:
            # Try contacts lookup
            emails = get_contact_emails(token)
            if emails:
                resolved.extend(emails[:1])  # Use the primary email only
                logger.debug("MAIL", f"Resolved '{token}' → {emails[0]}")
            else:
                resolved.append(token)  # Pass through, SMTP will reject if invalid
    return resolved
