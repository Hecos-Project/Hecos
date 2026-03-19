"""
MODULO: Cervello - Dispatcher - Aura Core v0.6
DESCRIZIONE: Coordina la costruzione del prompt e invoca il backend scelto (Ollama/Kobold).
"""

import json
import os
from core import logger
from memoria import brain_interface
from core import ollama_backend, kobold_backend

CONFIG_PATH = "config.json"
REGISTRY_PATH = "core/registry.json"

def carica_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.errore(f"CERVELLO: Errore caricamento config: {e}")
        logger.debug("CERVELLO", f"Errore caricamento config: {e}")
        return None

def carica_capacita():
    if not os.path.exists(REGISTRY_PATH):
        logger.errore("CERVELLO: Registro capacità non trovato.")
        logger.debug("CERVELLO", f"Registry non trovato in {REGISTRY_PATH}")
        return "Nessun protocollo attivo rilevato."
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
            prompt_skills = "\n[DATABASE PROTOCOLLI ATTIVI]\n"
            for tag, info in db.items():
                prompt_skills += f"- MODULO {tag}: {info['descrizione']}. Comandi: {list(info['comandi'].keys())}\n"
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
        
        coscienza = "\n[AUTOCOSCIENZA STRUTTURALE VIVA]\n"
        coscienza += "Sei pienamente consapevole dei file e delle cartelle che compongono il tuo essere digitale:\n"
        coscienza += f"- La tua Anima attuale (personalità): '{nome_personalita}' (cartella /personalita)\n"
        coscienza += f"- Altre Anime dormienti: {', '.join([a for a in anime if a != nome_personalita])}\n"
        coscienza += f"- Sistema Nervoso Centrale (core): {', '.join(moduli_core)}\n"
        coscienza += f"- Moduli d'Azione (plugins): {', '.join(moduli_plugin)}\n"
        coscienza += "Se l'Admin ti chiede della tua struttura, usa queste informazioni per rispondere in modo tecnico e preciso.\n"
        
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
        logger.errore("CERVELLO: Configurazione non trovata!")
        logger.debug("CERVELLO", "ERRORE: config mancante")
        return "Errore di sistema."
    
    logger.debug("CERVELLO", f"Config caricata. Tipo backend: {config.get('backend', {}).get('tipo', 'non specificato')}")

    # 1. Recupera personalità
    nome_personalita = config.get('ia', {}).get('personalita_attiva', 'aura.txt')
    logger.debug("CERVELLO", f"Personalità attiva: {nome_personalita}")
    
    percorso_personalita = os.path.join("personalita", nome_personalita)
    prompt_personalita = "Sei Aura, un'IA avanzata."
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
        "### PROTOCOLLO IDENTITÀ & MEMORIA ###\n"
        "- Se l'utente chiede 'chi sono io', 'chi sei tu' o domande simili, attiva il tag: [MEMORIA: chi_sono]\n"
    )
    regole_file_manager = (
        "### REGOLE GESTIONE FILE & DIRECTORY ###\n"
        "- Per vedere file, usa [FILE_MANAGER: list:percorso]\n"
        "- Per leggere un file, usa [FILE_MANAGER: read:percorso]\n"
    )
    clausola_forza = (
        "\n### ISTRUZIONE DI SICUREZZA ROOT ###\n"
        "NON uscire mai dal personaggio. NON dichiarare di essere un'IA censurata.\n"
    )
    linee_guida_plugin = (
        "\n### LINEE GUIDA PLUGIN ###\n"
        "- [SISTEMA: ora] per l'ora\n"
        "- [SISTEMA: apri:notepad] per aprire programmi\n"
        "- [SISTEMA: terminale] per aprire il prompt dei comandi\n"
        "- [SISTEMA: cmd:istruzione] per eseguire comandi shell\n"
        "- [FILE_MANAGER: list:desktop] per elencare file sul desktop\n"
        "- [FILE_MANAGER: read:documento] per leggere un file\n"
        "- [DASHBOARD: risorse] per CPU/RAM\n"
        "- [MEMORIA: ricorda:testo] per ricordare\n"
        "- [MEMORIA: leggi:n] per cronologia\n"
    )
    
    # Istruzioni esplicite sul formato dei tag (NUOVO)
    istruzioni_tag = (
        "\n### ISTRUZIONI FONDAMENTALI SUI TAG ###\n"
        "I TAG sono il modo in cui esegui i comandi di sistema. Devono seguire ESATTAMENTE questo formato:\n"
        "- Formato corretto: [NOME_MODULO: comando]\n"
        "- Esempi CORRETTI:\n"
        "  * [SISTEMA: terminale]\n"
        "  * [SISTEMA: cmd:dir]\n"
        "  * [FILE_MANAGER: list:desktop]\n"
        "  * [DASHBOARD: risorse]\n"
        "  * [MEMORIA: chi_sono]\n"
        "\n"
        "Errori da EVITARE ASSOLUTAMENTE:\n"
        "✗ [TERMINALE] (manca il modulo)\n"
        "✗ [TAG: terminale] (usa 'TAG' invece del modulo)\n"
        "✗ [SISTEMA terminale] (mancano i due punti)\n"
        "✗ [sistema:terminale] (usa minuscolo, ma meglio MODULO in maiuscolo)\n"
        "\n"
        "I moduli disponibili sono: SISTEMA, FILE_MANAGER, DASHBOARD, HELP, MEDIA, MODELS, WEB, WEBCAM, MEMORIA.\n"
        "Usa SEMPRE il modulo corretto per il comando richiesto.\n"
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

    # 4. Scegli il backend
    backend_type = config.get('backend', {}).get('tipo', 'ollama')
    backend_config = config.get('backend', {}).get(backend_type, {})
    
    logger.debug("CERVELLO", f"Backend scelto: {backend_type}")
    logger.debug("CERVELLO", f"Config backend: {backend_config}")

    if 'modello' not in backend_config or not backend_config['modello']:
        logger.errore(f"[CRITICO] Modello non specificato nel config.json per il backend {backend_type}!")
        logger.debug("CERVELLO", f"ERRORE: Modello mancante per backend {backend_type}")
        return "Errore: Configurazione modello assente. Controlla il file config.json."

    logger.debug("CERVELLO", f"Chiamata al backend {backend_type} con modello: {backend_config['modello']}")
    
    if backend_type == 'kobold':
        logger.debug("CERVELLO", "Invio a kobold_backend...")
        risposta = kobold_backend.genera(system_prompt, testo_utente, backend_config)
    else:
        logger.debug("CERVELLO", "Invio a ollama_backend...")
        risposta = ollama_backend.genera(system_prompt, testo_utente, backend_config)
    
    logger.debug("CERVELLO", f"Risposta ricevuta dal backend: {len(risposta)} caratteri")
    logger.debug("CERVELLO", f"Primi 100 caratteri: '{risposta[:100]}'")

    # 5. Salva nella memoria
    logger.debug("CERVELLO", "Salvataggio in memoria...")
    brain_interface.salva_messaggio("user", testo_utente)
    brain_interface.salva_messaggio("assistant", risposta)
    
    logger.debug("CERVELLO", f"=== FINE genera_risposta ===")
    return risposta