import subprocess
try:
    from core.logging import logger
    from core.i18n import translator
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[EXE_DEBUG]", *args)
    logger = DummyLogger()
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()

class ExecutorTools:
    """
    Plugin: System Executor
    Allows the execution of low-level shell commands (advanced use).
    """

    def __init__(self):
        self.tag = "EXECUTOR"
        self.desc = "Direct terminal command execution."
        self.status = translator.t("plugin_executor_status_ready")

    def execute_shell(self, command: str) -> str:
        """
        Executes a shell command in the system terminal and returns the output (max 500 characters).
        
        :param command: The command to execute (e.g., 'dir', 'ipconfig').
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
