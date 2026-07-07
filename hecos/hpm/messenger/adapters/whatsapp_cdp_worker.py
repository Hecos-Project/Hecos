import sys
import json
import time
from urllib.parse import quote

# Fix Windows console emoji printing crash
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

_WA_MSG_BOX_SELECTORS = [
    'div[contenteditable="true"][data-testid="conversation-compose-box-input"]',
    'div[contenteditable="true"][tabindex="10"]',
    'footer div[contenteditable="true"]',
    'div[contenteditable="true"][data-tab="10"]',
    'div[contenteditable="true"][title="Type a message"]',
    'div[contenteditable="true"][title="Scrivi un messaggio"]'
]
_WA_MSG_SENT_SELECTOR = 'span[data-icon="msg-check"], span[data-icon="msg-dblcheck"]'

def main():
    # Legge input da stdin
    try:
        raw_input = sys.stdin.read()
        if not raw_input:
            print("❌ Nessun input ricevuto dal worker.")
            return
        input_data = json.loads(raw_input)
        phone = input_data["phone"]
        text = input_data["text"]
        single_block = input_data.get("single_block", True)
    except Exception as e:
        print(f"❌ Errore IPC json: {e}")
        return

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        print(f"❌ Playwright non installato: {e}")
        return

    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.connect_over_cdp('http://127.0.0.1:9222', timeout=15000)
            except Exception as e:
                print(f"❌ Impossibile connettersi a CDP: {e}. Attention: CDP browser not active, CDP port closed or browser not running. Open: Tray Dashboard for more information.")
                return

            url_web = f"https://web.whatsapp.com/send?phone={phone}&text={quote(text)}"

            wa_page = None
            for ctx in browser.contexts:
                for pg in ctx.pages:
                    try:
                        if "web.whatsapp.com" in pg.url:
                            wa_page = pg
                            break
                    except Exception as e:
                        print(f"❌ Errore lettura tab url: {e}")
                if wa_page:
                    break

            if not wa_page:
                # Forza navigazione in un tab vuoto
                print(f"❌ Nessuna scheda WhatsApp Web attiva trovata nei contesti CDP.")
                return

            try:
                wa_page.bring_to_front()
            except Exception as e:
                print(f"❌ Errore bring_to_front: {e}")
                return
            
            navigated_without_reload = False
            if "web.whatsapp.com" in wa_page.url:
                try:
                    # Prova a usare lo shortcut da tastiera per la ricerca (Ctrl+Alt+/)
                    # Questo porta automaticamente il focus sulla barra di ricerca!
                    wa_page.keyboard.press("Control+Alt+/")
                    time.sleep(1)
                    
                    # Cancelliamo eventuale testo già presente nella ricerca
                    wa_page.keyboard.press("Control+A")
                    wa_page.keyboard.press("Backspace")
                    time.sleep(0.5)
                    
                    # Scriviamo il nome del contatto o il numero
                    wa_page.keyboard.insert_text(phone)
                    time.sleep(2.5) # Aspettiamo che appaiano i risultati di ricerca
                    
                    # Premiamo invio per aprire la prima chat trovata
                    wa_page.keyboard.press("Enter")
                    time.sleep(1.5) # Aspettiamo che si apra la conversazione
                    
                    navigated_without_reload = True
                except Exception as e:
                    print(f"⚠️ Errore durante la ricerca via shortcut: {e}")
                    pass

            if not navigated_without_reload:
                try:
                    # Se proprio fallisce, ricarica la pagina usando l'API send
                    wa_page.goto(url_web, wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    print(f"❌ Errore goto: {e}")
                    return

            # Check QR code
            try:
                qr = wa_page.locator('div[data-testid="qrcode"]')
                if qr.is_visible(timeout=3000):
                    print("❌ WhatsApp Web non è loggato. Scansiona il QR code.")
                    return
            except Exception:
                pass

            # Cerca input box
            msg_box = None
            for selector in _WA_MSG_BOX_SELECTORS:
                try:
                    loc = wa_page.locator(selector).first
                    loc.wait_for(state="visible", timeout=10000)
                    msg_box = loc
                    break
                except Exception:
                    continue

            if not msg_box:
                print("❌ Non riesco a trovare la casella di testo di WhatsApp Web (non visibile o selettori cambiati).")
                return

            msg_box.click()
            time.sleep(0.3)

            try:
                # Svuotiamo la casella di testo se c'è qualcosa
                current_val = msg_box.inner_text()
                if current_val.strip():
                    wa_page.keyboard.press("Control+A")
                    wa_page.keyboard.press("Backspace")
                    time.sleep(0.2)
                
                # Furbata suggerita: digitiamo ">>" per forzare la comparsa del tasto invio
                msg_box.type(">>", delay=10)
                
                # Aspettiamo che il tasto invio diventi visibile
                send_btn = wa_page.locator('span[data-icon="send"]').first
                try:
                    send_btn.wait_for(state="visible", timeout=3000)
                except Exception:
                    pass # Se non appare, procediamo comunque
                
                # Ora cancelliamo ">>"
                wa_page.keyboard.press("Control+A")
                wa_page.keyboard.press("Backspace")
                time.sleep(0.2)
                
                # E scriviamo il testo vero
                if single_block:
                    lines = text.split('\n')
                    for i, line in enumerate(lines):
                        if line:
                            msg_box.type(line, delay=10)
                        if i < len(lines) - 1:
                            wa_page.keyboard.press("Shift+Enter")
                else:
                    msg_box.type(text, delay=10)
                time.sleep(0.5)
            except Exception:
                if single_block:
                    lines = text.split('\n')
                    for i, line in enumerate(lines):
                        if line:
                            msg_box.type(line, delay=10)
                        if i < len(lines) - 1:
                            wa_page.keyboard.press("Shift+Enter")
                else:
                    msg_box.type(text, delay=10)
                time.sleep(0.5)

            # Send
            try:
                send_btn = wa_page.locator('span[data-icon="send"]').first
                if send_btn.is_visible(timeout=1000):
                    send_btn.click()
                else:
                    wa_page.keyboard.press("Enter")
            except Exception:
                wa_page.keyboard.press("Enter")

            # Verifica
            sent_ok = False
            try:
                wa_page.locator(_WA_MSG_SENT_SELECTOR).last.wait_for(state="visible", timeout=10000)
                sent_ok = True
            except Exception:
                sent_ok = None

            if sent_ok is True:
                print(f"✅ Messaggio WhatsApp inviato a `{phone}` (checkmark confermato).")
            elif sent_ok is None:
                print(f"⚠️ Messaggio WhatsApp inviato a `{phone}` (nessun checkmark rilevato, verifica manualmente).")
            else:
                print(f"❌ Errore verifica invio a `{phone}`.")
                
    except Exception as e:
        print(f"❌ Errore script Playwright subprocess: {e}")


if __name__ == "__main__":
    main()
