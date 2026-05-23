"""
MODULE: Messenger — WhatsApp Adapter  [BETA]
DESCRIPTION: Sends messages via WhatsApp using pywhatkit (session-less, opens browser)
             or whatsapp-web.py for a persistent session.
             Marked BETA because it relies on WhatsApp Web UI automation,
             which can break on WhatsApp updates.

STATUS: BETA — use Telegram for production-critical messaging.
"""

from __future__ import annotations
import time
import platform
import webbrowser
from urllib.parse import quote
from hecos.core.logging import logger

def send(cfg, recipient: str, text: str) -> str:
    """Send a WhatsApp message natively. Prioritizes the Desktop App (no new tabs) over the Web version."""
    if not cfg.enabled:
        return "⚠️ WhatsApp adapter is disabled. Enable it in Messenger settings."

    # Normalize phone number — must be in E.164 format e.g. +393331234567
    phone = recipient.strip()
    if not phone.startswith("+"):
        cc = getattr(cfg, "phone_country_code", "+39") or "+39"
        phone = cc + phone.lstrip("0")

    phone = phone.replace(" ", "").replace("-", "")

    try:
        import pyautogui  # type: ignore
        url_app = f"whatsapp://send?phone={phone}&text={quote(text)}"
        url_web = f"https://web.whatsapp.com/send?phone={phone}&text={quote(text)}"

        is_web = False
        if platform.system() == "Windows":
            import os
            try:
                # Try opening the native WhatsApp Desktop App (reuses existing window!)
                os.startfile(url_app)
                time.sleep(5) # App opens much faster than web
            except Exception:
                webbrowser.open(url_web)
                time.sleep(15)
                is_web = True
        else:
            webbrowser.open(url_web)
            time.sleep(15)
            is_web = True

        # Failsafe multiple enters to ensure focus and sending
        pyautogui.press('enter')
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(2)

        if is_web:
            # Clean up the browser tab we forced open
            pyautogui.hotkey('ctrl', 'w')
        
        logger.info("MESSENGER/WhatsApp", f"Message executed to {phone}")
        return f"✅ Messaggio WhatsApp inviato a `{phone}`."

    except ImportError:
        return "❌ WhatsApp: The 'pyautogui' library is required. Run: pip install pyautogui"
    except Exception as e:
        logger.warning("MESSENGER/WhatsApp", f"Send failed: {e}")
        return f"❌ WhatsApp send error: {e}"

def check(cfg) -> str:
    if not cfg.enabled:
        return "DISABLED"

    try:
        import pyautogui  # noqa: F401
        return "BETA (pyautogui ready — app/browser-based)"
    except ImportError:
        return "NOT INSTALLED (run: pip install pyautogui)"

