import subprocess
try:
    from core.logging import logger
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[EXE_DEBUG]", *args)
    logger = DummyLogger()

class ExecutorTools:
    """
    Plugin: System Executor
    Permette l'esecuzione di comandi shell a basso livello (uso avanzato).
    """

    def __init__(self):
        self.tag = "EXECUTOR"
        self.desc = "Esecuzione comandi terminale diretti."
        self.status = "READY"

    def execute_shell(self, command: str) -> str:
        """
        Esegue un comando shell nel terminale di sistema e restituisce l'output (max 500 caratteri).
        
        :param command: Il comando da eseguire (es. 'dir', 'ipconfig').
        """
        try:
            logger.debug("EXECUTOR", f"Shell direct: {command}")
            risultato = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
            return risultato[:500]
        except Exception as e:
            return f"Errore esecuzione: {e}"

tools = ExecutorTools()

# --- COMPATIBILITY SHIMS ---
def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status
