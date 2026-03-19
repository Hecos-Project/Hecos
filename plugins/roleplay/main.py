"""
Plugin Roleplay - Aura Core
Permette di interpretare personaggi in scenari di gioco di ruolo.
"""

import json
import os
from core import logger

# Stato interno
_active_character = None
_active_character_prompt = None
_active_scene = None
_active_scene_prompt = None

_characters_dir = os.path.join(os.path.dirname(__file__), "characters")
_scenes_dir = os.path.join(os.path.dirname(__file__), "scenes")

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
    if not os.path.exists(_characters_dir):
        return "Nessun personaggio trovato (cartella 'characters' mancante)."
    files = [f[:-5] for f in os.listdir(_characters_dir) if f.endswith('.json')]
    if not files:
        return "Nessun personaggio disponibile."
    return "Personaggi disponibili:\n- " + "\n- ".join(files)

def _load_character(name):
    global _active_character, _active_character_prompt
    file_path = os.path.join(_characters_dir, name + '.json')
    if not os.path.exists(file_path):
        return f"Personaggio '{name}' non trovato."
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
    if not os.path.exists(_scenes_dir):
        return "Nessuna scena trovata (cartella 'scenes' mancante)."
    files = [f[:-5] for f in os.listdir(_scenes_dir) if f.endswith('.json')]
    if not files:
        return "Nessuna scena disponibile."
    return "Scene disponibili:\n- " + "\n- ".join(files)

def _load_scene(name):
    global _active_scene, _active_scene_prompt
    file_path = os.path.join(_scenes_dir, name + '.json')
    if not os.path.exists(file_path):
        return f"Scena '{name}' non trovata."
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