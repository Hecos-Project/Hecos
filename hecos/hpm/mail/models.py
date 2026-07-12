"""
MODULE: Mail Plugin â€” Pydantic Models
DESCRIPTION: Data models for configuration and message validation.
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


# â”€â”€ Config Model â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class MailConfig(BaseModel):
    """Validated configuration for the Mail plugin (sourced from plugins.yaml / .env)."""
    enabled: bool = True
    lazy_load: bool = True
    mail_address: str = ""
    mail_app_password: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_security: str = "STARTTLS"      # TLS | STARTTLS | PLAIN
    imap_host: str = ""
    imap_port: int = 993
    imap_security: str = "SSL"            # SSL | STARTTLS
    max_messages: int = 100
    sync_on_open: bool = True
    auto_detect_provider: bool = True


# â”€â”€ Message Model â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class EmailAttachment(BaseModel):
    id: str = ""
    message_id: str = ""
    filename: str = ""
    size: int = 0
    content_type: str = "application/octet-stream"
    local_path: str = ""


class EmailMessage(BaseModel):
    """Represents a single email message."""
    id: str = ""
    uid: int = 0
    folder: str = "INBOX"
    subject: str = ""
    from_addr: str = ""
    to_addrs: str = ""
    cc: str = ""
    bcc: str = ""
    reply_to: str = ""
    body_text: str = ""
    body_html: str = ""
    date: str = ""
    flags: str = ""
    read: bool = False
    starred: bool = False
    thread_id: str = ""
    message_id_header: str = ""   # Message-ID header for threading
    in_reply_to: str = ""
    has_attachments: bool = False
    attachments: List[EmailAttachment] = Field(default_factory=list)
    preview: str = ""             # First ~200 chars of body for list view


class EmailDraft(BaseModel):
    """Represents an email draft."""
    id: str = ""
    to_addrs: str = ""
    cc: str = ""
    bcc: str = ""
    subject: str = ""
    body: str = ""
    is_html: bool = False
    created_at: str = ""
    updated_at: str = ""


class MailStats(BaseModel):
    """Counts per folder."""
    inbox: int = 0
    inbox_unread: int = 0
    sent: int = 0
    drafts: int = 0
    trash: int = 0
    starred: int = 0
