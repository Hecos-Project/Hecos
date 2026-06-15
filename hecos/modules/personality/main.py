"""
personality/main.py
Modulo per la gestione delle personalità AI (Souls) in Hecos.
Offre comandi HDCS e tools per LLM.
"""

import os
import logging

_log = logging.getLogger("HecosPersonality")

# Dummy fallback per evitare crash in parsing se non c'è config
class DummyConfigMgr:
    def sync_available_personalities(self): return []
    def set(self, val, *keys): pass
    def save(self): return True

try:
    from hecos.app.config import ConfigManager
except ImportError:
    def ConfigManager(): return DummyConfigMgr()

class PersonalityTools:
    def __init__(self):
        self.tag = "PERSONALITY"
        self.desc = "Manage and switch AI personalities (souls) dynamically."
        
        self.slash_commands = [
            {
                "id": "switch_soul",
                "aliases": ["/soul", "/persona", "/personality"],
                "description": "Cambia l'anima (personalità) attiva del sistema",
                "usage": "/soul <nome_o_indice>",
                "icon": "🧠",
                "category": "SYSTEM",
                "requires_args": True,
            },
            {
                "id": "list_souls",
                "aliases": ["/souls", "/personas"],
                "description": "Elenca le personalità disponibili",
                "usage": "/souls",
                "icon": "📋",
                "category": "SYSTEM",
                "requires_args": False,
            }
        ]

    def _get_cfg_mgr(self):
        import sys
        if hasattr(sys, 'hecos_config_manager'):
            return sys.hecos_config_manager
        return ConfigManager()

    def list_souls(self, config_manager=None, **kwargs) -> str:
        """
        Elenca tutte le personalità (souls) attualmente disponibili nel sistema.
        L'LLM deve usare questo per capire quali opzioni l'utente ha a disposizione.
        """
        cfg = config_manager if config_manager else self._get_cfg_mgr()
        souls = cfg.sync_available_personalities()
        if not souls:
            return "Nessuna personalità trovata."
        
        out = ["## 🧠 Personalità Disponibili\n"]
        for i, s in enumerate(souls):
            clean_name = s.replace('.yaml', '')
            out.append(f"{i+1}. **{clean_name}**")
            
        out.append("\n*Usa `/soul <nome>` per cambiare.*")
        return "\n".join(out)

    def switch_soul(self, name_or_index: str, config_manager=None, **kwargs) -> str:
        """
        Cambia la personalità attiva. Accetta sia il nome esatto (es. "Motoko") sia l'indice numerico.
        Restituisce un messaggio di successo o errore.
        """
        cfg = config_manager if config_manager else self._get_cfg_mgr()
        souls = cfg.sync_available_personalities()
        if not souls:
            return "❌ Errore: Nessuna personalità disponibile."

        target = str(name_or_index).strip().lower()
        if not target:
            return "❌ Specifica un nome o un indice. Esempio: `/soul motoko` o `/soul 1`"
        
        # Try index
        if target.isdigit():
            idx = int(target) - 1
            if 0 <= idx < len(souls):
                return self._apply_soul(souls[idx], cfg)
            return f"❌ Errore: Indice {target} non valido."
            
        # Try exact or partial match
        for s in souls:
            clean_name = s.replace('.yaml', '').lower()
            if target == clean_name or target in clean_name:
                return self._apply_soul(s, cfg)
                
        return f"❌ Errore: Personalità '{name_or_index}' non trovata. Usa `/souls` per vedere le opzioni."

    def _apply_soul(self, filename: str, cfg) -> str:
        # Usa update_config che è il metodo originale e sicuro del core (che unisce dizionari e salva)
        payload = {"ai": {"active_personality": filename}}
        if cfg.update_config(payload):
            # Sincronizza a runtime i processori e i filtri, proprio come fa il Central Hub
            try:
                from hecos.core.processing import processore, filtri
                from hecos.core.system import module_loader
                import copy
                
                # Fetching the snapshot explicitly from the real config manager
                cfg_snapshot = copy.deepcopy(cfg.config)
                processore.configure(cfg_snapshot)
                module_loader.update_capability_registry(cfg_snapshot, debug_log=False)
                filtri.reset_cache()
            except Exception as e:
                _log.error(f"[PERSONALITY] Errore di sync background: {e}")
                
            name = filename.replace('.yaml', '')
            _log.info(f"[PERSONALITY] Anima cambiata in: {name}")
            return f"✅ **Personalità cambiata con successo a:** {name}\n\n*Nota: l'effetto è immediato nella chat e nella sidebar!*"
        else:
            return f"❌ Errore durante il salvataggio della nuova personalità ({filename})."

tools = PersonalityTools()

def info():
    return {"tag": tools.tag, "desc": tools.desc}

def get_plugin():
    return tools

def on_load(*args, **kwargs):
    """Chiamato al caricamento del modulo."""
    _log.info("[PERSONALITY] Modulo caricato - pronto per switch animico.")
