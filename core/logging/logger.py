import logging
import os
import sys
import subprocess
from datetime import datetime

# Disabilita i debug di requests e urllib3 (troppo verbosi)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)

# Creiamo la cartella log se non esiste
if not os.path.exists("logs"):
    os.makedirs("logs")

info_filename = f"logs/zentra_info_{datetime.now().strftime('%Y-%m-%d')}.log"
debug_filename = f"logs/zentra_debug_{datetime.now().strftime('%Y-%m-%d')}.log"

logger = logging.getLogger("ZentraLogger")
logger.setLevel(logging.DEBUG)  # Il logger accetta tutto

# Svuota gli handler esistenti se modulo ricaricato
if logger.hasHandlers():
    logger.handlers.clear()

file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

# Handler per il file INFO/WARN/ERROR
info_file_handler = logging.FileHandler(info_filename, encoding='utf-8')
info_file_handler.setLevel(logging.INFO)
info_file_handler.setFormatter(file_formatter)

# Handler per il file SOLO DEBUG
class LevelFilter(logging.Filter):
    def __init__(self, level):
        self.level = level
    def filter(self, record):
        return record.levelno == self.level

debug_file_handler = logging.FileHandler(debug_filename, encoding='utf-8')
debug_file_handler.setLevel(logging.DEBUG)
debug_file_handler.addFilter(LevelFilter(logging.DEBUG))
debug_file_handler.setFormatter(file_formatter)

# Handler per la console (default INFO)
class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: '\033[96m',    # Ciano
        logging.INFO: '\033[97m',     # Bianco
        logging.WARNING: '\033[93m',  # Giallo
        logging.ERROR: '\033[91m',    # Rosso
        logging.CRITICAL: '\033[95m'  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = ColorFormatter('%(asctime)s [%(levelname)s] %(message)s')
console_handler.setFormatter(console_formatter)

# Aggiungi gli handler al logger
logger.addHandler(info_file_handler)
logger.addHandler(debug_file_handler)
logger.addHandler(console_handler)

_console_window_started = False

def chiudi_console_log():
    """Chiude forzatamente eventuali finestre PowerShell con il titolo Zentra Logs."""
    global _console_window_started
    try:
        if os.name == 'nt':
            # Usa taskkill filtrando per il titolo esatto della finestra
            subprocess.run('taskkill /f /fi "windowtitle eq Zentra Logs*" >nul 2>&1', shell=True)
            _console_window_started = False
    except:
        pass

def init_logger(config):
    """
    Inizializza le impostazioni di logging lette da config.json
    """
    global _console_window_started
    
    logging_config = config.get('logging', {})
    
    if not logging_config:
        # Se non c'è, mettiamo i default e poi config_manager lo salverà in futuro
        pass
        
    destinazione = logging_config.get('destinazione', 'chat')
    tipo_messaggi = logging_config.get('tipo_messaggi', 'entrambi')
    
    # Rimuovi eventuali filtri precedenti dal console_handler
    for f in console_handler.filters[:]:
        console_handler.removeFilter(f)

    # Crea un nuovo filtro basato sulla preferenza tipo_messaggi
    class ConsoleTypeFilter(logging.Filter):
        def filter(self, record):
            if tipo_messaggi == 'info':
                return record.levelno >= logging.INFO
            elif tipo_messaggi == 'debug':
                return record.levelno == logging.DEBUG
            else: # 'entrambi'
                return True
                
    console_handler.addFilter(ConsoleTypeFilter())
    
    if destinazione == 'console':
        # Disabilita l'output sulla chat principale
        if console_handler in logger.handlers:
            logger.removeHandler(console_handler)
        
        # Pulisce sempre eventuali finestre orfane all'avvio o cambio config
        chiudi_console_log()
        chiudi_console_debug()
            
        if tipo_messaggi == 'info' or tipo_messaggi == 'entrambi':
            # La finestra principale segue sempre il log INFO (Attività)
            ps_script_info = (
                "$host.ui.RawUI.WindowTitle = 'Zentra Core - Log Attivit\u00e0'; "
                f"Get-Content -Path '{info_filename}' -Wait -Tail 20 | ForEach-Object {{ "
                "if ($_ -match '\\[ERROR\\]') { Write-Host $_ -ForegroundColor Red } "
                "elseif ($_ -match '\\[WARNING\\]') { Write-Host $_ -ForegroundColor Yellow } "
                "else { Write-Host $_ -ForegroundColor White } "
                "}"
            )
            subprocess.Popen(f'start /min powershell -WindowStyle Minimized -NoExit -Command "{ps_script_info}"', shell=True)
            
        if tipo_messaggi == 'debug' or tipo_messaggi == 'entrambi':
            # Se è richiesto il debug, apriamo una finestra dedicata (Debug Tecnico)
            apri_console_debug()
            
        _console_window_started = True
    elif destinazione == 'file_only':
        # Se si sceglie solo file, chiudi tutte le console e scrivi solo su log
        chiudi_console_log()
        chiudi_console_debug()
        
        # Disabilita l'output sulla chat principale
        if console_handler in logger.handlers:
            logger.removeHandler(console_handler)
    else:
        # Se si passa a chat, chiudi le console se aperte
        chiudi_console_log()
        chiudi_console_debug()
            
        # Assicurati che l'output standard sia attivo
        if console_handler not in logger.handlers:
            logger.addHandler(console_handler)

