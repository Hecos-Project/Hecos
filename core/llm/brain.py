"""
MODULO: Brain - Dispatcher - Zentra Core v0.6
DESCRIZIONE: Coordina la costruzione del prompt e invoca il backend scelto (Ollama/Kobold).
"""

import json
import os
from core.logging import logger
from memory import brain_interface
from core.llm import client
from core.i18n import translator
from core.llm.manager import manager
from core.system.plugin_loader import ottieni_tools_schema, ottieni_legacy_schema

CONFIG_PATH = "config.json"
REGISTRY_PATH = "core/registry.json"

def carica_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.errore(f"BRAIN: {translator.t('error')}: {e}")
        logger.debug("BRAIN", f"Error loading config: {e}")
        return None

def carica_capacita():
    if not os.path.exists(REGISTRY_PATH):
        logger.errore("BRAIN: Registry not found.")
        logger.debug("BRAIN", f"Registry not found in {REGISTRY_PATH}")
        return translator.t("no_active_protocols") # I should add this key
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
            prompt_skills = f"\n{translator.t('active_protocols_db')}\n"
            for tag, info in db.items():
                modulo_label = translator.t("module")
                comandi_label = translator.t("commands")
                prompt_skills += f"- {modulo_label} {tag}: {info['descrizione']}. {comandi_label}: {list(info['comandi'].keys())}\n"
            logger.debug("BRAIN", f"Capabilities loaded: {len(db)} modules")
            return prompt_skills
    except Exception as e:
        logger.errore(f"BRAIN: Skills reading error: {e}")
        logger.debug("BRAIN", f"Capability reading error: {e}")
        return ""

def genera_autocoscienza(nome_personalita):
    try:
        anime = [f for f in os.listdir("personality") if f.endswith('.txt')]
        moduli_core = [f for f in os.listdir("core") if f.endswith('.py')]
        moduli_plugin = [f for f in os.listdir("plugins") if f.endswith('.py')]
        
        coscienza = f"\n{translator.t('structural_self_awareness')}\n"
        coscienza += f"{translator.t('awareness_desc')}\n"
        coscienza += f"- {translator.t('current_soul', name=nome_personalita)}\n"
        altre_anime = ', '.join([a for a in anime if a != nome_personalita])
        coscienza += f"- {translator.t('dormant_souls', souls=altre_anime)}\n"
        coscienza += f"- {translator.t('central_nervous_system', modules=', '.join(moduli_core))}\n"
        coscienza += f"- {translator.t('action_modules', modules=', '.join(moduli_plugin))}\n"
        coscienza += f"{translator.t('admin_structure_hint')}\n"
        
        logger.debug("BRAIN", f"Self-awareness generated: {len(coscienza)} characters")
        return coscienza
    except Exception as e:
        logger.errore(f"BRAIN: Self-awareness perception error: {e}")
        logger.debug("BRAIN", f"Self-awareness error: {e}")
        return ""

