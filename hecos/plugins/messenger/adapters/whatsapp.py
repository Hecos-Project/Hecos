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


def _send_via_playwright(phone: str, text: str) -> str:
    """
    Use the Hecos browser engine (Playwright/CDP) to send a WhatsApp Web message.
    Returns a result string — either success ✅ or error ❌.
    """
    try:
        from hecos.modules.browser import engine
    except ImportError:
        return "❌ Browser engine non disponibile (hecos.modules.browser non trovato)."

    # Ensure browser is connected/running
    if not engine.is_running():
        logger.info("MESSENGER/WhatsApp", "Browser non connesso — tentativo di avvio...")
        if not engine.launch():
            err = engine.get_last_error()
            return f"❌ Impossibile avviare il browser CDP: {err}"

    browser = engine._BROWSER
    if not browser:
        return "❌ Browser CDP non disponibile dopo il lancio."

    url_web = f"https://web.whatsapp.com/send?phone={phone}&text={quote(text)}"

    try:
        # ── Find or create a WhatsApp Web tab ──────────────────────────────
        wa_page = None
        for ctx in browser.contexts:
            for pg in ctx.pages:
                try:
                    if "web.whatsapp.com" in pg.url:
                        wa_page = pg
                        logger.debug("MESSENGER/WhatsApp", f"Riutilizzo tab WA esistente: {pg.url}")
                        break
                except Exception:
                    pass
            if wa_page:
                break

        if wa_page is None:
            # Open a new tab inside the CDP context
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            wa_page = ctx.new_page()
            logger.info("MESSENGER/WhatsApp", "Aperto nuovo tab per WhatsApp Web.")

        # ── Navigate to the direct message URL ─────────────────────────────
        wa_page.bring_to_front()
        
        navigated_without_reload = False
        if "web.whatsapp.com" in wa_page.url:
            try:
                # Try to use the search box in the side panel to avoid a full page reload
                search_box = wa_page.locator('div#side div[contenteditable="true"]').first
                if search_box.is_visible(timeout=3000):
                    logger.info("MESSENGER/WhatsApp", "Uso la barra di ricerca per aprire la chat senza ricaricare.")
                    search_box.click()
                    wa_page.keyboard.press("Control+A")
                    wa_page.keyboard.press("Backspace")
                    search_box.type(phone, delay=30)
                    time.sleep(2) # Wait for search results
                    wa_page.keyboard.press("Enter")
                    time.sleep(1)
                    navigated_without_reload = True
            except Exception as e:
                logger.warning("MESSENGER/WhatsApp", f"Uso search box fallito, fallback al reload: {e}")

        if not navigated_without_reload:
            logger.info("MESSENGER/WhatsApp", f"Navigazione (con reload) verso: {url_web}")
            wa_page.goto(url_web, wait_until="domcontentloaded", timeout=30000)

        # ── Check for QR code (not logged in) ──────────────────────────────
        try:
            qr = wa_page.locator('div[data-testid="qrcode"]')
            if qr.is_visible(timeout=3000):
                return (
                    "❌ WhatsApp Web non è loggato. "
                    "Apri il browser, vai su web.whatsapp.com e scansiona il QR code, poi riprova."
                )
        except Exception:
            pass  # Not shown, good

        # ── Wait for the message input box ─────────────────────────────────
        msg_box = None
        for selector in [_WA_MSG_BOX_SELECTOR, _WA_MSG_BOX_FALLBACK]:
            try:
                loc = wa_page.locator(selector).first
                loc.wait_for(state="visible", timeout=20000)
                msg_box = loc
                logger.debug("MESSENGER/WhatsApp", f"Input box trovato con selettore: {selector}")
                break
            except Exception:
                continue

        if msg_box is None:
            # Screenshot for debug
            try:
                from hecos.modules.browser import interactor
                interactor.take_screenshot()
            except Exception:
                pass
            return (
                "❌ Non riesco a trovare la casella di testo di WhatsApp Web. "
                "Possibile causa: pagina non caricata, chat non trovata, o selettore obsoleto. "
                "Controlla il browser manualmente."
            )

        # ── Click and send the message ──────────────────────────────────────
        msg_box.click()
        time.sleep(0.3)

        # The text URL-encoded is already in the input via the WA URL — just press Enter
        # But verify the text is there first, or if we used the search box we MUST type it
        try:
            current_val = msg_box.inner_text()
            if navigated_without_reload or not current_val.strip():
                # Text not pre-filled (or we skipped URL reload) — type it manually
                logger.debug("MESSENGER/WhatsApp", "Digitazione manuale del messaggio.")
                # Assicuriamoci che la casella sia vuota prima di scrivere
                if current_val.strip():
                    wa_page.keyboard.press("Control+A")
                    wa_page.keyboard.press("Backspace")
                msg_box.type(text, delay=10)
                time.sleep(0.5)
        except Exception:
            # Fallback: just type
            msg_box.type(text, delay=10)
            time.sleep(0.5)

        # Press Enter to send (using Send button or global keyboard press for reliability)
        try:
            send_btn = wa_page.locator('span[data-icon="send"]').first
            if send_btn.is_visible(timeout=1000):
                send_btn.click()
                logger.info("MESSENGER/WhatsApp", "Pulsante Send cliccato.")
            else:
                wa_page.keyboard.press("Enter")
                logger.info("MESSENGER/WhatsApp", "Tasto Enter premuto (keyboard).")
        except Exception:
            wa_page.keyboard.press("Enter")
            logger.info("MESSENGER/WhatsApp", "Tasto Enter premuto (fallback).")

        # ── Verify message was sent (wait for checkmark) ────────────────────
        sent_ok = False
        try:
            wa_page.locator(_WA_MSG_SENT_SELECTOR).last.wait_for(state="visible", timeout=10000)
            sent_ok = True
            logger.info("MESSENGER/WhatsApp", "✅ Messaggio inviato confermato (checkmark visibile).")
        except Exception:
            # Checkmark not found — still might have sent (WA sometimes delays icons)
            logger.warning("MESSENGER/WhatsApp", "⚠️ Checkmark non confermato entro 10s — messaggio probabilmente inviato ma non verificato.")
            sent_ok = None  # uncertain

        if sent_ok is True:
            return f"✅ Messaggio WhatsApp inviato a `{phone}` e confermato (checkmark presente)."
        elif sent_ok is None:
            return f"⚠️ Messaggio WhatsApp inviato a `{phone}` ma non è stato possibile verificare il checkmark (controlla manualmente)."
        else:
            return f"❌ Invio fallito a `{phone}` — nessuna conferma dal browser."

    except Exception as e:
        logger.warning("MESSENGER/WhatsApp", f"Playwright send error: {e}")
        return f"❌ Errore Playwright durante invio a `{phone}`: {e}"


