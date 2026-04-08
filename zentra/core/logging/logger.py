import logging
import os
import sys
import subprocess
from datetime import datetime

# Set verbose levels for internal libraries - default WARNING to avoid chat pollution
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
litellm_log = logging.getLogger("LiteLLM")
litellm_log.setLevel(logging.WARNING)  # Default OFF; init_logger controls this
litellm_log.propagate = False  # Never leak to root logger


# Create logs directory if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")

info_filename = f"logs/zentra_info_{datetime.now().strftime('%Y-%m-%d')}.log"
debug_filename = f"logs/zentra_debug_{datetime.now().strftime('%Y-%m-%d')}.log"

# Global logger for Zentra (points to root for multi-library consistency)
logger = logging.getLogger() 
logger.setLevel(logging.DEBUG)

# File formatters
file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

# Handler for INFO/WARN/ERROR file
info_file_handler = logging.FileHandler(info_filename, encoding='utf-8')
info_file_handler.setLevel(logging.INFO)
info_file_handler.setFormatter(file_formatter)

# Handler for DEBUG-ONLY file
class LevelFilter(logging.Filter):
    def __init__(self, level):
        self.level = level
    def filter(self, record):
        return record.levelno == self.level

debug_file_handler = logging.FileHandler(debug_filename, encoding='utf-8')
debug_file_handler.setLevel(logging.DEBUG)
debug_file_handler.addFilter(LevelFilter(logging.DEBUG))
debug_file_handler.setFormatter(file_formatter)

# Console Handler (the one that shows in the chat)
class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: '\033[96m',    # Cyan
        logging.INFO: '\033[97m',     # White
        logging.WARNING: '\033[93m',  # Yellow
        logging.ERROR: '\033[91m',    # Red
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

# Filter for Console output based on preference
class RejectAllFilter(logging.Filter):
    """Filter that rejects all records. Used to silence console output when external windows are active."""
    def filter(self, record):
        return False

class ConsoleTypeFilter(logging.Filter):
    """Filter for Console output types (info, debug, both)."""
    def __init__(self, message_types):
        super().__init__()
        self.message_types = message_types

    def filter(self, record):
        if self.message_types == 'info':
            return record.levelno >= logging.INFO
        elif self.message_types == 'debug':
            return record.levelno == logging.DEBUG
        else: # 'both'
            return True

# Initial setup: just files for now, until init_logger is called
if not logger.hasHandlers():
    logger.addHandler(info_file_handler)
    logger.addHandler(debug_file_handler)
    # Default to console if not initialized yet
    logger.addHandler(console_handler)

if not litellm_log.hasHandlers():
    litellm_log.addHandler(debug_file_handler)

_console_window_started = False

def init_logger(config, allow_external_windows=True):
    """
    Initializes logging settings read from config.json.
    CLEANS ALL HANDLERS first to ensure strict isolation.
    """
    global _console_window_started
    
    logging_config = config.get('logging', {})
    destination = logging_config.get('destination', 'chat')
    message_types = logging_config.get('message_types', 'both')
    
    # Toggle LiteLLM library debug verbosity dynamically based on config
    llm_cfg = config.get('llm', {})
    debug_llm = llm_cfg.get('debug_llm', False)
    
    # Purge ALL handlers from LiteLLM logger (prevents its built-in StreamHandler to stdout)
    for h in litellm_log.handlers[:]:
        litellm_log.removeHandler(h)
    # Also silence httpcore/httpx/requests at WARNING always
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # CRITICAL: Prevent LiteLLM from auto-adding its own stdout StreamHandler via LITELLM_LOG env var
    import os as _os
    _os.environ["LITELLM_LOG"] = ""  # Always reset to prevent LiteLLM from activating verbose mode
    
    if debug_llm:
        litellm_log.setLevel(logging.DEBUG)
        # Redirect LiteLLM output ONLY to our debug file handler, never to stdout
        litellm_log.addHandler(debug_file_handler)
    else:
        litellm_log.setLevel(logging.WARNING)
        
    # PULIZIA TOTALE: rimuove ogni handler precedente (anche dalle librerie esterne)
    for h in logger.handlers[:]:
        logger.removeHandler(h)
    
    # RI-AGGIUNTA FILE HANDLERS (Sempre attivi)
    logger.addHandler(info_file_handler)
    logger.addHandler(debug_file_handler)

    # Remove all existing filters from console_handler before re-adding
    for f in console_handler.filters[:]:
        console_handler.removeFilter(f)

    # Re-add filters based on current config
    console_handler.addFilter(ConsoleTypeFilter(message_types))
    
    destination_lower = destination.lower().strip()
    
    if (destination_lower == 'console' or destination_lower == 'file_only'):
        console_handler.addFilter(RejectAllFilter())
        
    if destination_lower == 'console':
        # Skip external windows if requested
        if not allow_external_windows:
            logger.addHandler(console_handler) # fallback to terminal if external windows restricted
            return
            
        # NON aggiungiamo console_handler qui -> i log restano solo su file
        # che vengono poi letti dalle finestre PowerShell esterne
        
        # Chiudiamo le finestre orfane (per sicurezza)
        close_activity_log()
        close_debug_log()
            
        if message_types == 'info' or message_types == 'both':
            ps_script_info = (
                "$host.ui.RawUI.WindowTitle = 'Zentra Core - Activity Log'; "
                "Write-Host '=== ACTIVITY LOG CONSOLE ACTIVE ===' -ForegroundColor White; "
                f"Get-Content -Path '{info_filename}' -Wait -Tail 20 | ForEach-Object {{ "
                "if ($_ -match '\\[ERROR\\]') { Write-Host $_ -ForegroundColor Red } "
                "elseif ($_ -match '\\[WARNING\\]') { Write-Host $_ -ForegroundColor Yellow } "
                "else { Write-Host $_ -ForegroundColor White } "
                "}"
            )
            # Remove /min and -WindowStyle Minimized to make windows visible as requested
            subprocess.Popen(f'start "" powershell -NoExit -Command "{ps_script_info}"', shell=True)
            
        if message_types == 'debug' or message_types == 'both':
            # Finestra Technical Debug
            open_debug_log()
            
        _console_window_started = True
        
    elif destination_lower == 'file_only':
        # Già fatto sopra (solo file handlers aggiunti)
        close_activity_log()
        close_debug_log()
        
    else:
        # Destinazione standard: CHAT (nel terminale principale)
        close_activity_log()
        close_debug_log()
        logger.addHandler(console_handler)

