"""
MODULE: Messenger — WhatsApp Adapter  [BETA]
DESCRIPTION: Sends messages via WhatsApp Web using the existing Playwright/CDP browser
             already connected in Hecos browser engine. No blind pyautogui needed.
             Falls back to pyautogui+webbrowser if Playwright is unavailable.

STATUS: BETA — relies on WhatsApp Web UI selectors which can break on WA updates.
"""

from __future__ import annotations
import time
import platform
import threading
from urllib.parse import quote
from hecos.core.logging import logger

# ── WhatsApp Web selectors (update here if WA changes UI) ──────────────────
_WA_MSG_BOX_SELECTOR  = 'div[contenteditable="true"][data-tab="10"]'
_WA_MSG_BOX_FALLBACK  = 'div[contenteditable="true"][title="Type a message"]'
_WA_MSG_SENT_SELECTOR = 'span[data-icon="msg-check"], span[data-icon="msg-dblcheck"]'
_WA_LOADING_SELECTOR  = 'div[data-testid="intro-md-beta-logo-dark"], div[data-testid="qrcode"]'


def _send_via_playwright(phone: str, text: str, send_as_single_block: bool = True) -> str:
    """
    Usa un subprocess per inviare il messaggio via Playwright/CDP.
    Questo evita il crash "Cannot switch to a different thread" (greenlet error)
    che avviene se si usa sync_playwright da un thread AI diverso da quello principale.
    """
    import subprocess
    import sys
    import json
    import os

    worker_script = os.path.join(os.path.dirname(__file__), "whatsapp_cdp_worker.py")
    if not os.path.exists(worker_script):
        return "FALLBACK_PYAUTOGUI"

    input_data = json.dumps({"phone": phone, "text": text, "single_block": send_as_single_block})

    try:
        # Esegui il worker in un subprocess isolato
        result = subprocess.run(
            [sys.executable, worker_script],
            input=input_data,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=60
        )
        
        output = result.stdout.strip()
        
        # Gestisci errori del subprocess
        if result.returncode != 0:
            logger.warning("MESSENGER/WhatsApp", f"Subprocess CDP terminato con errore: {result.stderr}")
            return "FALLBACK_PYAUTOGUI"
            
        if not output or "FALLBACK_PYAUTOGUI" in output:
            return "FALLBACK_PYAUTOGUI"
            
        # Ritorna l'output testuale stampato dal worker (es: "✅ Messaggio inviato...")
        return output
        
    except subprocess.TimeoutExpired:
        logger.warning("MESSENGER/WhatsApp", "Timeout CDP worker (60s).")
        return "FALLBACK_PYAUTOGUI"
    except Exception as e:
        logger.warning("MESSENGER/WhatsApp", f"Errore esecuzione CDP worker: {e}")
        return "FALLBACK_PYAUTOGUI"


def send(cfg, recipient: str, text: str, is_app_open: bool = False) -> str:
    """Send a WhatsApp message. Uses CDP/Playwright if available, falls back to pyautogui."""
    if not cfg.enabled:
        return "⚠️ WhatsApp adapter disabilitato. Abilitalo nelle impostazioni Messenger."

    # Normalize phone number ONLY if it looks like a number (no letters)
    phone = recipient.strip()
    has_letters = any(c.isalpha() for c in phone)
    
    if not has_letters:
        if not phone.startswith("+"):
            cc = getattr(cfg, "phone_country_code", "+39") or "+39"
            phone = cc + phone.lstrip("0")
        phone = phone.replace(" ", "").replace("-", "")

    # ── Try Playwright/CDP first (recommended) ──────────────────────────────
    try:
        from hecos.modules.browser import engine  # noqa: F401 — just check availability
        logger.info("MESSENGER/WhatsApp", f"Invio via Playwright/CDP a {phone}...")
        single_block = getattr(cfg.whatsapp, "send_as_single_block", True)
        result = _send_via_playwright(phone, text, single_block)
        if result != "FALLBACK_PYAUTOGUI":
            logger.info("MESSENGER/WhatsApp", f"Risultato invio: {result}")
            return result
        else:
            logger.info("MESSENGER/WhatsApp", "Browser CDP non connesso — fallback a pyautogui.")
    except ImportError:
        logger.warning("MESSENGER/WhatsApp", "Browser engine non disponibile — uso fallback pyautogui.")

    # ── Fallback: pyautogui blind send ─────────────────────────────────────
    return _send_via_pyautogui(phone, text, is_app_open)


