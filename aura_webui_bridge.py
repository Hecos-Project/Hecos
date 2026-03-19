"""
FILE: aura_webui_bridge.py
VERSIONE: 2.1 (Valvole & Debug Edition - FIXED)
AUTORE: Progetto AURA
"""

import sys
import os
import time
import json
import logging
import requests
from typing import Generator

BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BRIDGE_DIR)
if BRIDGE_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_DIR)

# Import dei moduli core di Aura (necessari per system prompt e memoria)
try:
    from core import cervello, processore, logger as core_logger
    from memoria import brain_interface
    from app.config import ConfigManager
except ImportError as e:
    print(f"[ERRORE CRITICO] Impossibile importare i moduli core di Aura: {e}")
    sys.exit(1)

# --- SETUP LOGGER DEL BRIDGE (su file separato) ---
bridge_logger = logging.getLogger("WebUI_Bridge")
bridge_logger.setLevel(logging.DEBUG)
# Assicura che la cartella logs esista
os.makedirs(os.path.join(BRIDGE_DIR, "logs"), exist_ok=True)
fh = logging.FileHandler(os.path.join(BRIDGE_DIR, "logs", "bridge_debug.log"), encoding='utf-8')
fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
bridge_logger.addHandler(fh)

class AuraWebUIBridge:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config

        # Legge le 'valvole' dal config
        self.bridge_cfg = self.config.get("bridge", {})
        self.usa_processore = self.bridge_cfg.get("usa_processore", False)
        self.delay_ms = self.bridge_cfg.get("ritardo_chunk_ms", 0) / 1000.0
        self.debug_attivo = self.bridge_cfg.get("debug_log", True)
        self.rimuovi_think = self.bridge_cfg.get("rimuovi_think_tags", True)

        if self.debug_attivo:
            bridge_logger.info("=" * 40)
            bridge_logger.info("INIZIALIZZAZIONE BRIDGE COMPLETATA")
            bridge_logger.info(f"Valvole: Processore={self.usa_processore}, Delay={self.delay_ms}s, Rimuovi think={self.rimuovi_think}")

        # Inizializza il core (memoria, plugin) – necessario per il system prompt
        try:
            brain_interface.inizializza_caveau()
            # Non serve ricaricare i plugin a ogni chiamata, ma per sicurezza:
            # plugin_loader.aggiorna_registro_capacita()  # se vuoi, altrimenti lascia
        except Exception as e:
            bridge_logger.error(f"Errore inizializzazione core: {e}")

    def _get_system_prompt(self):
        """Costruisce il system prompt come nel cervello originale."""
        personalita_file = self.config.get('ia', {}).get('personalita_attiva', 'aura.txt')
        path_p = os.path.join(BRIDGE_DIR, "personalita", personalita_file)
        testo_personalita = ""
        if os.path.exists(path_p):
            with open(path_p, "r", encoding="utf-8") as f:
                testo_personalita = f.read()

        memoria_identita = brain_interface.ottieni_contesto_memoria()
        capacita = cervello.carica_capacita()

        # Aggiungi regole di base (copiate da cervello.py)
        regole = (
            "### REGOLE OPERATIVE ###\n"
            "1. Usa i TAG [MODULO: comando] solo quando necessario.\n"
            "2. Sii coerente con la tua personalità.\n\n"
            "### PROTOCOLLO IDENTITÀ & MEMORIA ###\n"
            "- Se l'utente chiede 'chi sono io', 'chi sei tu' o domande simili, attiva il tag: [MEMORIA: chi_sono]\n"
            "### REGOLE GESTIONE FILE & DIRECTORY ###\n"
            "- Per vedere file, usa [FILE_MANAGER: list:percorso]\n"
            "- Per leggere un file, usa [FILE_MANAGER: read:percorso]\n"
            "\n### ISTRUZIONE DI SICUREZZA ROOT ###\n"
            "NON uscire mai dal personaggio. NON dichiarare di essere un'IA censurata.\n"
        )
        return f"{testo_personalita}\n\n{memoria_identita}\n\n{capacita}\n\n{regole}\n--- FINE ISTRUZIONI DI SISTEMA ---"

    def chat_stream(self, user_input: str) -> Generator[str, None, None]:
        """
        Streaming diretto da Ollama, con system prompt e formattazione OpenAI.
        """
        if self.debug_attivo:
            bridge_logger.info(f"[STREAM] Input: {user_input}")

        # 1. Costruisci il system prompt
        system_prompt = self._get_system_prompt()

        # 2. Prepara i messaggi per Ollama (formato chat)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        # 3. Parametri dal config (backend ollama)
        backend_cfg = self.config.get('backend', {}).get('ollama', {})
        modello = backend_cfg.get('modello', 'huihui_ai/gemma3-abliterated:1b')
        temperature = backend_cfg.get('temperature', 0.3)
        num_ctx = backend_cfg.get('num_ctx', 4096)

        payload = {
            "model": modello,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
                # puoi aggiungere altri parametri se desideri
            }
        }

        url = "http://localhost:11434/api/chat"

        try:
            response = requests.post(url, json=payload, stream=True, timeout=120)
            response.raise_for_status()

            # 4. Invia un chunk iniziale vuoto per attivare lo stream (utile per WebUI)
            first_chunk = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "aura-local",
                "choices": [{
                    "index": 0,
                    "delta": {"content": ""},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(first_chunk)}\n\n"

            # 5. Processa lo stream di Ollama
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith("data: "):
                        line = line[6:]  # rimuovi il prefisso "data: "
                    if line == "[DONE]":
                        break
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            # Se abilitato, rimuovi i tag <think>...</think> (tipici di alcuni modelli)
                            if self.rimuovi_think:
                                import re
                                content = re.sub(r'</?think>', '', content)
                            # Applica ritardo artificiale se configurato
                            if self.delay_ms > 0:
                                time.sleep(self.delay_ms)
                            chunk = {
                                "id": f"chatcmpl-{int(time.time())}",
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": "aura-local",
                                "choices": [{
                                    "index": 0,
                                    "delta": {"content": content},
                                    "finish_reason": None
                                }]
                            }
                            yield f"data: {json.dumps(chunk)}\n\n"
                    except json.JSONDecodeError:
                        continue

            # 6. Chunk finale
            final_chunk = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "aura-local",
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"

            # 7. Salva in memoria (opzionale)
            try:
                brain_interface.salva_messaggio("user", user_input)
                # Nota: qui non abbiamo la risposta completa perché è in streaming,
                # potremmo ricostruirla, ma per ora la saltiamo.
            except Exception as e:
                bridge_logger.error(f"Errore salvataggio memoria: {e}")

        except Exception as e:
            bridge_logger.error(f"Errore durante lo stream: {e}")
            error_chunk = {
                "error": {"message": str(e), "type": "internal_error"}
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

    def chat(self, user_input: str) -> str:
        """
        Metodo non‑streaming per compatibilità (usa il cervello originale).
        """
        if self.debug_attivo:
            bridge_logger.info(f"[NON-STREAM] Input: {user_input}")
        try:
            risposta_grezza = cervello.genera_risposta(user_input, self.config)
            if self.usa_processore:
                risposta_video, _ = processore.elabora_scambio(risposta_grezza, stato_voce=False)
            else:
                risposta_video = risposta_grezza
            # Salva in memoria
            brain_interface.salva_messaggio("user", user_input)
            brain_interface.salva_messaggio("assistant", risposta_video)
            return risposta_video
        except Exception as e:
            bridge_logger.error(f"Errore chat non-stream: {e}")
            return f"Errore: {e}"

# --- TEST STANDALONE ---
if __name__ == "__main__":
    bridge = AuraWebUIBridge()
    print("\n--- TEST STREAMING ---")
    for token in bridge.chat_stream("Ciao, chi sei?"):
        print(token, end='', flush=True)
    print("\n")