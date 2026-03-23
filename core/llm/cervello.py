"""
MODULO: Cervello - Dispatcher - Zentra Core v0.6
DESCRIZIONE: Coordina la costruzione del prompt e invoca il backend scelto (Ollama/Kobold).
"""

import json
import os
from core.logging import logger
from memoria import brain_interface
from core.llm import client
from core.i18n import translator

CONFIG_PATH = "config.json"
REGISTRY_PATH = "core/registry.json"

def carica_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.errore(f"CERVELLO: {translator.t('error')}: {e}")
        logger.debug("CERVELLO", f"Error loading config: {e}")
        return None

def carica_capacita():
    if not os.path.exists(REGISTRY_PATH):
        logger.errore("CERVELLO: Registry not found.")
        logger.debug("CERVELLO", f"Registry not found in {REGISTRY_PATH}")
        return translator.t("no_active_protocols") # I should add this key
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
            prompt_skills = f"\n{translator.t('active_protocols_db')}\n"
            for tag, info in db.items():
                modulo_label = translator.t("module")
                comandi_label = translator.t("commands")
                prompt_skills += f"- {modulo_label} {tag}: {info['descrizione']}. {comandi_label}: {list(info['comandi'].keys())}\n"
            logger.debug("CERVELLO", f"Capacità caricate: {len(db)} moduli")
            return prompt_skills
    except Exception as e:
        logger.errore(f"CERVELLO: Errore lettura abilità: {e}")
        logger.debug("CERVELLO", f"Errore lettura capacità: {e}")
        return ""

def genera_autocoscienza(nome_personalita):
    try:
        anime = [f for f in os.listdir("personalita") if f.endswith('.txt')]
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
        
        logger.debug("CERVELLO", f"Autocoscienza generata: {len(coscienza)} caratteri")
        return coscienza
    except Exception as e:
        logger.errore(f"CERVELLO: Errore di percezione autocoscienza: {e}")
        logger.debug("CERVELLO", f"Errore autocoscienza: {e}")
        return ""

