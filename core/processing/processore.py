"""
MODULO: Processore Logico - Zentra Core v2.5
DESCRIZIONE: Il 'motore di esecuzione'. Trasforma il pensiero dell'IA in azioni 
reali tramite plugin e filtra il testo per la sintesi vocale.
Supporta la nuova struttura a cartelle dei plugin (plugins/nome_modulo/main.py).
Brain unificato.
"""
import sys
import re
import os
import json

import importlib.util
from core.llm import brain
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
    "memory": "file_manager",
    "personality": "file_manager",
    "logs": "file_manager",
    "config": "file_manager",
    "main": "file_manager",
}

def configura(nuova_config):
    """Riceve la configurazione dal Main e la memorizza per le chiamate al cervello (Brain)."""
    global config_attuale
    config_attuale = nuova_config
    logger.info("[PROCESSOR] Hardware configuration synchronized.")

def _importa_plugin(modulo_nome):
    """
    Importa dinamicamente un plugin dalla nuova struttura a cartelle.
    Cerca in: plugins/nome_modulo/main.py
    """
    try:
        plugin_path = os.path.join("plugins", modulo_nome, "main.py")
        if not os.path.exists(plugin_path):
            logger.debug("PROCESSOR", f"Plugin {modulo_nome} not found in {plugin_path}")
            return None
        
        spec = importlib.util.spec_from_file_location(
            f"plugins.{modulo_nome}.main", 
            plugin_path
        )
        if spec is None:
            logger.debug("PROCESSOR", f"Unable to create spec for {modulo_nome}")
            return None
            
        plugin_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin_module)
        logger.debug("PROCESSOR", f"Plugin {modulo_nome} imported successfully")
        return plugin_module
    except Exception as e:
        logger.errore(f"[PROCESSOR] Plugin import error for {modulo_nome}: {e}")
        logger.debug("PROCESSOR", f"Exception: {str(e)}")
        return None

