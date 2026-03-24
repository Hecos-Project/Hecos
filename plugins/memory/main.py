"""
PLUGIN: Memory Management
DESCRIPTION: Class-based interface for accessing the Vault (Semantic and Episodic Memory).
"""

import sqlite3
import os
try:
    from memory import brain_interface
    from core.i18n import translator
except ImportError:
    class DummyBrainInterface:
        def aggiorna_profilo(self, k, v): print(f"[MEM_SAVE] {k}={v}"); return True
        def ottieni_contesto_memoria(self): return "Stand-alone profile."
    brain_interface = DummyBrainInterface()
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()

class MemoryTools:
    """
    Plugin: Memory
    Access to the Vault of memories and Admin profile (Identity and History).
    """

    def __init__(self):
        self.tag = "MEMORY"
        self.desc = "Access to the Vault of memories and Admin profile (Identity and History)."
        self.status = "ONLINE (Vault Access Granted)"

    def remember_info(self, text: str) -> str:
        """
        Save important information about the user in the biographical profile.
        Use this tool when the user tells you something about themselves, their preferences, or important facts.
        
        :param text: The detailed information to remember (e.g. 'The user likes coffee').
        """
        info_to_save = text.strip()
        success = brain_interface.aggiorna_profilo("note_biografiche", info_to_save)
        if success:
            return f"Archiviation protocol completed: I now remember that {info_to_save}."
        else:
            return "Critical error during biographical profile update."

    def who_am_i(self) -> str:
        """
        Ask Zentra to retrieve identity data for the Admin and the AI (context profile).
        Use this tool to read the current state of the relationship, personality, and known user traits.
        """
        return brain_interface.ottieni_contesto_memoria()

    def read_history(self, n: str) -> str:
        """
        Extract the last N saved messages from the database history.
        
        :param n: The number of previous messages to extract (e.g. '10').
        """
        try:
            count = int(n.strip())
            # This function will need to be implemented in brain_interface for SQL queries
            return f"Analyzing last {count} exchanges... (Database Consultation active)."
        except ValueError:
            return "Error: specify a valid number for reading."

    def reset_memory(self) -> str:
        """
        Execute the Tabula Rasa protocol: clear the entire episodic chat history.
        Use this tool ONLY if explicitly requested by the user to wipe the memory.
        """
        # Note: Actual deletion logic is handled here or by brain_interface
        # to ensure the integrity of the .db file
        try:
            db_path = "memory/archivio_chat.db"
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM cronologia")
                conn.commit()
                conn.close()
                return "OBLIVION protocol executed. Episodic history cleared. Tabula Rasa."
            else:
                return "Memory database not found."
        except Exception as e:
            return f"Memory reset failure: {e}"

# Istanzia pubblicamente lo strumento per l'esportazione verso il Core
tools = MemoryTools()

# --- COMPATIBILITY SHIMS ---
def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status

