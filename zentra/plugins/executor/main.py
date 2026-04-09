"""
PLUGIN: System Executor (Zentra Code Jail)
DESCRIPTION: Permette all'IA di eseguire calcoli e snippet di codice Python in locale, 
previa severa analisi statica (AST) per bloccare importazioni di sistema pericolose.
"""

import os
import ast
import subprocess
import sys
try:
    from zentra.core.logging import logger
    from zentra.core.i18n import translator
    from app.config import ConfigManager
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[EXE_DEBUG]", *args)
        def info(self, *args, **kwargs): print("[EXE_INFO]", *args)
        def error(self, *args, **kwargs): print("[EXE_ERR]", *args)
    logger = DummyLogger()
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()
    class DummyConfigMgr:
        def __init__(self): self.config = {}
        def get_plugin_config(self, tag, key, default): return default
    ConfigManager = DummyConfigMgr

# --- AST SECURITY ANALYZER ---
FORBIDDEN_IMPORTS = {
    'os', 'sys', 'subprocess', 'shutil', 'socket', 'pathlib', 
    'pty', 'tempfile', 'requests', 'urllib', 'ftplib', 'ctypes', 'winreg'
}

FORBIDDEN_CALLS = {'eval', 'exec', 'compile', 'open'} # 'open' is blocked to prevent touching host files freely

class SecurityAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.errors = []
        
    def visit_Import(self, node):
        for alias in node.names:
            base_module = alias.name.split('.')[0]
            if base_module in FORBIDDEN_IMPORTS:
                self.errors.append(f"Import non consentito: {alias.name}")
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module in FORBIDDEN_IMPORTS:
                self.errors.append(f"Import non consentito da: {node.module}")
        self.generic_visit(node)
        
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.errors.append(f"Funzione non consentita: {node.func.id}")
        self.generic_visit(node)

# --- PLUGIN CLASS ---
class ExecutorTools:
    """
    Plugin: Zentra Code Jail (AST Sandbox)
    Allows safe algorithmic execution.
    """

    def __init__(self):
        self.tag = "EXECUTOR"
        self.desc = "Safe Python execution (AST Sandbox)."
        self.status = "ONLINE (Code Jail Active)"
        
        self.config_schema = {
            "timeout_seconds": {
                "type": "int",
                "default": 10,
                "description": "Timeout in secondi per prevenire loop infiniti."
            }
        }
        
        # Ensure the shared workspace exists for visibility
        self.workspace_dir = os.path.abspath(os.path.join(os.getcwd(), "workspace", "sandbox"))
        os.makedirs(self.workspace_dir, exist_ok=True)

    def run_python_code(self, code: str) -> str:
        """
        Executes a block of Python code safely after strict Static Analysis.
        Use this for math, data manipulation, algorithm building.
        DO NOT use for file I/O or system commands (imports like os, sys are blocked).
        
        :param code: The Python script to execute.
        """
        # 1. Syntax Check & AST Security Analysis
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return f"SyntaxError nel codice: {e}"
        except Exception as e:
            return f"Errore di parsing inatteso: {e}"
            
        analyzer = SecurityAnalyzer()
        analyzer.visit(tree)
        
        if analyzer.errors:
            logger.error(f"[{self.tag}] Tentativo di violazione di sicurezza bloccato:\n{analyzer.errors}")
            return f"SECURITY VIOLATION BLOCKED: The sandbox prevents you from using these modules/functions:\n{', '.join(analyzer.errors)}\nPlease rewrite your logic without them."

        # 2. Write to user-visible workspace for transparency
        script_path = os.path.join(self.workspace_dir, "ai_last_script.py")
        output_path = os.path.join(self.workspace_dir, "ai_last_output.txt")
        
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)
        except Exception as e:
            return f"Errore interno di I/O nel sandbox: {e}"
            
        logger.info(f"[{self.tag}] Codice sicuro validato. Esecuzione in corso...")
        
        # 3. Subprocess Execution
        cfg = ConfigManager()
        timeout = cfg.get_plugin_config(self.tag, "timeout_seconds", 10)
        
        try:
            # We run the script in a separate python process using the current interpreter
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                cwd=self.workspace_dir # Restrict execution working dir to sandbox
            )
            
            output, _ = process.communicate(timeout=timeout)
            output = output if output is not None else ""
            
            # Save output for user visibility
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output)
            
            if process.returncode != 0:
                return f"Execution failed (Code {process.returncode}):\n{output}"
                
            return output[-2000:] if len(output) > 2000 else output
            
        except subprocess.TimeoutExpired:
            process.kill()
            timeout_msg = f"Timeout Error: Lo script ha superato il limite di {timeout} secondi ed è stato killato."
            return timeout_msg
        except Exception as e:
            return f"Internal Execution Error: {e}"

# Istanzia pubblicamente lo strumento per l'esportazione verso il Core
tools = ExecutorTools()

# --- COMPATIBILITY SHIMS ---
def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status

def execute(comando: str) -> str:
    """Compatibilità legacy rimossa."""
    return "La shell dell'host è disabilitata. Usa lo strumento 'run_python_code' per elaborazioni algebriche/dati in locale."
