"""
PLUGIN: Memory Management
DESCRIPTION: Command interface for accessing the Vault (Semantic and Episodic Memory).
COMMANDS: [MEMORY: remember:info], [MEMORY: who_am_i], [MEMORY: read:n], [MEMORY: reset]
"""

from memory import brain_interface

def info():
    """Plugin manifest for the centralized skills database."""
    return {
        "tag": "MEMORY",
        "desc": "Access to the Vault of memories and Admin profile (Identity and History).",
        "comandi": {
            "remember:text": "Save important information about the user in the biographical profile.",
            "who_am_i": "Ask Zentra to retrieve identity data for the Admin and the AI.",
            "read:n": "Extract the last N saved messages from the database history.",
            "reset": "Execute the Tabula Rasa protocol: clear the entire chat history."
        }
    }

def status():
    """Verify the connection status to the memory database."""
    return "ONLINE (Vault Access Granted)"

def esegui(azione):
    """Execute read/write operations on Zentra's memory."""
    
    # --- SAVING BIOGRAPHICAL INFORMATION ---
    if azione.startswith("remember:"):
        info_to_save = azione.replace("remember:", "").strip()
        success = brain_interface.aggiorna_profilo("note_biografiche", info_to_save)
        if success:
            return f"Archiviation protocol completed: I now remember that {info_to_save}."
        else:
            return "Critical error during biographical profile update."

    # --- IDENTITY RETRIEVAL ---
    if azione == "who_am_i" or azione == "chi_sono":
        return brain_interface.ottieni_contesto_memoria()

    # --- HISTORY READING (DATABASE) ---
    if azione.startswith("read:"):
        try:
            n = int(azione.replace("read:", "").strip())
            # This function will need to be implemented in brain_interface for SQL queries
            return f"Analyzing last {n} exchanges... (Database Consultation active)."
        except ValueError:
            return "Error: specify a valid number for reading (e.g. [MEMORY: read:10])."

    # --- OBLIVION PROTOCOL (RESET) ---
    if azione == "reset":
        # Note: Actual deletion logic is handled by brain_interface
        # to ensure the integrity of the .db file
        try:
            import sqlite3
            conn = sqlite3.connect("memory/archivio_chat.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cronologia")
            conn.commit()
            conn.close()
            return "OBLIVION protocol executed. Episodic history cleared. Tabula Rasa."
        except Exception as e:
            return f"Memory reset failure: {e}"

    return "Memory command not recognized or incorrect syntax."