def _send_via_pyautogui(phone: str, text: str, is_app_open: bool) -> str:
    """Legacy fallback: opens WhatsApp Web in a browser tab and uses pyautogui to press Enter."""
    import webbrowser

    url_web = f"https://web.whatsapp.com/send?phone={phone}&text={quote(text)}"

    # Auto-detect if WhatsApp Desktop app is running on Windows
    if not is_app_open and platform.system() == "Windows":
        import subprocess
        try:
            output = subprocess.check_output('tasklist /FI "IMAGENAME eq WhatsApp.exe"', shell=True).decode("utf-8", errors="ignore")
            if "WhatsApp.exe" in output:
                is_app_open = True
        except Exception as e:
            logger.debug("MESSENGER/WhatsApp", f"Auto-detect WhatsApp.exe fallito: {e}")

    try:
        import pyautogui  # type: ignore

        def _bg_worker():
            try:
                import os
                url_app = f"whatsapp://send?phone={phone}&text={quote(text)}"
                is_web = False
                if platform.system() == "Windows":
                    try:
                        os.startfile(url_app)
                        time.sleep(2 if is_app_open else 10)
                    except Exception:
                        webbrowser.open(url_web)
                        time.sleep(3 if is_app_open else 20)
                        is_web = True
                else:
                    webbrowser.open(url_web)
                    time.sleep(3 if is_app_open else 20)
                    is_web = True

                time.sleep(1)
                pyautogui.press("enter")
                time.sleep(1)
                pyautogui.press("enter")
                time.sleep(2)

                if is_web:
                    pyautogui.hotkey("ctrl", "w")

                logger.warning(
                    "MESSENGER/WhatsApp",
                    f"[FALLBACK pyautogui] Invio cieco eseguito per {phone} — "
                    "nessuna verifica possibile. Considera di usare il browser CDP."
                )
            except Exception as e:
                logger.warning("MESSENGER/WhatsApp", f"[FALLBACK] Background thread fallito: {e}")

        threading.Thread(target=_bg_worker, daemon=True).start()
        logger.warning("MESSENGER/WhatsApp", f"[FALLBACK pyautogui] Thread avviato per {phone} — nessuna verifica invio.")
        return (
            f"⚠️ [FALLBACK] Procedura pyautogui avviata per `{phone}`. "
            "Nessuna verifica reale possibile (metodo cieco). "
            "Per invii affidabili, usa il browser CDP. "
            "Attention: CDP browser not active, CDP port closed or browser not running. Open: Tray Dashboard for more information."
        )

    except ImportError:
        return "❌ WhatsApp: 'pyautogui' non installato e browser CDP non disponibile. Esegui: pip install pyautogui"
    except Exception as e:
        logger.warning("MESSENGER/WhatsApp", f"Fallback send fallito: {e}")
        return f"❌ Errore WhatsApp send: {e}"


def check(cfg) -> str:
    if not cfg.enabled:
        return "DISABLED"

    # Check Playwright availability (preferred)
    try:
        from hecos.modules.browser import engine
        from playwright.sync_api import sync_playwright  # noqa: F401
        cdp_status = "CDP connesso" if engine.is_running() else "CDP non connesso (browser non avviato). Attention: CDP browser not active, CDP port closed or browser not running. Open: Tray Dashboard for more information."
        return f"BETA (Playwright pronto — {cdp_status})"
    except ImportError:
        pass

    # Fallback: check pyautogui
    try:
        import pyautogui  # noqa: F401
        return "BETA [FALLBACK] (pyautogui pronto — browser CDP non disponibile)"
    except ImportError:
        return "NOT INSTALLED (esegui: pip install playwright oppure pip install pyautogui)"