def genera_risposta(testo_utente, config_esterno=None):
    logger.debug("CERVELLO", f"=== INIZIO genera_risposta ===")
    logger.debug("CERVELLO", f"Testo utente: '{testo_utente}'")
    logger.debug("CERVELLO", f"config_esterno fornito: {config_esterno is not None}")
    
    # Se il processore passa il config aggiornato lo usiamo, altrimenti carichiamo da file
    if config_esterno:
        config = config_esterno
        logger.debug("CERVELLO", "Usando config_esterno")
    else:
        config = carica_config()
        logger.debug("CERVELLO", "Usando config da file")
        
    if not config:
        logger.errore("CERVELLO: Config not found!")
        logger.debug("CERVELLO", "ERROR: missing config")
        return translator.t("error")
    
    logger.debug("CERVELLO", f"Config caricata. Tipo backend: {config.get('backend', {}).get('tipo', 'non specificato')}")

    # 1. Recupera personalità
    nome_personalita = config.get('ia', {}).get('personalita_attiva', 'zentra.txt')
    logger.debug("CERVELLO", f"Personalità attiva: {nome_personalita}")
    
    percorso_personalita = os.path.join("personalita", nome_personalita)
    prompt_personalita = "Sei Zentra, un'IA avanzata."
    if os.path.exists(percorso_personalita):
        try:
            with open(percorso_personalita, "r", encoding="utf-8") as f:
                prompt_personalita = f.read()
            logger.debug("CERVELLO", f"Personalità caricata: {len(prompt_personalita)} caratteri")
        except Exception as e:
            logger.errore(f"CERVELLO: Errore lettura personalità: {e}")
            logger.debug("CERVELLO", f"Errore lettura personalità: {e}")

    # 2. Memoria e autocoscienza
    logger.debug("CERVELLO", "Caricamento memoria...")
    contesto_memoria = brain_interface.ottieni_contesto_memoria()
    logger.debug("CERVELLO", f"Memoria: {len(contesto_memoria)} caratteri")
    
    logger.debug("CERVELLO", "Generazione autocoscienza...")
    autocoscienza = genera_autocoscienza(nome_personalita)
    logger.debug("CERVELLO", f"Autocoscienza: {len(autocoscienza)} caratteri")
    
    logger.debug("CERVELLO", "Caricamento capacità...")
    capacita = carica_capacita()
    logger.debug("CERVELLO", f"Capacità: {len(capacita)} caratteri")

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
        "\n### LINEE GUIDA PLUGIN ###\n"
        "- [SYSTEM: ora] per l'ora\n"
        "- [SYSTEM: apri:notepad] per aprire programmi\n"
        "- [SYSTEM: terminale] per aprire il prompt dei comandi\n"
        "- [SYSTEM: cmd:istruzione] per eseguire comandi shell\n"
        "- [FILE_MANAGER: list:desktop] per elencare file sul desktop\n"
        "- [FILE_MANAGER: read:documento] per leggere un file\n"
        "- [DASHBOARD: risorse] per CPU/RAM\n"
        "- [MEMORIA: ricorda:testo] per ricordare\n"
        "- [MEMORIA: leggi:n] per cronologia\n"
    )
    
    # Istruzioni esplicite sul formato dei tag (NUOVO)
    istruzioni_tag = (
        f"\n{translator.t('tag_instructions_title')}\n"
        f"{translator.t('tag_instructions_desc')}\n"
        f"- {translator.t('tag_format_correct')}\n"
        f"- {translator.t('tag_examples_title')}\n"
        "  * [SYSTEM: terminale]\n"
        "  * [SYSTEM: cmd:dir]\n"
        "  * [FILE_MANAGER: list:desktop]\n"
        "  * [DASHBOARD: risorse]\n"
        "  * [MEMORIA: chi_sono]\n"
        "\n"
        f"{translator.t('tag_errors_to_avoid')}\n"
        "✗ [TERMINALE] (manca il modulo)\n"
        "✗ [TAG: terminale] (usa 'TAG' instead of module)\n"
        "✗ [SYSTEM terminale] (mancano i due punti)\n"
        "✗ [sistema:terminale] (usa minuscolo, ma meglio MODULO in maiuscolo)\n"
        "\n"
        f"{translator.t('tag_available_modules', modules='SYSTEM, FILE_MANAGER, DASHBOARD, HELP, MEDIA, MODELS, WEB, WEBCAM, MEMORIA')}\n"
        f"{translator.t('tag_use_correct_module')}\n"
    )

    system_prompt = (
        f"{prompt_personalita}\n"
        f"{contesto_memoria}\n"
        f"{autocoscienza}\n"
        f"{capacita}\n"
        "### REGOLE OPERATIVE ###\n"
        "1. Usa i TAG [MODULO: comando] solo quando necessario.\n"
        "2. Sii coerente con la tua personalità.\n\n"
        f"{regole_identita}"
        f"{regole_file_manager}"
        f"{clausola_forza}"
        f"{linee_guida_plugin}"
        f"{istruzioni_tag}"  # <--- AGGIUNTO
    )
    
    logger.debug("CERVELLO", f"System prompt creato: {len(system_prompt)} caratteri")
    
    # Verifica se il plugin roleplay è attivo
    try:
        from plugins.roleplay.main import get_roleplay_prompt
        rp_prompt = get_roleplay_prompt()
        if rp_prompt:
            # Sostituisce il prompt di sistema con quello del roleplay
            system_prompt = rp_prompt
            logger.debug("CERVELLO", "Modalità roleplay attiva - prompt sostituito")
    except ImportError:
        pass
    except Exception as e:
        logger.errore(f"Errore nel plugin roleplay: {e}")

    # 4. Invocazione del client LiteLLM unificato
    backend_type = config.get('backend', {}).get('tipo', 'ollama')
    backend_config = config.get('backend', {}).get(backend_type, {})
    
    # Passiamo il tipo di backend al client per la logica interna
    backend_config['tipo_backend'] = backend_type
    
    logger.debug("CERVELLO", f"Backend scelto: {backend_type}")
    logger.debug("CERVELLO", f"Config backend: {backend_config}")

    if 'modello' not in backend_config or not backend_config['modello']:
        logger.errore(f"[CRITICAL] Model not specified in config.json for backend {backend_type}!")
        logger.debug("CERVELLO", f"ERROR: Missing model for backend {backend_type}")
        return f"{translator.t('error')}: {translator.t('model_config_missing')}"

    logger.debug("CERVELLO", f"Chiamata a LiteLLM ({backend_type}) con modello: {backend_config['modello']}")
    
    # Unica chiamata al client unificato
    risposta = client.generate(system_prompt, testo_utente, backend_config, config.get('llm', {}))
    
    logger.debug("CERVELLO", f"Risposta ricevuta dal backend: {len(risposta)} caratteri")
    logger.debug("CERVELLO", f"Primi 100 caratteri: '{risposta[:100]}'")

    # 5. Salva nella memoria
    logger.debug("CERVELLO", "Salvataggio in memoria...")
    brain_interface.salva_messaggio("user", testo_utente)
    brain_interface.salva_messaggio("assistant", risposta)
    
    logger.debug("CERVELLO", f"=== FINE genera_risposta ===")
    return risposta