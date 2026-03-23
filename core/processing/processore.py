"""
MODULO: Processore Logico - Zentra Core v2.5
DESCRIZIONE: Il 'motore di esecuzione'. Trasforma il pensiero dell'IA in azioni 
reali tramite plugin e filtra il testo per la sintesi vocale.
Supporta la nuova struttura a cartelle dei plugin (plugins/nome_modulo/main.py)
"""
import sys
import re
import os

import importlib.util
from core.llm import cervello
from core.processing import filtri
from core.logging import logger
from core.i18n import translator

# Colori per i log a video
GIALLO = '\033[93m'
CIANO = '\033[96m'
ROSSO = '\033[91m'
RESET = '\033[0m'

# Variabile globale per mantenere i parametri hardware
config_attuale = {}

# Blacklist di tag da ignorare
BLACKLIST = ["titolo", "anima", "regole", "database", "status", "tag"]

# Mappatura per tag generici al modulo corretto
TAG_MAPPING = {
    "terminale": "system",
    "cmd": "system",
    "istruzione": "system",
    "apri": "system",
    "notepad": "system",
    "chrome": "system",
    "visual studio": "system",
    "sillytavern": "system",
    "desktop": "file_manager",
    "download": "file_manager",
    "documenti": "file_manager",
    "core": "file_manager",
    "plugins": "file_manager",
    "memoria": "file_manager",
    "personalita": "file_manager",
    "logs": "file_manager",
    "config": "file_manager",
    "main": "file_manager",
}

def configura(nuova_config):
    """Riceve la configurazione dal Main e la memorizza per le chiamate al cervello."""
    global config_attuale
    config_attuale = nuova_config
    logger.info("[PROCESSORE] Configurazione hardware sincronizzata.")

def _importa_plugin(modulo_nome):
    """
    Importa dinamicamente un plugin dalla nuova struttura a cartelle.
    Cerca in: plugins/nome_modulo/main.py
    """
    try:
        plugin_path = os.path.join("plugins", modulo_nome, "main.py")
        if not os.path.exists(plugin_path):
            logger.debug("PROCESSORE", f"Plugin {modulo_nome} non trovato in {plugin_path}")
            return None
        
        spec = importlib.util.spec_from_file_location(
            f"plugins.{modulo_nome}.main", 
            plugin_path
        )
        if spec is None:
            logger.debug("PROCESSORE", f"Impossibile creare spec per {modulo_nome}")
            return None
            
        plugin_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin_module)
        logger.debug("PROCESSORE", f"Plugin {modulo_nome} importato con successo")
        return plugin_module
    except Exception as e:
        logger.errore(f"[PROCESSORE] Errore importazione plugin {modulo_nome}: {e}")
        logger.debug("PROCESSORE", f"Eccezione: {str(e)}")
        return None

