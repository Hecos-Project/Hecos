import logging
import os
from datetime import datetime

# Disabilita i debug di requests e urllib3 (troppo verbosi)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Creiamo la cartella log se non esiste
if not os.path.exists("logs"):
    os.makedirs("logs")

# Nome del file basato sulla data odierna per una rotazione giornaliera
log_filename = f"logs/aura_{datetime.now().strftime('%Y-%m-%d')}.log"

# Configurazione con due handler separati
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Il logger accetta tutto

# Handler per il file (registra TUTTO, livello DEBUG)
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
file_handler.setFormatter(file_formatter)

# Handler per la console (solo INFO ed ERROR)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # <--- IMPORTANTE: solo INFO e superiori
console_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
console_handler.setFormatter(console_formatter)

# Aggiungi gli handler al logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def info(messaggio):
    """Registra un evento informativo standard."""
    logging.info(messaggio)

def errore(messaggio):
    """Registra un errore critico nel sistema."""
    logging.error(messaggio)

def debug(modulo, messaggio):
    """Registra un messaggio di debug nel file di log (non appare in console)."""
    logging.debug(f"[DEBUG][{modulo}] {messaggio}")
    
def warning(modulo, messaggio):
    """Registra un avviso (warning) nel file di log."""
    logging.warning(f"[WARNING][{modulo}] {messaggio}")

def debug_ia(testo_utente, risposta_ia, tag_rilevato=None):
    """
    Registra il flusso completo della conversazione e l'attivazione dei plugin.
    Utile per capire se l'IA sta formattando correttamente i tag.
    """
    info_tag = f" | TAG RILEVATO: {tag_rilevato}" if tag_rilevato else ""
    logging.info(f"UTENTE: {testo_utente} | IA: {risposta_ia}{info_tag}")

def leggi_log(n=10, solo_errori=False):
    """
    Ritorna le ultime N righe del log. 
    Se solo_errori è True, filtra solo le righe critiche.
    """
    try:
        if not os.path.exists(log_filename):
            return "Nessun log trovato per la giornata odierna."
            
        with open(log_filename, 'r', encoding='utf-8') as f:
            righe = f.readlines()
            if solo_errori:
                righe = [r for r in righe if "[ERROR]" in r]
            
            ultime_righe = righe[-n:]
            return "".join(ultime_righe) if ultime_righe else "Il registro è vuoto."
    except Exception as e:
        return f"Errore durante la lettura del file log: {e}"