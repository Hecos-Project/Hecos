"""
MODULO: Plugin Loader & Capability Registry - Aura Core
DESCRIZIONE: Gestisce la scansione dinamica dei plugin (ora in sottocartelle) 
e la creazione del registro centrale JSON.
"""

import importlib.util
import os
import glob
import json
from core import logger

REGISTRY_PATH = "core/registry.json"

def aggiorna_registro_capacita():
    """
    Scansiona la directory dei plugin, interroga il manifest info() e 
    genera un file JSON centralizzato con tutte le abilità attive.
    Supporta sia la vecchia struttura (file .py direttamente in plugins) 
    che la nuova struttura (sottocartelle con main.py).
    """
    skills_map = {}
    
    # Cerca nella nuova struttura (sottocartelle con main.py)
    plugin_dirs = [d for d in os.listdir("plugins") 
                  if os.path.isdir(os.path.join("plugins", d)) 
                  and not d.startswith("__")
                  and d != "plugins_disabled"]  # <--- IGNORA QUESTA CARTELLA
    
    for plugin_dir in plugin_dirs:
        main_file = os.path.join("plugins", plugin_dir, "main.py")
        if not os.path.exists(main_file):
            logger.debug("LOADER", f"Plugin {plugin_dir} senza main.py, ignorato")
            continue
        
        try:
            # Importazione dinamica del modulo
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_dir}.main", 
                main_file
            )
            if spec is None:
                continue
                
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
            
            # Estrazione manifest
            if hasattr(modulo, "info"):
                dati = modulo.info()
                stato = modulo.status() if hasattr(modulo, "status") else "ATTIVO"
                
                skills_map[dati['tag']] = {
                    "descrizione": dati['desc'],
                    "comandi": dati['comandi'],
                    "stato": stato,
                    "esempio": dati.get("esempio", "")
                }
                logger.debug("LOADER", f"Plugin {plugin_dir} caricato con tag {dati['tag']}")
        except Exception as e:
            logger.errore(f"LOADER: Fallimento caricamento {plugin_dir}: {e}")
            continue
    
    # 2. (Opzionale) Cerca anche nella vecchia struttura per compatibilità
    #    Plugin ancora presenti come file singoli in plugins/
    old_plugins = glob.glob(os.path.join("plugins", "*.py"))
    for file in old_plugins:
        nome_modulo = os.path.basename(file)[:-3]
        if nome_modulo.startswith("__") or nome_modulo.startswith("_"):
            continue
        
        # Evita di ricaricare plugin già trovati nella nuova struttura
        if any(nome_modulo == d for d in plugin_dirs):
            continue
            
        try:
            spec = importlib.util.spec_from_file_location(nome_modulo, file)
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
            
            if hasattr(modulo, "info"):
                dati = modulo.info()
                stato = modulo.status() if hasattr(modulo, "status") else "ATTIVO"
                
                skills_map[dati['tag']] = {
                    "descrizione": dati['desc'],
                    "comandi": dati['comandi'],
                    "stato": stato,
                    "esempio": dati.get("esempio", "")
                }
                logger.debug("LOADER", f"Plugin legacy {nome_modulo} caricato con tag {dati['tag']}")
        except Exception as e:
            logger.errore(f"LOADER: Fallimento caricamento legacy {nome_modulo}: {e}")
            continue

    # Scrittura del registro centralizzato
    try:
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(skills_map, f, indent=4, ensure_ascii=False)
        logger.info(f"REGISTRY: Registro capacità aggiornato ({len(skills_map)} moduli).")
    except Exception as e:
        logger.errore(f"REGISTRY: Errore scrittura file: {e}")
    
    return skills_map

def ottieni_capacita_formattate():
    """Restituisce una stringa leggibile per il terminale."""
    if not os.path.exists(REGISTRY_PATH):
        aggiorna_registro_capacita()
        
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    res = "\n=== PROTOCOLLI DI AZIONE ATTIVI (ROOT ACCESS) ===\n"
    for tag, info in data.items():
        res += f"\n[MODULO: {tag}] - Stato: {info['stato']}\n"
        res += f"Descrizione: {info['descrizione']}\n"
        for cmd, spiegazione in info['comandi'].items():
            res += f"  • {tag}:{cmd} --> {spiegazione}\n"
    return res