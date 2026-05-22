"""
PLUGIN: Memory Management
DESCRIPTION: Class-based interface for accessing the Vault (Semantic and Episodic Memory).
             Includes RAG vector memory tools: rag_search, rag_store, rag_ingest_file.
"""

import os
try:
    from memory import brain_interface
    from hecos.core.i18n import translator
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
    Includes RAG vector memory tools for long-term semantic recall.
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
        Ask Hecos to retrieve identity data for the Admin and the AI (context profile).
        Use this tool to read the current state of the relationship, personality, and known user traits.
        """
        try:
            from app.config import ConfigManager
            cfg = ConfigManager().config
            personality_name = cfg.get('ai', {}).get('active_personality', 'Hecos_System_Soul.yaml')
            clean_name = personality_name.replace(".yaml", "").replace("_", " ") if personality_name else "Hecos"
            return brain_interface.get_context(config=cfg, dynamic_name=clean_name)
        except Exception as e:
            from hecos.core.logging import logger
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

    # ── RAG Vector Memory tools ────────────────────────────────────────────────

    def rag_search(self, query: str) -> str:
        """
        Perform a semantic search in the long-term vector memory (RAG).
        Use this tool when the user asks about past conversations, stored documents,
        or facts they previously shared, and the answer is not in the immediate context.

        :param query: The question or topic to search for in the knowledge base.
        """
        try:
            from hecos.core.rag import get_rag_engine
            engine = get_rag_engine()
            if not engine.is_enabled():
                return "RAG Vector Memory is currently disabled in configuration."
            chunks = engine.search(query, top_k=5)
            if not chunks:
                return "No relevant information found in the knowledge base for that query."
            lines = [f"[RAG RECALL — top {len(chunks)} results for: '{query}']"]
            for i, c in enumerate(chunks, 1):
                src = f" (source: {c.source})" if c.source else ""
                lines.append(f"{i}.{src} {c.text[:400]}")
            return "\n".join(lines)
        except Exception as e:
            return f"RAG search error: {e}"

    def rag_store(self, text: str, label: str = "user_note") -> str:
        """
        Store a piece of information permanently in the vector knowledge base.
        Use this when the user tells you something important to remember long-term,
        beyond the normal episodic chat history.

        :param text: The information to store (e.g. 'My favourite colour is violet').
        :param label: A short descriptive label for this memory (e.g. 'colour_preference').
        """
        try:
            from hecos.core.rag import get_rag_engine
            engine = get_rag_engine()
            if not engine.is_enabled():
                # Fallback: save to profile notes as before
                success = brain_interface.update_profile("notes", text.strip())
                return "RAG disabled — saved to biographical profile instead." if success else "Save failed."
            result = engine.ingest_text(text.strip(), source=label, namespace="knowledge")
            if result and result.ok:
                return f"Knowledge stored: '{label}' — {result.chunk_count} chunk(s) indexed in vector memory."
            return "Vector storage failed. Check system logs."
        except Exception as e:
            return f"rag_store error: {e}"

    def rag_ingest_file(self, path: str) -> str:
        """
        Ingest a local file into the vector knowledge base.
        Supported formats: .txt, .md, .pdf.
        Use this when the user says 'remember this document' or 'read this file'.

        :param path: Absolute or relative path to the file to ingest.
        """
        try:
            from hecos.core.rag import get_rag_engine
            import os
            engine = get_rag_engine()
            if not engine.is_enabled():
                return "RAG Vector Memory is disabled. Enable it in the Cognition System settings."
            if not os.path.exists(path):
                return f"File not found: {path}"
            result = engine.ingest_file(path, namespace="documents")
            if result and result.ok:
                fname = os.path.basename(path)
                return f"File '{fname}' successfully ingested: {result.chunk_count} chunks indexed in vector memory."
            err = result.error if result else "Unknown error"
            return f"File ingestion failed: {err}"
        except Exception as e:
            return f"rag_ingest_file error: {e}"

# Publicly instantiate the tool for exporting to Core
tools = MemoryTools()

# --- COMPATIBILITY SHIMS ---
def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status