def elabora_scambio(testo_utente, stato_voce):
    """Gestisce l'intera catena: IA -> Plugin -> Pulizia -> Risposta."""
    logger.info(f"[PROCESSOR] Input received: '{testo_utente}'. Calling brain...")
    logger.debug("PROCESSOR", f"Input received: '{testo_utente}' | Voice status: {stato_voce}")
    
    # 1. Genera risposta dall'IA
    logger.debug("PROCESSOR", "Calling brain.genera_risposta()")
    risposta_grezza = brain.genera_risposta(testo_utente, config_attuale)
    
    # 2. Analisi Tag Plugin e Tool Calls
    logger.debug("PROCESSOR", "Searching for tags or tool_calls in response...")
    
    # Rimuove i blocchi <think>...</think> prodotti dai reasoning model (Qwen, DeepSeek-R1, ecc.)
    # Lo facciamo qui prima di qualsiasi analisi per escludere il ragionamento interno dall'output
    if isinstance(risposta_grezza, str):
        risposta_grezza = re.sub(r'<think>.*?</think>', '', risposta_grezza, flags=re.DOTALL | re.IGNORECASE).strip()
        risposta_grezza = re.sub(r'<think>.*$', '', risposta_grezza, flags=re.DOTALL | re.IGNORECASE).strip()
    
    tags_trovati = []
    
    # Controlla se è una risposta strutturata (Function Calling nativo)
    is_tool_call_object = not isinstance(risposta_grezza, str) and hasattr(risposta_grezza, 'tool_calls') and risposta_grezza.tool_calls
    
    if is_tool_call_object:
        logger.info("[PROCESSOR] Native Function Calling detected.")
        for call in risposta_grezza.tool_calls:
            # call.function.name format: "tag__method"
            if "__" in call.function.name:
                tag, method = call.function.name.split("__", 1)
                try:
                    args = json.loads(call.function.arguments)
                except Exception as e:
                    logger.debug("PROCESSOR", f"Error parsing arguments: {e}")
                    args = {}
                
                # Formato tuple: (modulo, args, "function_call", method_name)
                tags_trovati.append((tag.lower(), args, "function_call", method))
                logger.debug("PROCESSOR", f"Function call extracted: {tag.upper()}.{method}() with args {args}")
            else:
                logger.debug("PROCESSOR", f"Unknown function format: {call.function.name}")
        
        # Testo grezzo verbale, se presente, altrimenti stringa vuota per evitare eccezioni
        testo_risposta_originale = getattr(risposta_grezza, 'content', "") or ""
        risposta_grezza = testo_risposta_originale
        logger.debug("PROCESSOR", f"Testo associato alla function call: '{risposta_grezza}'")
    else:
        # Se non è un oggetto tool_call, ci assicuriamo che sia una stringa
        if not isinstance(risposta_grezza, str):
            risposta_grezza = getattr(risposta_grezza, 'content', "") or ""
            
        logger.debug("PROCESSOR", f"Raw response received: {len(risposta_grezza)} characters")
        logger.debug("PROCESSOR", f"Content: '{risposta_grezza[:200]}...'")
        
        # Cerca tag standard [MODULO: comando] (Legacy)
        matches_standard = re.findall(r'\[(\w+):(.*?)\]', risposta_grezza)
        for tag, azione in matches_standard:
            tags_trovati.append((tag.lower(), azione.strip(), "standard", None))
            logger.debug("PROCESSOR", f"Standard tag found: {tag.upper()} -> '{azione}'")
        
        # Cerca tag semplici [MODULO] (Legacy)
        matches_semplici = re.findall(r'\[(\w+)\]', risposta_grezza)
        for tag in matches_semplici:
            if not any(t[0] == tag.lower() for t in tags_trovati):
                tags_trovati.append((tag.lower(), "", "semplice", None))
                logger.debug("PROCESSOR", f"Simple tag found: {tag.upper()}")
                
    # Processa TUTTI i test/tag trovati
    for tag_originale, azione_o_args, tipo, method_name in tags_trovati:
        # Determina il modulo da chiamare (con mappatura per legacy fallback)
        modulo_da_chiamare = tag_originale
        
        # Se il tag è "tag" (errore legacy AI), cerca di mappare l'azione
        if tag_originale == "tag" and not method_name and isinstance(azione_o_args, str):
            azione_pulita = azione_o_args.strip().lower()
            for keyword, modulo in TAG_MAPPING.items():
                if keyword in azione_pulita:
                    modulo_da_chiamare = modulo
                    logger.debug("PROCESSOR", f"Mapped 'tag' with action '{azione_pulita}' to module {modulo}")
                    break
            else:
                logger.debug("PROCESSOR", f"Tag 'tag' with action '{azione_o_args}' not mappable, ignored")
                continue
        
        if modulo_da_chiamare in BLACKLIST:
            logger.debug("PROCESSOR", f"Module {modulo_da_chiamare} blacklisted, ignored")
            continue
            
        logger.debug("PROCESSOR", f"Processing module {modulo_da_chiamare.upper()} (original tag: {tag_originale})")
        
        # Importa il plugin
        plugin_module = _importa_plugin(modulo_da_chiamare)
        
        if plugin_module:
            if method_name and hasattr(plugin_module, "tools"):
                # Esecuzione nuovo stile (Class-based/Function Calling)
                logger.debug("PROCESSOR", f"Executing native function {method_name} in {modulo_da_chiamare}")
                print(f"{GIALLO}[SYSTEM] {translator.t('executing_module', module=modulo_da_chiamare.upper())}{RESET}")
                try:
                    metodo = getattr(plugin_module.tools, method_name)
                    # Passa gli argomenti al metodo python
                    esito = metodo(**azione_o_args) if azione_o_args else metodo()
                    if esito:
                        logger.info(f"[PROCESSOR] Tool {method_name} output: {len(str(esito))} chars")
                        print(f"{CIANO}[OUTPUT {modulo_da_chiamare.upper()}]:\n{esito}{RESET}")
                except Exception as e:
                    logger.errore(f"[PROCESSOR] Tool execution error for {method_name}: {e}")
            elif hasattr(plugin_module, "esegui") and not method_name:
                # Esecuzione vecchio stile (Regex -> esegui(comando: str))
                logger.debug("PROCESSOR", f"Plugin {modulo_da_chiamare} has 'execute'; calling with: '{azione_o_args}'")
                print(f"{GIALLO}[SYSTEM] {translator.t('executing_module', module=modulo_da_chiamare.upper())}{RESET}")
                
                try:
                    esito = plugin_module.esegui(azione_o_args)
                    if esito:
                        logger.info(f"[PROCESSOR] Plugin {modulo_da_chiamare.upper()} output: {len(str(esito))} chars")
                        print(f"{CIANO}[OUTPUT {modulo_da_chiamare.upper()}]: {esito}{RESET}")
                except Exception as e:
                    logger.errore(f"[PROCESSOR] Plugin execution error for {modulo_da_chiamare}: {e}")
            else:
                logger.debug("PROCESSOR", f"Plugin {modulo_da_chiamare} format error / not found.")
        else:
            logger.debug("PROCESSOR", f"Plugin {modulo_da_chiamare} not loaded.")
    
    if not tags_trovati:
        logger.debug("PROCESSOR", "No tags/tools found in response")

    
        # 3. Pulizia per l'output video
    logger.debug("PROCESSOR", "Removing tags for video output")
    risposta_video = re.sub(r'\[.*?:.*?\]', '', risposta_grezza).strip()
    
    if not risposta_video:
        # Controlla se c'erano tag nella risposta originale
        if re.search(r'\[.*?\]', risposta_grezza):
            # C'erano tag, quindi probabilmente è stato eseguito un comando
            logger.debug("PROCESSOR", "Response contained only tags; command executed")
            risposta_video = translator.t('command_executed')
        else:
            # Nessun tag e nessuna risposta - problema col modello
            logger.warning("PROCESSOR", "Empty response received from model")
            risposta_video = translator.t('model_no_response_error')
    
    logger.debug("PROCESSOR", f"Final video response: {len(risposta_video)} characters")
    # Sanitizza per la stampa sicura su terminale Windows (previene charmap crash)
    risposta_video = filtri.pulisci_per_video(risposta_video)

    # 4. Preparazione Testo Vocale
    testo_pulito = ""
    if stato_voce:
        logger.debug("PROCESSOR", "Preparing text for speech synthesis")
        testo_pulito = filtri.pulisci_per_voce(risposta_video)
        logger.info("[PROCESSOR] Text filtered and prepared for speech synthesis.")
        logger.debug("PROCESSOR", f"Voice text: {len(testo_pulito)} characters")
        
    return risposta_video, testo_pulito