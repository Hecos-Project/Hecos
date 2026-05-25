"""
MODULE: Mail Credential Helper
DESCRIPTION: Reads and saves SMTP/IMAP credentials for the Mail plugin.

Priority order:
  1. Environment variables (HECOS_MAIL_ADDRESS, HECOS_MAIL_APP_PASSWORD) — .env file
  2. plugins.yaml MAIL block (mail_address, mail_app_password)

This ensures credentials are NEVER committed to GitHub.
To use .env, add these two lines to hecos/.env:
    HECOS_MAIL_ADDRESS=you@gmail.com
    HECOS_MAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
"""

import os
from hecos.core.logging import logger


# ── Config accessors ──────────────────────────────────────────────────────────

def _get_mail_cfg() -> dict:
    """Returns the MAIL section of plugins.yaml (already merged into ConfigManager.config)."""
    try:
        from hecos.app.config import ConfigManager
        return ConfigManager().config.get("plugins", {}).get("MAIL", {})
    except Exception as e:
        logger.error(f"[MAIL] Could not read MAIL config: {e}")
        return {}


def get_user_email(username: str = "admin") -> str:
    """
    Returns the mail address.
    Priority: HECOS_MAIL_ADDRESS env var > plugins.yaml mail_address
    """
    # 1. Try environment variable (.env)
    env_email = os.environ.get("HECOS_MAIL_ADDRESS", "").strip()
    if env_email:
        return env_email
    # 2. Fall back to plugins.yaml
    return (_get_mail_cfg().get("mail_address") or "").strip()


def get_user_app_password(username: str = "admin") -> str:
    """
    Returns the mail app-password.
    Priority: HECOS_MAIL_APP_PASSWORD env var > plugins.yaml mail_app_password
    """
    # 1. Try environment variable (.env)
    env_pwd = os.environ.get("HECOS_MAIL_APP_PASSWORD", "").strip()
    if env_pwd:
        return env_pwd
    # 2. Fall back to plugins.yaml
    return (_get_mail_cfg().get("mail_app_password") or "").strip()


def get_user_smtp_host_override(username: str = "admin") -> str:
    """Returns manual SMTP host override from MAIL config (empty = auto-detect)."""
    return (_get_mail_cfg().get("smtp_host") or "").strip()


def get_user_imap_host_override(username: str = "admin") -> str:
    """Returns manual IMAP host override from MAIL config (empty = auto-detect)."""
    return (_get_mail_cfg().get("imap_host") or "").strip()


def set_mail_credentials(email: str, password: str) -> bool:
    """
    Saves email address and/or app password into plugins.yaml MAIL section.
    Note: If env vars HECOS_MAIL_ADDRESS / HECOS_MAIL_APP_PASSWORD are set,
    those take priority at runtime. Saving here ensures persistence across restarts.
    """
    try:
        from hecos.app.config import ConfigManager
        cm = ConfigManager()
        # Use update_config to go through full validation + save pipeline
        update = {}
        if email:
            update["mail_address"] = email.strip()
        if password:
            update["mail_app_password"] = password.strip()
        if not update:
            return False
        # Merge into MAIL plugin block
        current_plugins = cm.config.get("plugins", {})
        current_mail = current_plugins.get("MAIL", {})
        current_mail.update(update)
        cm.config.setdefault("plugins", {})["MAIL"] = current_mail
        ok = cm.save()
        if ok:
            logger.info(f"[MAIL] Credentials saved to plugins.yaml (fields: {list(update.keys())})")
        else:
            logger.error("[MAIL] cm.save() returned False — check CONFIG logs")
        return ok
    except Exception as e:
        logger.error(f"[MAIL] set_mail_credentials error: {e}")
        return False


def set_user_app_password(username: str, password: str) -> bool:
    """Alias kept for backwards compatibility — saves password into MAIL config."""
    return set_mail_credentials(email="", password=password)


# ── Provider auto-detection ────────────────────────────────────────────────────

_PROVIDER_MAP = {
    "gmail.com":      {"smtp_host": "smtp.gmail.com",         "smtp_port": 587, "smtp_security": "STARTTLS",
                       "imap_host": "imap.gmail.com",          "imap_port": 993, "imap_security": "SSL"},
    "googlemail.com": {"smtp_host": "smtp.gmail.com",         "smtp_port": 587, "smtp_security": "STARTTLS",
                       "imap_host": "imap.gmail.com",          "imap_port": 993, "imap_security": "SSL"},
    "outlook.com":    {"smtp_host": "smtp-mail.outlook.com",  "smtp_port": 587, "smtp_security": "STARTTLS",
                       "imap_host": "outlook.office365.com",   "imap_port": 993, "imap_security": "SSL"},
    "hotmail.com":    {"smtp_host": "smtp-mail.outlook.com",  "smtp_port": 587, "smtp_security": "STARTTLS",
                       "imap_host": "outlook.office365.com",   "imap_port": 993, "imap_security": "SSL"},
    "live.com":       {"smtp_host": "smtp-mail.outlook.com",  "smtp_port": 587, "smtp_security": "STARTTLS",
                       "imap_host": "outlook.office365.com",   "imap_port": 993, "imap_security": "SSL"},
    "yahoo.com":      {"smtp_host": "smtp.mail.yahoo.com",    "smtp_port": 587, "smtp_security": "STARTTLS",
                       "imap_host": "imap.mail.yahoo.com",     "imap_port": 993, "imap_security": "SSL"},
    "icloud.com":     {"smtp_host": "smtp.mail.me.com",       "smtp_port": 587, "smtp_security": "STARTTLS",
                       "imap_host": "imap.mail.me.com",        "imap_port": 993, "imap_security": "SSL"},
    "libero.it":      {"smtp_host": "smtp.libero.it",         "smtp_port": 465, "smtp_security": "TLS",
                       "imap_host": "imap.libero.it",          "imap_port": 993, "imap_security": "SSL"},
    "virgilio.it":    {"smtp_host": "out.virgilio.it",        "smtp_port": 465, "smtp_security": "TLS",
                       "imap_host": "in.virgilio.it",          "imap_port": 993, "imap_security": "SSL"},
    "tiscali.it":     {"smtp_host": "smtp.tiscali.it",        "smtp_port": 465, "smtp_security": "TLS",
                       "imap_host": "imap.tiscali.it",         "imap_port": 993, "imap_security": "SSL"},
}


def auto_detect_provider(email: str) -> dict | None:
    """Returns SMTP/IMAP settings for a known provider, or None."""
    if not email or "@" not in email:
        return None
    domain = email.split("@")[-1].lower()
    return _PROVIDER_MAP.get(domain)


def resolve_mail_settings(cfg: dict, username: str = "admin") -> dict:
    """
    Builds the effective SMTP/IMAP settings by merging:
    1. Auto-detected provider settings (based on mail_address domain)
    2. Config file overrides (smtp_host, smtp_port, etc.)
    Priority for credentials: env vars > plugins.yaml fields
    """
    email    = get_user_email(username)
    password = get_user_app_password(username)

    settings = {}
    if cfg.get("auto_detect_provider", True) and email:
        detected = auto_detect_provider(email)
        if detected:
            settings.update(detected)
            logger.debug(f"[MAIL] Auto-detected provider for {email.split('@')[-1]}")

    # Merge explicit config overrides (non-empty values only)
    for key in ("smtp_host", "smtp_port", "smtp_security", "imap_host", "imap_port", "imap_security"):
        val = cfg.get(key)
        if val and str(val).strip():
            settings[key] = val

    settings["username"] = email
    settings["password"] = password
    settings["email"]    = email
    return settings
