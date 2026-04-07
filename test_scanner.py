
import os
import sys

# Aggiungi la root del progetto al path per permettere i nuovi import pacchettizzati
project_root = os.path.abspath(os.curdir)
sys.path.append(project_root)

# Mock logger to see output
class MockLogger:
    def info(self, tag, msg=None):
        if msg: print(f"[INFO] [{tag}] {msg}")
        else: print(f"[INFO] {tag}")
    def debug(self, tag, msg=None):
        if msg: print(f"[DEBUG] [{tag}] {msg}")
        else: print(f"[DEBUG] {tag}")
    def error(self, msg): print(f"[ERROR] {msg}")
    def warning(self, tag, msg=None):
        if msg: print(f"[WARN] [{tag}] {msg}")
        else: print(f"[WARN] {tag}")

from zentra.core.logging import logger
logger.info = lambda t, m=None: print(f"[INFO] [{t}] {m}") if m else print(f"[INFO] {t}")
logger.debug = lambda t, m=None: print(f"[DEBUG] [{t}] {m}") if m else print(f"[DEBUG] {t}")
logger.error = lambda m: print(f"[ERROR] {m}")
logger.warning = lambda t, m=None: print(f"[WARN] [{t}] {m}") if m else print(f"[WARN] {t}")

from zentra.core.system.plugin_scanner import update_capability_registry
from zentra.app.config import ConfigManager

print("--- STARTING PLUGIN SCAN TEST ---")
cm = ConfigManager()
update_capability_registry(cm.config, debug_log=True)
print("--- SCAN COMPLETE ---")
