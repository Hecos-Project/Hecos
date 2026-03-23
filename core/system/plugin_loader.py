"""
MODULO: Plugin Loader & Capability Registry - Zentra Core
DESCRIZIONE: Gestisce la scansione dinamica dei plugin (ora in sottocartelle) 
e la creazione del registro centrale JSON. Supporta anche la raccolta degli
schemi di configurazione per i plugin.
"""

import importlib.util
import os
import glob
import json
from core.logging import logger
from core.i18n import translator

REGISTRY_PATH = "core/registry.json"

# Memorizza gli schemi di configurazione raccolti dai plugin
_plugin_config_schemas = {}

# ... in cima al file ...
_loaded_plugins = {}   # tag -> modulo

def get_plugin_module(tag):
    """Restituisce il modulo del plugin se attivo, altrimenti None."""
    return _loaded_plugins.get(tag)

def aggiorna_registro_capacita(config=None, debug_log=True):
    """
    Scansiona la directory dei plugin, interroga il manifest info() e 
    genera un file JSON centralizzato con tutte le abilità attive.
    Se config è passato, lo usa per verificare il flag 'enabled'.
    """
    global _plugin_config_schemas
    _plugin_config_schemas.clear()
    skills_map = {}
    
    # Se non abbiamo config, lo carichiamo (per retrocompatibilità)
    if config is None:
        from app.config import ConfigManager
        config = ConfigManager().config
    
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
                tag = dati['tag']
                # Controlla flag enabled
                plugin_enabled = config.get('plugins', {}).get(tag, {}).get('enabled', True)
                if not plugin_enabled:
                    if debug_log: logger.debug("LOADER", f"Plugin {plugin_dir} disabilitato da config.")
                    continue
                    
                # Salva modulo e carica
                _loaded_plugins[tag] = modulo
                
                stato = modulo.status() if hasattr(modulo, "status") else "ONLINE"
                
                skills_map[tag] = {
                    "descrizione": dati['desc'],
                    "comandi": dati['comandi'],
                    "stato": stato,
                    "esempio": dati.get("esempio", "")
                }
                logger.debug("LOADER", f"Plugin {plugin_dir} caricato con tag {tag}")
                
                # Raccogli lo schema di configurazione se presente
                if hasattr(modulo, "config_schema"):
                    _plugin_config_schemas[tag] = modulo.config_schema()
                    logger.debug("LOADER", f"Plugin {plugin_dir} ha config_schema")
                    
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
                tag = dati['tag']
                
                # Controlla il flag enabled
                plugin_enabled = config.get('plugins', {}).get(tag, {}).get('enabled', True)
                if not plugin_enabled:
                    logger.debug("LOADER", f"Plugin legacy {nome_modulo} disabilitato, ignorato.")
                    continue
                
                stato = modulo.status() if hasattr(modulo, "status") else "ONLINE"
                
                skills_map[tag] = {
                    "descrizione": dati['desc'],
                    "comandi": dati['comandi'],
                    "stato": stato,
                    "esempio": dati.get("esempio", "")
                }
                logger.debug("LOADER", f"Plugin legacy {nome_modulo} caricato con tag {tag}")
                
                if hasattr(modulo, "config_schema"):
                    _plugin_config_schemas[tag] = modulo.config_schema()
                    logger.debug("LOADER", f"Plugin legacy {nome_modulo} ha config_schema")
                    
        except Exception as e:
            logger.errore(f"LOADER: Fallimento caricamento legacy {nome_modulo}: {e}")
            continue

    # Scrittura del registro centralizzato
    try:
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(skills_map, f, indent=4, ensure_ascii=False)
        if debug_log:
            logger.info(f"REGISTRY: Registro capacità aggiornato ({len(skills_map)} moduli).")
    except Exception as e:
        logger.errore(f"REGISTRY: Errore scrittura file: {e}")
    
    return skills_map

