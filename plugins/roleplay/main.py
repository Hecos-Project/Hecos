"""
Plugin Roleplay - Zentra Core
Permette di interpretare personaggi in scenari di gioco di ruolo.
"""

import json
import os
try:
    from core.logging import logger
    from core.i18n import translator
    from app.config import ConfigManager
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[RP_DEBUG]", *args)
        def info(self, *args, **kwargs): print("[RP_INFO]", *args)
        def errore(self, *args, **kwargs): print("[RP_ERR]", *args)
    logger = DummyLogger()
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()
    class DummyConfigMgr:
        def __init__(self): self.config = {}
        def get_plugin_config(self, tag, key, default): return default
    ConfigManager = DummyConfigMgr

# Stato interno (Modulo-level per mantenere compatibilità con brain.py)
_active_character = None
_active_character_prompt = None
_active_scene = None
_active_scene_prompt = None

# Directory predefinite
_DEFAULT_CHARACTERS_DIR = os.path.join(os.path.dirname(__file__), "characters")
_DEFAULT_SCENES_DIR = os.path.join(os.path.dirname(__file__), "scenes")

def get_roleplay_prompt():
    """Restituisce il prompt combinato (personaggio + scena) se attivo, altrimenti None."""
    if _active_character_prompt:
        combined = _active_character_prompt
        if _active_scene_prompt:
            combined += "\n" + _active_scene_prompt
        return combined
    return None

class RoleplayTools:
    """
    Plugin: Roleplay
    Permette di caricare e gestire personaggi e scenari per il gioco di ruolo.
    """

    def __init__(self):
        self.tag = "ROLEPLAY"
        self.desc = translator.t("plugin_roleplay_desc")
        self.config_schema = {
            "characters_dir": {
                "type": "str",
                "default": _DEFAULT_CHARACTERS_DIR,
                "description": translator.t("plugin_roleplay_chars_dir_desc")
            },
            "scenes_dir": {
                "type": "str",
                "default": _DEFAULT_SCENES_DIR,
                "description": translator.t("plugin_roleplay_scenes_dir_desc")
            },
            "default_character": {
                "type": "str",
                "default": "",
                "description": translator.t("plugin_roleplay_default_char_desc")
            },
            "default_scene": {
                "type": "str",
                "default": "",
                "description": translator.t("plugin_roleplay_default_scene_desc")
            }
        }

    @property
    def status(self):
        if _active_character:
            return translator.t("plugin_roleplay_status_active", name=_active_character)
        return translator.t("plugin_roleplay_status_online")

    def _get_characters_dir(self) -> str:
        cfg = ConfigManager()
        path = cfg.get_plugin_config("ROLEPLAY", "characters_dir", _DEFAULT_CHARACTERS_DIR)
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(__file__), path)
        return path

    def _get_scenes_dir(self) -> str:
        cfg = ConfigManager()
        path = cfg.get_plugin_config("ROLEPLAY", "scenes_dir", _DEFAULT_SCENES_DIR)
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(__file__), path)
        return path

    def list_characters(self) -> str:
        """Elenca tutti i personaggi disponibili per il gioco di ruolo."""
        chars_dir = self._get_characters_dir()
        if not os.path.exists(chars_dir):
            return f"No character found (folder '{chars_dir}' missing)."
        files = [f[:-5] for f in os.listdir(chars_dir) if f.endswith('.json')]
        if not files:
            return "No characters available."
        return "Available characters:\n- " + "\n- ".join(files)

    def load_character(self, name: str) -> str:
        """
        Carica un personaggio dal suo nome per interpretarne il ruolo.
        
        :param name: Il nome del personaggio da caricare (esatto).
        """
        global _active_character, _active_character_prompt
        chars_dir = self._get_characters_dir()
        file_path = os.path.join(chars_dir, name.strip() + '.json')
        if not os.path.exists(file_path):
            return f"Character '{name}' not found in {chars_dir}."
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            prompt = f"Sei {data['nome']}. {data.get('descrizione', '')}\n"
            prompt += f"Personalità: {data.get('personalita', '')}\n"
            if 'tratti' in data:
                prompt += f"Tratti: {', '.join(data['tratti'])}\n"
            if 'storia' in data:
                prompt += f"Storia: {data['storia']}\n"
            _active_character = name
            _active_character_prompt = prompt
            logger.info(f"Roleplay: loaded character {name}")
            return f"Character '{name}' loaded. Now roleplaying as {data['nome']}."
        except Exception as e:
            logger.errore(f"Error loading character {name}: {e}")
            return f"Errore caricamento personaggio: {e}"

    def unload_character(self) -> str:
        """Disattiva il personaggio corrente e torna alla personalità normale."""
        global _active_character, _active_character_prompt
        _active_character = None
        _active_character_prompt = None
        logger.info("Roleplay character deactivated")
        return "Roleplay deactivated. Returned to normal personality."

    def list_scenes(self) -> str:
        """Elenca tutte le scene disponibili per il gioco di ruolo."""
        scenes_dir = self._get_scenes_dir()
        if not os.path.exists(scenes_dir):
            return f"No scene found (folder '{scenes_dir}' missing)."
        files = [f[:-5] for f in os.listdir(scenes_dir) if f.endswith('.json')]
        if not files:
            return "No scenes available."
        return "Available scenes:\n- " + "\n- ".join(files)

    def load_scene(self, name: str) -> str:
        """
        Carica un'ambientazione o scena specifica per il gioco di ruolo.
        
        :param name: Il nome della scena da caricare.
        """
        global _active_scene, _active_scene_prompt
        scenes_dir = self._get_scenes_dir()
        file_path = os.path.join(scenes_dir, name.strip() + '.json')
        if not os.path.exists(file_path):
            return f"Scene '{name}' not found in {scenes_dir}."
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            prompt = f"Ambientazione: {data.get('descrizione', '')}\n"
            if 'elementi' in data:
                prompt += f"Elementi presenti: {', '.join(data['elementi'])}\n"
            _active_scene = name
            _active_scene_prompt = prompt
            logger.info(f"Roleplay: loaded scene {name}")
            return f"Scene '{name}' loaded."
        except Exception as e:
            logger.errore(f"Error loading scene {name}: {e}")
            return f"Errore caricamento scena: {e}"

    def unload_scene(self) -> str:
        """Rimuove la scena o l'ambientazione attuale."""
        global _active_scene, _active_scene_prompt
        _active_scene = None
        _active_scene_prompt = None
        return "Scene removed."

    def reset_roleplay(self) -> str:
        """Reset completo di personaggi e scene attive."""
        global _active_character, _active_character_prompt, _active_scene, _active_scene_prompt
        _active_character = None
        _active_character_prompt = None
        _active_scene = None
        _active_scene_prompt = None
        return "Roleplay reset completely."

# Istanzia pubblicamente lo strumento per l'esportazione verso il Core
tools = RoleplayTools()

# --- COMPATIBILITY SHIMS ---
def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status