def apri_console_debug():
    """Apre una finestra console dedicata esclusivamente ai log di DEBUG (es. LiteLLM)."""
    # Chiudiamo eventuali istanze precedenti per evitare duplicati
    chiudi_console_debug()
    
    today = datetime.now().strftime("%Y-%m-%d")
    debug_filename = f"logs/zentra_debug_{today}.log"
    
    # Assicuriamoci che il file esista altrimenti Get-Content fallisce
    if not os.path.exists(debug_filename):
        with open(debug_filename, "a") as f:
            f.write(f"{datetime.now()} [DEBUG] [SYSTEM] Console Debug Inizializzata.\n")

    ps_script_debug = (
        "$host.ui.RawUI.WindowTitle = 'Zentra Core - Debug Tecnico (LiteLLM)'; "
        "Write-Host '=== CONSOLE DEBUG TECNICO ATTIVA ===' -ForegroundColor Cyan; "
        f"Get-Content -Path '{debug_filename}' -Wait -Tail 20 | ForEach-Object {{ "
        "if ($_ -match '\\[DEBUG\\]') { Write-Host $_ -ForegroundColor Cyan } "
        "else { Write-Host $_ -ForegroundColor Gray } "
        "}"
    )
    
    try:
        subprocess.Popen(f'start /min powershell -WindowStyle Minimized -NoExit -Command "{ps_script_debug}"', shell=True)
        return True
    except:
        return False

def chiudi_console_debug():
    """Chiude la finestra di debug tecnico cercando il titolo della finestra."""
    try:
        subprocess.run('taskkill /FI "WINDOWTITLE eq Zentra Core - Debug Tecnico (LiteLLM)*" /F', 
                       shell=True, capture_output=True)
    except:
        pass

def chiudi_console_log():
    """Chiude la finestra di log attivit\u00e0."""
    try:
        subprocess.run('taskkill /FI "WINDOWTITLE eq Zentra Core - Log Attivit\u00e0*" /F', 
                       shell=True, capture_output=True)
    except:
        pass


def info(modulo, messaggio=None):
    """Registra un evento informativo standard. Se messaggio è None, modulo viene trattato come il messaggio."""
    if messaggio is None:
        logger.info(modulo)
    else:
        logger.info(f"[{modulo}] {messaggio}")

def errore(modulo, messaggio=None):
    """Registra un errore critico nel sistema. Se messaggio è None, modulo viene trattato come l'errore."""
    if messaggio is None:
        logger.error(modulo)
    else:
        logger.error(f"[{modulo}] {messaggio}")

def debug(modulo, messaggio):
    """Registra un messaggio di debug nel file di log."""
    logger.debug(f"[{modulo}] {messaggio}")
    
def warning(modulo, messaggio=None):
    """Registra un avviso (warning). Se messaggio è None, modulo viene trattato come l'avviso."""
    if messaggio is None:
        logger.warning(modulo)
    else:
        logger.warning(f"[{modulo}] {messaggio}")

def debug_ia(testo_utente, risposta_ia, tag_rilevato=None):
    """
    Registra il flusso completo della conversazione e l'attivazione dei plugin.
    Utile per capire se l'IA sta formattando correttamente i tag.
    """
    info_tag = f" | TAG RILEVATO: {tag_rilevato}" if tag_rilevato else ""
    logger.info(f"UTENTE: {testo_utente} | IA: {risposta_ia}{info_tag}")

def leggi_log(n=10, solo_errori=False):
    """
    Ritorna le ultime N righe del log INFO.
    Se solo_errori è True, filtra solo le righe critiche.
    """
    try:
        if not os.path.exists(info_filename):
            return "Nessun log trovato per la giornata odierna."
            
        with open(info_filename, 'r', encoding='utf-8') as f:
            righe = f.readlines()
            if solo_errori:
                righe = [r for r in righe if "[ERROR]" in r]
            
            ultime_righe = righe[-n:]
            return "".join(ultime_righe) if ultime_righe else "Il registro è vuoto."
    except Exception as e:
        return f"Errore durante la lettura del file log: {e}"
