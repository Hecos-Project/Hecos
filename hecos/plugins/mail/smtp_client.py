"""
MODULE: Mail SMTP Client
DESCRIPTION: Sends emails via SMTP with TLS/STARTTLS/PLAIN support.
             Credentials and server settings are resolved from the user profile
             via credential_helper.resolve_mail_settings().
"""

import smtplib
import ssl
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr, parseaddr
from datetime import datetime
from hecos.core.logging import logger


class SmtpClient:
    """SMTP client supporting TLS (465), STARTTLS (587), and PLAIN (25)."""

    def __init__(self, host: str, port: int, security: str,
                 username: str, password: str, display_name: str = ""):
        self.host         = host
        self.port         = int(port)
        self.security     = (security or "STARTTLS").upper()
        self.username     = username
        self.password     = password
        self.display_name = display_name or username

    def send(self, to: str | list, subject: str, body: str,
             cc: str = "", bcc: str = "", reply_to_msg_id: str = "",
             attach_paths: list = None, is_html: bool = False,
             in_reply_to: str = "") -> tuple[bool, str]:
        """
        Sends an email. Returns (success: bool, message: str).
        `to` can be a comma-separated string or a list.
        """
        if not self.host:
            return False, "SMTP host not configured."
        if not self.username:
            return False, "Sender email not configured. Insert your email in the Mail Config panel."
        if not self.password:
            return False, "App password not configured. Insert your app-password in the Mail Config panel."

        # Normalise recipients
        def _split(s):
            if isinstance(s, list):
                return [x.strip() for x in s if x.strip()]
            return [x.strip() for x in (s or "").split(",") if x.strip()]

        to_list  = _split(to)
        cc_list  = _split(cc)
        bcc_list = _split(bcc)
        all_rcpt = to_list + cc_list + bcc_list

        if not all_rcpt:
            return False, "No recipients specified."

        # Build message
        msg = MIMEMultipart("alternative" if is_html else "mixed")
        msg["Subject"] = subject
        msg["From"]    = formataddr((self.display_name, self.username))
        msg["To"]      = ", ".join(to_list)
        if cc_list:
            msg["Cc"]  = ", ".join(cc_list)
        msg["Date"]    = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
            msg["References"]  = in_reply_to

        # Add body
        if is_html:
            msg.attach(MIMEText(body, "html", "utf-8"))
        else:
            msg.attach(MIMEText(body, "plain", "utf-8"))

        # Attach files
        for path in (attach_paths or []):
            try:
                with open(path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{os.path.basename(path)}"'
                )
                msg.attach(part)
            except Exception as e:
                logger.warning(f"[MAIL] Could not attach {path}: {e}")

        # Send
        try:
            ctx = ssl.create_default_context()
            if self.security == "TLS":
                with smtplib.SMTP_SSL(self.host, self.port, context=ctx) as server:
                    server.login(self.username, self.password)
                    server.sendmail(self.username, all_rcpt, msg.as_bytes())
            else:  # STARTTLS or PLAIN
                with smtplib.SMTP(self.host, self.port) as server:
                    server.ehlo()
                    if self.security == "STARTTLS":
                        server.starttls(context=ctx)
                        server.ehlo()
                    server.login(self.username, self.password)
                    server.sendmail(self.username, all_rcpt, msg.as_bytes())

            logger.info(f"[MAIL] Email sent to {', '.join(to_list)} | subject: {subject}")
            return True, f"Email sent to {', '.join(to_list)}."
        except smtplib.SMTPAuthenticationError:
            msg = "Authentication failed. Check your email and app-password in the Mail config panel."
            logger.error(f"[MAIL] SMTP auth error: {self.username}@{self.host}")
            return False, msg
        except smtplib.SMTPConnectError as e:
            logger.error(f"[MAIL] SMTP connect error: {e}")
            return False, f"Cannot connect to SMTP server {self.host}:{self.port}."
        except Exception as e:
            logger.error(f"[MAIL] SMTP send error: {e}")
            return False, f"Send error: {e}"

    def test_connection(self) -> tuple[bool, str]:
        """Tests the SMTP connection and login without sending anything."""
        if not self.host:
            return False, "SMTP host not configured."
        try:
            ctx = ssl.create_default_context()
            if self.security == "TLS":
                with smtplib.SMTP_SSL(self.host, self.port, context=ctx, timeout=10) as server:
                    server.login(self.username, self.password)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                    server.ehlo()
                    if self.security == "STARTTLS":
                        server.starttls(context=ctx)
                        server.ehlo()
                    server.login(self.username, self.password)
            return True, f"SMTP connection OK ({self.host}:{self.port} / {self.security})"
        except smtplib.SMTPAuthenticationError:
            return False, "SMTP authentication failed. Check credentials."
        except Exception as e:
            return False, f"SMTP connection failed: {e}"


def build_smtp_client(cfg: dict, username: str = "admin") -> SmtpClient:
    """Factory: builds a SmtpClient from resolved settings."""
    from hecos.plugins.mail.credential_helper import resolve_mail_settings
    s = resolve_mail_settings(cfg, username)
    return SmtpClient(
        host=s.get("smtp_host", ""),
        port=s.get("smtp_port", 587),
        security=s.get("smtp_security", "STARTTLS"),
        username=s.get("email", ""),
        password=s.get("password", ""),
        display_name=s.get("display_name", "")
    )
