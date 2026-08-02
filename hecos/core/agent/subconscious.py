"""
hecos/core/agent/subconscious.py
─────────────────────────────────────────────────────────────────────────────
Gestisce la 'Coscienza Operativa' persistente di Hecos (il Subconscio).
Permette all'agente di appuntarsi task in corso per poterli riprendere 
automaticamente dopo un riavvio o un blackout.
─────────────────────────────────────────────────────────────────────────────
"""

import os
import json
import threading
from hecos.core.logging import logger
from hecos.core.constants import HECOS_DIR

# File path: C:\Hecos\workspace\consciousness.json
WORKSPACE_DIR = os.path.join(HECOS_DIR, "..", "workspace")
CONSCIOUSNESS_FILE = os.path.normpath(os.path.join(WORKSPACE_DIR, "consciousness.json"))

_lock = threading.Lock()

def _ensure_dir():
    if not os.path.exists(WORKSPACE_DIR):
        try:
            os.makedirs(WORKSPACE_DIR)
        except Exception:
            pass

def read_state() -> dict:
    """Legge lo stato attuale del subconscio."""
    with _lock:
        if not os.path.exists(CONSCIOUSNESS_FILE):
            return {"status": "IDLE", "goal": "", "context": ""}
        try:
            with open(CONSCIOUSNESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[Subconscious] Failed to read consciousness: {e}")
            return {"status": "IDLE", "goal": "", "context": ""}

def write_state(status: str, goal: str, context: str) -> bool:
    """
    Scrive lo stato nel subconscio.
    status: 'IN_PROGRESS', 'PAUSED', 'COMPLETED', 'IDLE'
    """
    _ensure_dir()
    state = {
        "status": status.upper(),
        "goal": goal,
        "context": context
    }
    with _lock:
        try:
            with open(CONSCIOUSNESS_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"[Subconscious] Failed to write consciousness: {e}")
            return False

def clear_state():
    """Resetta il subconscio a IDLE."""
    write_state("IDLE", "", "")

def get_pending_task() -> dict:
    """Restituisce il task in corso se lo status è IN_PROGRESS, altrimenti None."""
    state = read_state()
    if state.get("status") == "IN_PROGRESS":
        return state
    return None