def sincronizza_config_plugin(config_manager=None):
    """
    Sincronizza le configurazioni dei plugin con il file config.json.
    Aggiunge le sezioni mancanti con i valori di default definiti negli schemi.
    Inoltre assicura che per ogni plugin esista la chiave 'enabled' (default True).
    """
    if config_manager is None:
        from app.config import ConfigManager
        config_manager = ConfigManager()
    
    config = config_manager.config
    if "plugins" not in config:
        config["plugins"] = {}
    
    updated = False
    for tag, schema in _plugin_config_schemas.items():
        plugin_cfg = config["plugins"].get(tag, {})
        # Assicura che enabled sia presente (default True)
        if "enabled" not in plugin_cfg:
            plugin_cfg["enabled"] = True
            updated = True
        # Aggiungi eventuali chiavi mancanti con i valori di default
        for key, props in schema.items():
            if key not in plugin_cfg:
                default = props.get("default")
                plugin_cfg[key] = default
                updated = True
        if updated:
            config["plugins"][tag] = plugin_cfg
    
    if updated:
        config_manager.save()
        logger.info("REGISTRY: Configurazioni plugin sincronizzate.")
    
    return config

def ottieni_capacita_formattate():
    """Restituisce una stringa leggibile per il terminale."""
    if not os.path.exists(REGISTRY_PATH):
        aggiorna_registro_capacita()
        
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    res = f"\n=== {translator.t('help_registry_title')} ===\n"
    for tag, info in data.items():
        res += f"\n[MODULO: {tag}] - {translator.t('system_status', status=info['stato'])}\n"
        res += f"{translator.t('help_role')} {info['descrizione']}\n"
        for cmd, spiegazione in info['comandi'].items():
            res += f"  • {tag}:{cmd} --> {spiegazione}\n"
    return res

def genera_guida_dinamica():
    """
    Scansiona tutte le cartelle dei plugin (attivi e disattivati) per ricavare 
    i metadati necessari a costruire la guida utente (F1).
    Ritorna una lista di dizionari con i dettagli dei moduli.
    """
    guida = []
    
    def scansiona_cartella(base_path, stato_forzato=None):
        if not os.path.exists(base_path): 
            return
            
        plugin_dirs = [d for d in os.listdir(base_path) 
                       if os.path.isdir(os.path.join(base_path, d)) 
                       and not d.startswith("__")
                       and d != "plugins_disabled"]
        
        for plugin_dir in plugin_dirs:
            main_file = os.path.join(base_path, plugin_dir, "main.py")
            if not os.path.exists(main_file):
                continue
            try:
                spec = importlib.util.spec_from_file_location(
                    f"guida_{os.path.basename(base_path)}_{plugin_dir}", 
                    main_file
                )
                if spec is None: 
                    continue
                modulo = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(modulo)
                
                if hasattr(modulo, "info"):
                    dati = modulo.info()
                    stato_effettivo = stato_forzato if stato_forzato else (modulo.status() if hasattr(modulo, "status") else translator.t("online"))
                    
                    guida.append({
                        "tag": dati['tag'],
                        "descrizione": dati.get('desc', 'Nessuna descrizione.'),
                        "comandi": dati.get('comandi', {}),
                        "stato": stato_effettivo,
                        "esempio": dati.get("esempio", "")
                    })
            except Exception as e:
                logger.errore(f"LOADER GUIDA: Fallimento {plugin_dir}: {e}")
                
    # 1. Scansiona plugin attivi
    scansiona_cartella("plugins")
    
    # 2. Scansiona plugin disabilitati (forza stato DISATTIVATO)
    scansiona_cartella(os.path.join("plugins", "plugins_disabled"), stato_forzato=translator.t("offline"))
    
    # 3. Scansiona vecchi plugin nella root "plugins" per compatibilità
    vecchi = glob.glob(os.path.join("plugins", "*.py"))
    for file in vecchi:
        nome_mod = os.path.basename(file)[:-3]
        if nome_mod.startswith("__") or nome_mod.startswith("_"): 
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"guida_{nome_mod}", file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "info"):
                dati = mod.info()
                stato_effettivo = mod.status() if hasattr(mod, "status") else translator.t("online")
                # Evita duplicati se presente in cartella
                if not any(g['tag'] == dati['tag'] for g in guida):
                    guida.append({
                        "tag": dati['tag'],
                        "descrizione": dati.get('desc', 'Nessuna descrizione.'),
                        "comandi": dati.get('comandi', {}),
                        "stato": stato_effettivo,
                        "esempio": dati.get("esempio", "")
                    })
        except: 
            pass

    # Ordina per tag alfabetico
    guida.sort(key=lambda x: x['tag'])
    return guida