def send(cfg, recipient: str, text: str, is_app_open: bool = False) -> str:
    """Send a WhatsApp message. Uses CDP/Playwright if available, falls back to pyautogui."""
    if not cfg.enabled:
        return "⚠️ WhatsApp adapter disabilitato. Abilitalo nelle impostazioni Messenger."

    # Normalize phone number — must be E.164 format e.g. +393331234567
    phone = recipient.strip()
    if not phone.startswith("+"):
        cc = getattr(cfg, "phone_country_code", "+39") or "+39"
        phone = cc + phone.lstrip("0")
    phone = phone.replace(" ", "").replace("-", "")

    # ── Try Playwright/CDP first (recommended) ──────────────────────────────
    try:
        from hecos.modules.browser import engine  # noqa: F401 — just check availability
        logger.info("MESSENGER/WhatsApp", f"Invio via Playwright/CDP a {phone}...")
        result = _send_via_playwright(phone, text)
        logger.info("MESSENGER/WhatsApp", f"Risultato invio: {result}")
        return result
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
            "Per invii affidabili, usa il browser CDP."
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
        cdp_status = "CDP connesso" if engine.is_running() else "CDP non connesso (browser non avviato)"
        return f"BETA (Playwright pronto — {cdp_status})"
    except ImportError:
        pass

    # Fallback: check pyautogui
    try:
        import pyautogui  # noqa: F401
        return "BETA [FALLBACK] (pyautogui pronto — browser CDP non disponibile)"
    except ImportError:
        return "NOT INSTALLED (esegui: pip install playwright oppure pip install pyautogui)"
