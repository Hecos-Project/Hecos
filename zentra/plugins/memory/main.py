"""
PLUGIN: Memory Management
DESCRIPTION: Class-based interface for accessing the Vault (Semantic and Episodic Memory).
"""

import os
try:
    from memory import brain_interface
    from zentra.core.i18n import translator
except ImportError:
    # Minimal fallback for standalone testing
    class DummyBrainInterface:
        def update_profile(self, k, v): return True
        def get_context(self, *args, **kwargs): return "Stand-alone profile."
        def get_history(self, limit): return []
        def clear_history(self): return True
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
        success = brain_interface.update_profile("notes", info_to_save)
        if success:
            return f"Archiviation protocol completed: I now remember that {info_to_save}."
        else:
            return "Critical error during biographical profile update."

    def who_am_i(self) -> str:
        """
        Ask Zentra to retrieve identity data for the Admin and the AI (context profile).
        Use this tool to read the current state of the relationship, personality, and known user traits.
        """
        try:
            from app.config import ConfigManager
            cfg = ConfigManager().config
            personality_name = cfg.get('ai', {}).get('active_personality', 'zentra.txt')
            clean_name = personality_name.replace(".txt", "").replace("_", " ") if personality_name else "Zentra"
            return brain_interface.get_context(config=cfg, dynamic_name=clean_name)
        except Exception as e:
            from zentra.core.logging import logger
            logger.error(f"[MEMORY] who_am_i tool error: {e}")
            return brain_interface.get_context()

    def read_history(self, n: str) -> str:
        """
        Extract the last N saved messages from the database history.
        
        :param n: The number of previous messages to extract (e.g. '10').
        """
        try:
            count = int(n.strip())
            history = brain_interface.get_history(count)
            if not history:
                return "Episodic history is currently empty."
            
            res = f"Last {len(history)} messages extracted from Vault:\n"
            for role, msg in history:
                res += f"[{role.upper()}]: {msg[:200]}...\n"
            return res
        except ValueError:
            return "Error: specify a valid number for reading."
        except Exception as e:
            return f"Database consultation failure: {e}"

    def reset_memory(self) -> str:
        """
        Execute the Tabula Rasa protocol: clear the entire episodic chat history.
        Use this tool ONLY if explicitly requested by the user to wipe the memory.
        """
        if brain_interface.clear_history():
            return "OBLIVION protocol executed. Episodic history cleared. Tabula Rasa."
        else:
            return "Memory reset failure: check system logs."

# Publicly instantiate the tool for exporting to Core
tools = MemoryTools()

# --- COMPATIBILITY SHIMS ---
def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status