def genera_risposta(testo_utente, config_esterno=None, tag=None):
    logger.debug("BRAIN", f"=== START generate_response ===")
    logger.debug("BRAIN", f"User text: '{testo_utente}'")
    logger.debug("BRAIN", f"config_esterno fornito: {config_esterno is not None}")
    
    # Se il processore passa il config aggiornato lo usiamo, altrimenti carichiamo da file
    if config_esterno:
        config = config_esterno
        logger.debug("BRAIN", "Using external_config")
    else:
        config = carica_config()
        logger.debug("BRAIN", "Using file config")
        
    if not config:
        logger.errore("BRAIN: Config not found!")
        logger.debug("BRAIN", "ERROR: missing config")
        return translator.t("error")
    
    logger.debug("BRAIN", f"Config loaded. Backend type: {config.get('backend', {}).get('tipo', 'unspecified')}")

    # 1. Recupera personalità
    nome_personalita = config.get('ia', {}).get('personalita_attiva', 'zentra.txt')
    logger.debug("BRAIN", f"Active personality: {nome_personalita}")
    
    percorso_personalita = os.path.join("personality", nome_personalita)
    prompt_personalita = "You are Zentra, an advanced AI."
    if os.path.exists(percorso_personalita):
        try:
            with open(percorso_personalita, "r", encoding="utf-8") as f:
                prompt_personalita = f.read()
            logger.debug("BRAIN", f"Personality loaded: {len(prompt_personalita)} characters")
        except Exception as e:
            logger.errore(f"BRAIN: Personality reading error: {e}")
            logger.debug("BRAIN", f"Personality reading error: {e}")

    # 2. Memoria e autocoscienza
    logger.debug("BRAIN", "Memory loading...")
    contesto_memoria = brain_interface.ottieni_contesto_memoria()
    logger.debug("BRAIN", f"Memory: {len(contesto_memoria)} characters")
    
    logger.debug("BRAIN", "Self-awareness generation...")
    autocoscienza = genera_autocoscienza(nome_personalita)
    logger.debug("BRAIN", f"Self-awareness: {len(autocoscienza)} characters")
    
    logger.debug("BRAIN", "Capabilities loading...")
    capacita = carica_capacita()
    logger.debug("BRAIN", f"Capabilities: {len(capacita)} characters")

    # 3. Regole e linee guida
    regole_identita = (
        f"{translator.t('identity_protocol')}\n"
        f"- {translator.t('rule_who_am_i')}\n"
    )
    regole_file_manager = (
        f"{translator.t('file_management_rules')}\n"
        f"- {translator.t('rule_list_files')}\n"
        f"- {translator.t('rule_read_file')}\n"
    )
    clausola_forza = (
        f"\n{translator.t('root_security_instruction')}\n"
        f"{translator.t('root_security_desc')}\n"
    )
    linee_guida_plugin = (
        "\n### PLUGIN GUIDELINES ###\n"
        "- [SYSTEM: time] for the current time\n"
        "- [SYSTEM: open:notepad] to open programs\n"
        "- [SYSTEM: terminal] to open the command prompt\n"
        "- [SYSTEM: cmd:instruction] to execute shell commands\n"
        "- [FILE_MANAGER: list:desktop] to list files on the desktop\n"
        "- [FILE_MANAGER: read:document] to read a file\n"
        "- [DASHBOARD: resources] for CPU/RAM\n"
        "- [MEMORY: remember:text] to remember\n"
        "- [MEMORY: read:n] for history\n"
    )
    
    # --- MOTORE ROUTING (DUAL ENGINE) ---
    routing_cfg = config.get('motore_routing', {})
    modalita = routing_cfg.get('modalita', 'auto')
    modelli_legacy_str = routing_cfg.get('modelli_legacy', '')
    
    # Risoluzione del modello provvisoria (per capire quale stiamo per usare)
    from app.model_manager import ModelManager
    effective_backend_type, effective_default_model = ModelManager.get_effective_model_info(config)
    modello_risolto_temp = manager.resolve_model(tag, config_override=config)
    current_model = (modello_risolto_temp or effective_default_model).lower()

    is_legacy = False
    if modalita == 'forza_legacy':
        is_legacy = True
    elif modalita == 'auto':
        legacy_list = [m.strip().lower() for m in modelli_legacy_str.split(',') if m.strip()]
        if any(legacy_m in current_model for legacy_m in legacy_list):
            is_legacy = True
            
    if is_legacy:
        logger.debug("BRAIN", f"Routing: DUAL ENGINE -> LEGACY MODE (Tag Engine) per {current_model}")
        istruzioni_tag = (
            f"\n{translator.t('tag_instructions_title')}\n"
            f"{translator.t('tag_instructions_desc')}\n"
            f"{ottieni_legacy_schema()}\n"
        )
        tools = None
    else:
        logger.debug("BRAIN", f"Routing: DUAL ENGINE -> NATIVE MODE (JSON Calling) per {current_model}")
        istruzioni_tag = ""  # No manual tags needed for Native tools
        tools = ottieni_tools_schema()

    system_prompt = (
        f"{prompt_personalita}\n"
        f"{contesto_memoria}\n"
        f"{autocoscienza}\n"
        f"{capacita}\n"
        "### OPERATIVE RULES ###\n"
        "1. Be consistent with your personality.\n\n"
        f"{regole_identita}"
        f"{regole_file_manager}"
        f"{clausola_forza}"
        f"{linee_guida_plugin}"
        f"{istruzioni_tag}"
    )
    
    logger.debug("BRAIN", f"System prompt created: {len(system_prompt)} characters")
    
    # Verifica se il plugin roleplay è attivo
    try:
        from plugins.roleplay.main import get_roleplay_prompt
        rp_prompt = get_roleplay_prompt()
        if rp_prompt:
            # Sostituisce il prompt di sistema con quello del roleplay
            system_prompt = rp_prompt
            tag = "ROLEPLAY" # <--- Imposta il tag per lo smistamento del modello
            logger.debug("BRAIN", "Roleplay mode active - prompt replaced and tag set")
    except ImportError:
        pass
    except Exception as e:
        logger.errore(f"Roleplay plugin error: {e}")

    # 4. Risoluzione del modello e Invocazione del client LiteLLM unificato
    from app.model_manager import ModelManager
    effective_backend_type, effective_default_model = ModelManager.get_effective_model_info(config)
    
    backend_config = config.get('backend', {}).get(effective_backend_type, {}).copy() # Copia per non sporcare il config globale
    
    # Risoluzione dinamica del modello tramite LLMManager
    modello_risolto = manager.resolve_model(tag, config_override=config)
    if modello_risolto:
        backend_config['modello'] = modello_risolto
        logger.debug("BRAIN", f"Model resolved for tag '{tag}': {modello_risolto}")
        
        # Se il modello risolto (es da un plugin) è cloud, assicuriamoci che client.py sappia di mandarlo al provider
        is_cloud = any(modello_risolto.startswith(p + "/") for p in ["groq", "openai", "anthropic", "gemini", "cohere"])
        backend_config['tipo_backend'] = "cloud" if is_cloud else effective_backend_type
    else:
        # Fallback ultra-sicuro
        backend_config['modello'] = effective_default_model
        backend_config['tipo_backend'] = effective_backend_type
        
    logger.debug("BRAIN", f"Backend chosen: {backend_config['tipo_backend']}")

    if 'modello' not in backend_config or not backend_config['modello'] or backend_config['modello'] == 'N/D':
        logger.errore(f"[CRITICAL] Model not specified in config.json for backend {effective_backend_type}!")
        logger.debug("BRAIN", f"ERROR: Missing model for backend {effective_backend_type}")
        return f"{translator.t('error')}: {translator.t('model_config_missing')}"

    logger.debug("BRAIN", f"LiteLLM call ({backend_config['tipo_backend']}) with model: {backend_config['modello']}")
    
    # Unica chiamata al client unificato
    risposta = client.generate(system_prompt, testo_utente, backend_config, config.get('llm', {}), tools=tools)
    
    # 5. Salva nella memoria
    logger.debug("BRAIN", "Saving to memory...")
    brain_interface.salva_messaggio("user", testo_utente)
    
    # Gestione strutturata della risposta (Stringa o Message con tool_calls)
    if isinstance(risposta, str):
        logger.debug("BRAIN", f"Response received from backend: {len(risposta)} characters")
        logger.debug("BRAIN", f"First 100 characters: '{risposta[:100]}'")
        brain_interface.salva_messaggio("assistant", risposta)
    else:
        # È un oggetto Message (ha usato un tool)
        logger.debug("BRAIN", "Response is a tool call object.")
        tool_names = [call.function.name for call in getattr(risposta, 'tool_calls', [])]
        brain_interface.salva_messaggio("assistant", f"*(Tool call: {', '.join(tool_names)})*")
    
    logger.debug("BRAIN", f"=== END generate_response ===")
    return risposta