"""
Plugin Roleplay - Zentra Core
Permette di interpretare personaggi in scenari di gioco di ruolo.
"""

import json
import os
from core.logging import logger
from app.config import ConfigManager   # <--- per leggere configurazione

# Stato interno
_active_character = None
_active_character_prompt = None
_active_scene = None
_active_scene_prompt = None

# Directory predefinite (possono essere sovrascritte dalla configurazione)
_DEFAULT_CHARACTERS_DIR = os.path.join(os.path.dirname(__file__), "characters")
_DEFAULT_SCENES_DIR = os.path.join(os.path.dirname(__file__), "scenes")

def info():
    return {
        "tag": "ROLEPLAY",
        "desc": "Gestisce modalità roleplay: carica personaggi e scene per conversazioni immersive.",
        "comandi": {
            "list": "Elenca i personaggi disponibili.",
            "load: nome": "Carica il personaggio specificato (es. load: wizard).",
            "unload": "Disattiva il roleplay e torna alla personalità normale.",
            "scene: list": "Elenca le scene disponibili.",
            "scene: load: nome": "Carica una scena (aggiunge contesto).",
            "scene: unload": "Rimuove la scena corrente.",
            "reset": "Resetta il personaggio e la scena."
        }
    }

def status():
    if _active_character:
        return f"ONLINE (Personaggio: {_active_character})"
    return "ONLINE (Pronto)"

def config_schema():
    """
    Schema di configurazione per il plugin.
    I valori qui definiti verranno aggiunti automaticamente in config.json
    nella sezione plugins.ROLEPLAY.
    """
    return {
        "characters_dir": {
            "type": "str",
            "default": _DEFAULT_CHARACTERS_DIR,
            "description": "Percorso della cartella contenente i file JSON dei personaggi"
        },
        "scenes_dir": {
            "type": "str",
            "default": _DEFAULT_SCENES_DIR,
            "description": "Percorso della cartella contenente i file JSON delle scene"
        },
        "default_character": {
            "type": "str",
            "default": "",
            "description": "Nome del personaggio da caricare automaticamente all'avvio (vuoto = nessuno)"
        },
        "default_scene": {
            "type": "str",
            "default": "",
            "description": "Nome della scena da caricare automaticamente all'avvio (vuoto = nessuna)"
        }
    }

def _get_characters_dir():
    """Restituisce la directory dei personaggi configurata o quella predefinita."""
    cfg = ConfigManager()
    path = cfg.get_plugin_config("ROLEPLAY", "characters_dir", _DEFAULT_CHARACTERS_DIR)
    # Assicura che sia un percorso assoluto (se relativo, rispetto alla cartella del plugin)
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(__file__), path)
    return path

def _get_scenes_dir():
    """Restituisce la directory delle scene configurata o quella predefinita."""
    cfg = ConfigManager()
    path = cfg.get_plugin_config("ROLEPLAY", "scenes_dir", _DEFAULT_SCENES_DIR)
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(__file__), path)
    return path

def esegui(comando):
    global _active_character, _active_character_prompt, _active_scene, _active_scene_prompt
    cmd = comando.lower().strip()
    
    if cmd == "list":
        return _list_characters()
    elif cmd.startswith("load:"):
        name = cmd[5:].strip()
        return _load_character(name)
    elif cmd == "unload":
        return _unload()
    elif cmd == "scene: list":
        return _list_scenes()
    elif cmd.startswith("scene: load:"):
        name = cmd[12:].strip()
        return _load_scene(name)
    elif cmd == "scene: unload":
        return _unload_scene()
    elif cmd == "reset":
        return _reset()
    else:
        return "Comando roleplay non riconosciuto. Usa 'list', 'load:nome', 'unload', 'scene:list', 'scene:load:nome', 'scene:unload', 'reset'."

def _list_characters():
    chars_dir = _get_characters_dir()
    if not os.path.exists(chars_dir):
        return f"Nessun personaggio trovato (cartella '{chars_dir}' mancante)."
    files = [f[:-5] for f in os.listdir(chars_dir) if f.endswith('.json')]
    if not files:
        return "Nessun personaggio disponibile."
    return "Personaggi disponibili:\n- " + "\n- ".join(files)

def _load_character(name):
    global _active_character, _active_character_prompt
    chars_dir = _get_characters_dir()
    file_path = os.path.join(chars_dir, name + '.json')
    if not os.path.exists(file_path):
        return f"Personaggio '{name}' non trovato in {chars_dir}."
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
        logger.info(f"Roleplay: caricato personaggio {name}")
        return f"Personaggio '{name}' caricato. Ora interpreterai {data['nome']}."
    except Exception as e:
        logger.errore(f"Errore caricamento personaggio {name}: {e}")
        return f"Errore caricamento personaggio: {e}"

def _unload():
    global _active_character, _active_character_prompt, _active_scene, _active_scene_prompt
    _active_character = None
    _active_character_prompt = None
    _active_scene = None
    _active_scene_prompt = None
    logger.info("Roleplay disattivato")
    return "Roleplay disattivato. Tornato alla personalità normale."

def _list_scenes():
    scenes_dir = _get_scenes_dir()
    if not os.path.exists(scenes_dir):
        return f"Nessuna scena trovata (cartella '{scenes_dir}' mancante)."
    files = [f[:-5] for f in os.listdir(scenes_dir) if f.endswith('.json')]
    if not files:
        return "Nessuna scena disponibile."
    return "Scene disponibili:\n- " + "\n- ".join(files)

def _load_scene(name):
    global _active_scene, _active_scene_prompt
    scenes_dir = _get_scenes_dir()
    file_path = os.path.join(scenes_dir, name + '.json')
    if not os.path.exists(file_path):
        return f"Scena '{name}' non trovata in {scenes_dir}."
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        prompt = f"Ambientazione: {data.get('descrizione', '')}\n"
        if 'elementi' in data:
            prompt += f"Elementi presenti: {', '.join(data['elementi'])}\n"
        _active_scene = name
        _active_scene_prompt = prompt
        logger.info(f"Roleplay: caricata scena {name}")
        return f"Scena '{name}' caricata."
    except Exception as e:
        logger.errore(f"Errore caricamento scena {name}: {e}")
        return f"Errore caricamento scena: {e}"

def _unload_scene():
    global _active_scene, _active_scene_prompt
    _active_scene = None
    _active_scene_prompt = None
    return "Scena rimossa."

def _reset():
    global _active_character, _active_character_prompt, _active_scene, _active_scene_prompt
    _active_character = None
    _active_character_prompt = None
    _active_scene = None
    _active_scene_prompt = None
    return "Roleplay resettato."

# Funzione esposta per il cervello
def get_roleplay_prompt():
    """Restituisce il prompt combinato (personaggio + scena) se attivo, altrimenti None."""
    if _active_character_prompt:
        combined = _active_character_prompt
        if _active_scene_prompt:
            combined += "\n" + _active_scene_prompt
        return combined
    return None