def elabora_scambio(testo_utente, stato_voce):
    """Gestisce l'intera catena: IA -> Plugin -> Pulizia -> Risposta."""
    logger.info(f"[PROCESSORE] Ricevuto input: '{testo_utente}'. Chiamata al cervello...")
    logger.debug("PROCESSORE", f"Input ricevuto: '{testo_utente}' | Stato voce: {stato_voce}")
    
    # 1. Genera risposta dall'IA
    logger.debug("PROCESSORE", "Chiamata a cervello.genera_risposta()")
    risposta_grezza = cervello.genera_risposta(testo_utente, config_attuale)
    logger.debug("PROCESSORE", f"Risposta grezza ricevuta: {len(risposta_grezza)} caratteri")
    logger.debug("PROCESSORE", f"Contenuto: '{risposta_grezza[:200]}...'")
    
    logger.info("[PROCESSORE] Risposta grezza generata dall'IA.")
    
    # 2. Analisi Tag Plugin - cerca TUTTI i tag [MODULO: comando] o [MODULO]
    logger.debug("PROCESSORE", "Ricerca tag nella risposta...")
    
    # Lista per memorizzare tutti i tag trovati
    tags_trovati = []
    
    # Cerca tag standard [MODULO: comando]
    matches_standard = re.findall(r'\[(\w+):(.*?)\]', risposta_grezza)
    for tag, azione in matches_standard:
        tags_trovati.append((tag.lower(), azione.strip(), "standard"))
        logger.debug("PROCESSORE", f"Trovato tag standard: {tag.upper()} -> '{azione}'")
    
    # Cerca tag semplici [MODULO] (senza i due punti)
    matches_semplici = re.findall(r'\[(\w+)\]', risposta_grezza)
    for tag in matches_semplici:
        # Evita duplicati se il tag è già stato trovato come standard
        if not any(t[0] == tag.lower() for t in tags_trovati):
            tags_trovati.append((tag.lower(), "", "semplice"))
            logger.debug("PROCESSORE", f"Trovato tag semplice: {tag.upper()}")
    
    # Processa TUTTI i tag trovati
    for tag_originale, azione, tipo in tags_trovati:
        # Determina il modulo da chiamare (con mappatura)
        modulo_da_chiamare = tag_originale
        
        # Se il tag è "tag", cerca di capire il modulo dall'azione
        if tag_originale == "tag" and azione:
            # Prova a mappare l'azione a un modulo
            azione_pulita = azione.strip().lower()
            for keyword, modulo in TAG_MAPPING.items():
                if keyword in azione_pulita:
                    modulo_da_chiamare = modulo
                    logger.debug("PROCESSORE", f"Mappato tag 'tag' con azione '{azione}' a modulo {modulo}")
                    break
            else:
                # Se non trova mappatura, ignora
                logger.debug("PROCESSORE", f"Tag 'tag' con azione '{azione}' non mappabile, ignorato")
                continue
        
        if modulo_da_chiamare in BLACKLIST:
            logger.debug("PROCESSORE", f"Modulo {modulo_da_chiamare} in blacklist, ignorato")
            continue
            
        logger.debug("PROCESSORE", f"Elaborazione modulo {modulo_da_chiamare.upper()} (tag originale: {tag_originale})")
        
        # Importa il plugin dalla nuova struttura a cartelle
        plugin_module = _importa_plugin(modulo_da_chiamare)
        
        if plugin_module and hasattr(plugin_module, "esegui"):
            logger.debug("PROCESSORE", f"Plugin {modulo_da_chiamare} ha funzione esegui, chiamo con azione: '{azione}'")
            print(f"{GIALLO}[SYSTEM] {translator.t('executing_module', module=modulo_da_chiamare.upper())}{RESET}")
            
            try:
                esito = plugin_module.esegui(azione)
                if esito:
                    logger.info(f"[PROCESSORE] Output plugin {modulo_da_chiamare.upper()}: {esito}")
                    logger.debug("PROCESSORE", f"Output: {esito}")
                    print(f"{CIANO}[OUTPUT {modulo_da_chiamare.upper()}]: {esito}{RESET}")
                else:
                    logger.debug("PROCESSORE", f"Plugin {modulo_da_chiamare} non ha restituito output")
            except Exception as e:
                logger.errore(f"[PROCESSORE] Errore esecuzione plugin {modulo_da_chiamare}: {e}")
                logger.debug("PROCESSORE", f"Eccezione esecuzione: {str(e)}")
        else:
            logger.debug("PROCESSORE", f"Plugin {modulo_da_chiamare} non trovato o senza funzione esegui")
    
    if not tags_trovati:
        logger.debug("PROCESSORE", "Nessun tag trovato nella risposta")
    
        # 3. Pulizia per l'output video
    logger.debug("PROCESSORE", "Rimozione tag per output video")
    risposta_video = re.sub(r'\[.*?:.*?\]', '', risposta_grezza).strip()
    
    if not risposta_video:
        # Controlla se c'erano tag nella risposta originale
        if re.search(r'\[.*?\]', risposta_grezza):
            # C'erano tag, quindi probabilmente è stato eseguito un comando
            logger.debug("PROCESSORE", "Risposta conteneva solo tag, comando eseguito")
            risposta_video = translator.t('command_executed')
        else:
            # Nessun tag e nessuna risposta - problema col modello
            logger.warning("PROCESSORE", "Ricevuta risposta completamente vuota dal modello")
            risposta_video = translator.t('model_no_response_error')
    
    logger.debug("PROCESSORE", f"Risposta video finale: {len(risposta_video)} caratteri")

    # 4. Preparazione Testo Vocale
    testo_pulito = ""
    if stato_voce:
        logger.debug("PROCESSORE", "Preparazione testo per sintesi vocale")
        testo_pulito = filtri.pulisci_per_voce(risposta_video)
        logger.info("[PROCESSORE] Testo filtrato e preparato per la sintesi vocale.")
        logger.debug("PROCESSORE", f"Testo vocale: {len(testo_pulito)} caratteri")
        
    return risposta_video, testo_pulito