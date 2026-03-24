"""
FILE: zentra_webui_bridge.py
VERSIONE: 2.1 (Valvole & Debug Edition - FIXED)
AUTORE: Progetto ZENTRA
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

# Import dei moduli core di Zentra (necessari per system prompt e memoria)
try:
    from core.llm import brain
    from core.processing import processore
    from core.logging import logger as core_logger
    from memory import brain_interface
    from app.config import ConfigManager
    from core.i18n import translator
except ImportError as e:
    print(f"[ERROR] {e}")
    sys.exit(1)

# --- SETUP LOGGER DEL BRIDGE (su file separato) ---
bridge_logger = logging.getLogger("WebUI_Bridge")
bridge_logger.setLevel(logging.DEBUG)
# Assicura che la cartella logs esista
os.makedirs(os.path.join(BRIDGE_DIR, "logs"), exist_ok=True)
fh = logging.FileHandler(os.path.join(BRIDGE_DIR, "logs", "bridge_debug.log"), encoding='utf-8')
fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
bridge_logger.addHandler(fh)

class ZentraWebUIBridge:
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
            bridge_logger.info("BRIDGE INITIALIZATION COMPLETED")
            bridge_logger.info(f"Valves: Processor={self.usa_processore}, Delay={self.delay_ms}s, Remove think={self.rimuovi_think}")

        # Inizializza il core (memory, plugin) – necessario per il system prompt
        try:
            brain_interface.inizializza_caveau()
            # Non serve ricaricare i plugin a ogni chiamata, ma per sicurezza:
            # plugin_loader.aggiorna_registro_capacita()  # se vuoi, altrimenti lascia
        except Exception as e:
            bridge_logger.error(f"Core initialization error: {e}")

    def _get_system_prompt(self):
        """Costruisce il system prompt come nel cervello originale."""
        personalita_file = self.config.get('ia', {}).get('personalita_attiva', 'zentra.txt')
        path_p = os.path.join(BRIDGE_DIR, "personality", personalita_file)
        testo_personalita = ""
        if os.path.exists(path_p):
            with open(path_p, "r", encoding="utf-8") as f:
                testo_personalita = f.read()

        memoria_identita = brain_interface.ottieni_contesto_memoria()
        capacita = brain.carica_capacita()

        # Aggiungi regole di base (copiate da brain.py)
        regole = (
            f"{translator.t('identity_protocol')}\n"
            f"- {translator.t('rule_who_am_i')}\n"
            f"{translator.t('file_management_rules')}\n"
            f"- {translator.t('rule_list_files')}\n"
            f"- {translator.t('rule_read_file')}\n"
            f"\n{translator.t('root_security_instruction')}\n"
            f"{translator.t('root_security_desc')}\n"
        )
        return f"{testo_personalita}\n\n{memoria_identita}\n\n{capacita}\n\n{regole}\n--- END OF SYSTEM INSTRUCTIONS ---"

    def chat_stream(self, user_input: str) -> Generator[str, None, None]:
        """
        Streaming usando il client unificato di Zentra (LiteLLM),
        compatibile con Cloud e Locale.
        """
        if self.debug_attivo:
            bridge_logger.info(f"[STREAM] Input: {user_input}")

        # 1. Sistema e Modello
        system_prompt = self._get_system_prompt()
        
        try:
            from core.llm.manager import manager
            from core.llm import client
        except ImportError as e:
            bridge_logger.error(f"Cannot import LLM core modules: {e}")
            yield f"data: {json.dumps({'error': {'message': 'Core import error', 'type': 'internal_error'}})}\n\n"
            return
            
        backend_type = self.config.get('backend', {}).get('tipo', 'ollama')
        backend_cfg = self.config.get('backend', {}).get(backend_type, {}).copy()
        
        # Risolvi dinamicamente il modello di default
        modello = manager.resolve_model()
        if modello:
            backend_cfg['modello'] = modello
        backend_cfg['tipo_backend'] = backend_type
        
        if self.debug_attivo:
            bridge_logger.info(f"[STREAM] Using backend {backend_type} with model {backend_cfg.get('modello')}")

        try:
            # 2. Invia chunk iniziale (per risvegliare la WebUI)
            first_chunk = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "zentra-local",
                "choices": [{"index": 0, "delta": {"content": ""}, "finish_reason": None}]
            }
            yield f"data: {json.dumps(first_chunk)}\n\n"

            # 3. Chiama il client in modalità stream
            stream_generator = client.generate(
                system_prompt=system_prompt,
                user_message=user_input,
                config_or_subconfig=backend_cfg,
                llm_config=self.config.get('llm', {}),
                tools=None, # Function calling disattivato nello stream WebUI per ora
                stream=True
            )

            # 4. Processa i chunk da LiteLLM
            testo_completo = ""
            if not stream_generator or isinstance(stream_generator, str):
                # Caso di errore fallback dal client
                err = stream_generator if isinstance(stream_generator, str) else "Unknown error from client"
                bridge_logger.error(f"Stream generation failed: {err}")
                yield f"data: {json.dumps({'error': {'message': err, 'type': 'api_error'}})}\n\n"
                return

            for chunk in stream_generator:
                try:
                    # LiteLLM compatibilità Pydantic o dict
                    if hasattr(chunk, 'choices') and chunk.choices:
                        delta = chunk.choices[0].delta
                        content = getattr(delta, "content", "") or ""
                    else:
                        continue
                        
                    if content:
                        if self.rimuovi_think:
                            import re
                            content = re.sub(r'</?think>', '', content)
                            
                        if self.delay_ms > 0:
                            time.sleep(self.delay_ms)
                            
                        testo_completo += content
                        
                        out_chunk = {
                            "id": f"chatcmpl-{int(time.time())}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": "zentra-local",
                            "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}]
                        }
                        yield f"data: {json.dumps(out_chunk)}\n\n"
                except Exception as e:
                    bridge_logger.error(f"[STREAM] Chunk processing error: {e}")
                    continue

            # 5. Chunk finale chiusura
            final_chunk = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "zentra-local",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"

            # 6. Salva memoria post-streaming
            try:
                brain_interface.salva_messaggio("user", user_input)
                if testo_completo.strip():
                    brain_interface.salva_messaggio("assistant", testo_completo)
                if self.debug_attivo:
                    bridge_logger.info(f"[STREAM] DONE. Memory saved: {len(testo_completo)} chars.")
            except Exception as e:
                bridge_logger.error(f"Memory save error: {e}")

        except Exception as e:
            bridge_logger.error(f"Stream error: {e}")
            error_chunk = {"error": {"message": str(e), "type": "internal_error"}}
            yield f"data: {json.dumps(error_chunk)}\n\n"

    def chat(self, user_input: str) -> str:
        """
        Metodo non‑streaming per compatibilità (usa il cervello originale).
        """
        if self.debug_attivo:
            bridge_logger.info(f"[NON-STREAM] Input: {user_input}")
        try:
            risposta_grezza = brain.genera_risposta(user_input, self.config)
            if self.usa_processore:
                risposta_video, _ = processore.elabora_scambio(risposta_grezza, stato_voce=False)
            else:
                risposta_video = risposta_grezza
            # Salva in memoria
            brain_interface.salva_messaggio("user", user_input)
            brain_interface.salva_messaggio("assistant", risposta_video)
            return risposta_video
        except Exception as e:
            bridge_logger.error(f"Error: {e}")
            return f"{translator.t('error')}: {e}"

# --- TEST STANDALONE ---
if __name__ == "__main__":
    bridge = ZentraWebUIBridge()
    print("\n--- TEST STREAMING ---")
    for token in bridge.chat_stream("Ciao, chi sei?"):
        print(token, end='', flush=True)
    print("\n")