def open_debug_log():
    """Opens a dedicated console for DEBUG logs (e.g., LiteLLM)."""
    close_debug_log()
    
    today = datetime.now().strftime("%Y-%m-%d")
    debug_filename = f"logs/zentra_debug_{today}.log"
    
    if not os.path.exists(debug_filename):
        with open(debug_filename, "a") as f:
            f.write(f"{datetime.now()} [DEBUG] [SYSTEM] Debug Console Initialized.\n")

    ps_script_debug = (
        "$host.ui.RawUI.WindowTitle = 'Zentra Core - Technical Debug (LiteLLM)'; "
        "Write-Host '=== TECHNICAL DEBUG CONSOLE ACTIVE ===' -ForegroundColor Cyan; "
        f"Get-Content -Path '{debug_filename}' -Wait -Tail 20 | ForEach-Object {{ "
        "if ($_ -match '\\[DEBUG\\]') { Write-Host $_ -ForegroundColor Cyan } "
        "else { Write-Host $_ -ForegroundColor Gray } "
        "}"
    )
    
    try:
        # Remove /min and -WindowStyle Minimized to make windows visible
        subprocess.Popen(f'start "" powershell -NoExit -Command "{ps_script_debug}"', shell=True)
        return True
    except:
        return False

def close_debug_log():
    """Closes technical debug window via title search."""
    try:
        subprocess.run('taskkill /FI "WINDOWTITLE eq Zentra Core - Technical Debug (LiteLLM)*" /F', 
                       shell=True, capture_output=True)
    except:
        pass

def close_activity_log():
    """Closes activity log window via title search."""
    try:
        # Match both old and new titles for safety during transition
        subprocess.run('taskkill /FI "WINDOWTITLE eq Zentra Core - Activity Log*" /F', shell=True, capture_output=True)
        subprocess.run('taskkill /FI "WINDOWTITLE eq Zentra Core - Log Attivit\u00e0*" /F', shell=True, capture_output=True)
    except:
        pass

def close_all_consoles():
    """Closes all external windows."""
    close_activity_log()
    close_debug_log()

def info(module, message=None):
    """Logs a standard info event."""
    if message is None:
        logger.info(module)
    else:
        logger.info(f"[{module}] {message}")

def error(module, message=None):
    """Logs a critical error."""
    if message is None:
        logger.error(module)
    else:
        logger.error(f"[{module}] {message}")

def debug(module, message):
    """Logs a debug message."""
    logger.debug(f"[{module}] {message}")
    
def warning(module, message=None):
    """Logs a warning."""
    if message is None:
        logger.warning(module)
    else:
        logger.warning(f"[{module}] {message}")

def debug_ai(user_text, ai_response, tag_detected=None):
    """Logs full conversation flow and plugin activation."""
    info_tag = f" | TAG DETECTED: {tag_detected}" if tag_detected else ""
    logger.info(f"USER: {user_text} | AI: {ai_response}{info_tag}")

def read_logs(n=10, errors_only=False, debug_only=False):
    """Returns the last N lines of the specified log file."""
    try:
        target_file = info_filename
        if debug_only:
            target_file = debug_filename
            
        if not os.path.exists(target_file):
            return f"No logs found in {target_file} for today."
            
        with open(target_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if errors_only:
                lines = [r for r in lines if "[ERROR]" in r]
            
            last_lines = lines[-n:]
            return "".join(last_lines) if last_lines else "Log registry is empty."
    except Exception as e:
        return f"Error reading log file: {e}"
