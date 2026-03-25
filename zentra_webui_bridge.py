"""
FILE: zentra_webui_bridge.py
VERSIONE: 2.2 (Voice Bridge Edition)
AUTORE: Progetto ZENTRA
"""

import sys
import os
import time
import json
import logging
import requests
import subprocess
import threading
from typing import Generator

BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BRIDGE_DIR)
if BRIDGE_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_DIR)

# Caricamento Variabili d'Ambiente (.env) nel processo WebUI
try:
    from dotenv import load_dotenv
    env_path = os.path.join(BRIDGE_DIR, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass

# Import dei moduli core di Zentra
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

# --- LOGGER DEL BRIDGE ---
bridge_logger = logging.getLogger("WebUI_Bridge")
bridge_logger.setLevel(logging.DEBUG)
os.makedirs(os.path.join(BRIDGE_DIR, "logs"), exist_ok=True)
fh = logging.FileHandler(os.path.join(BRIDGE_DIR, "logs", "bridge_debug.log"), encoding='utf-8')
fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
bridge_logger.addHandler(fh)


class ZentraWebUIBridge:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config

        # Valvole dal config
        self.bridge_cfg = self.config.get("bridge", {})
        self.usa_processore = self.bridge_cfg.get("usa_processore", False)
        self.delay_ms = self.bridge_cfg.get("ritardo_chunk_ms", 0) / 1000.0
        self.debug_attivo = self.bridge_cfg.get("debug_log", True)
        self.rimuovi_think = self.bridge_cfg.get("rimuovi_think_tags", True)

        # --- VOICE ---
        self.voce_locale = self.bridge_cfg.get("voce_locale_abilitata", False)
        self.voce_cfg = self.config.get("voce", {})

        if self.debug_attivo:
            bridge_logger.info("=" * 40)
            bridge_logger.info("BRIDGE INITIALIZATION COMPLETED")
            bridge_logger.info(
                f"Valves: Processor={self.usa_processore}, Delay={self.delay_ms}s, "
                f"Remove think={self.rimuovi_think}, Local TTS={self.voce_locale}"
            )

        try:
            brain_interface.inizializza_caveau()
        except Exception as e:
            bridge_logger.error(f"Core initialization error: {e}")

    # ------------------------------------------------------------------
    # TTS LOCALE — bridge-safe, non-bloccante, NO keyboard/msvcrt
    # ------------------------------------------------------------------
    def _parla_locale(self, testo: str):
        """Chiama Piper in un thread daemon. Non blocca lo stream HTTP."""
        if not testo or not self.voce_locale:
            return
        testo = testo.strip()
        if not testo:
            return

        def _run():
            try:
                piper_path = self.voce_cfg.get("piper_path", r"C:\piper\piper.exe")
                model_path = self.voce_cfg.get("modello_onnx", r"C:\piper\it_IT-paola-medium.onnx")
                speed        = self.voce_cfg.get("speed", 1.2)
                length_scale = round(1.0 / max(0.1, speed), 3)
                noise_scale  = self.voce_cfg.get("noise_scale", 0.817)
                noise_w      = self.voce_cfg.get("noise_w", 0.9)
                silence      = self.voce_cfg.get("sentence_silence", 0.1)

                testo_pulito = testo.replace('"', '').replace('\n', ' ')
                wav_path = os.path.join(BRIDGE_DIR, "risposta_bridge.wav")

                cmd = [
                    piper_path, "-m", model_path,
                    "--length_scale", str(length_scale),
                    "--noise_scale",  str(noise_scale),
                    "--noise_w",      str(noise_w),
                    "--sentence_silence", str(silence),
                    "-f", wav_path
                ]
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    text=True
                )
                proc.communicate(input=testo_pulito)

                if os.path.exists(wav_path):
                    import winsound
                    winsound.PlaySound(wav_path, winsound.SND_FILENAME)
                    if self.debug_attivo:
                        bridge_logger.info(f"[TTS] Spoken locally: {len(testo_pulito)} chars")
            except Exception as e:
                bridge_logger.error(f"[TTS] Local voice error: {e}")

        threading.Thread(target=_run, daemon=True).start()

    # ------------------------------------------------------------------
    # SYSTEM PROMPT
    # ------------------------------------------------------------------
    def _get_system_prompt(self):
        personalita_file = self.config.get('ia', {}).get('personalita_attiva', 'zentra.txt')
        path_p = os.path.join(BRIDGE_DIR, "personality", personalita_file)
        testo_personalita = ""
        if os.path.exists(path_p):
            with open(path_p, "r", encoding="utf-8") as f:
                testo_personalita = f.read()

        memoria_identita = brain_interface.ottieni_contesto_memoria()
        capacita = brain.carica_capacita()

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

    # ------------------------------------------------------------------
    def chat_stream(self, user_input: str) -> Generator[str, None, None]:
        # Ricarica la configurazione per applicare i cambiamenti fatti dall'utente (es. cambio modello)
        self.config = self.config_manager.reload()

        if self.debug_attivo:
            bridge_logger.info(f"[STREAM] Input: {user_input}")

        system_prompt = self._get_system_prompt()

        try:
            from core.llm.manager import manager
            from core.llm import client
        except ImportError as e:
            bridge_logger.error(f"Cannot import LLM core modules: {e}")
            yield f"data: {json.dumps({'error': {'message': 'Core import error', 'type': 'internal_error'}})}\n\n"
            return

        backend_type = self.config.get('backend', {}).get('tipo', 'ollama')
        backend_cfg  = self.config.get('backend', {}).get(backend_type, {}).copy()

        modello = manager.resolve_model()
        if modello:
            backend_cfg['modello'] = modello
        backend_cfg['tipo_backend'] = backend_type

        if self.debug_attivo:
            bridge_logger.info(f"[STREAM] Backend={backend_type} Model={backend_cfg.get('modello')}")

        try:
            # Chunk iniziale per risvegliare WebUI
            yield f"data: {json.dumps({'id': f'chatcmpl-{int(time.time())}', 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'zentra-local', 'choices': [{'index': 0, 'delta': {'content': ''}, 'finish_reason': None}]})}\n\n"

            stream_generator = client.generate(
                system_prompt=system_prompt,
                user_message=user_input,
                config_or_subconfig=backend_cfg,
                llm_config=self.config.get('llm', {}),
                tools=None,
                stream=True
            )

            if not stream_generator or isinstance(stream_generator, str):
                err = stream_generator if isinstance(stream_generator, str) else "Unknown error from client"
                bridge_logger.error(f"Stream generation failed: {err}")
                yield f"data: {json.dumps({'error': {'message': err, 'type': 'api_error'}})}\n\n"
                return

            testo_completo = ""
            for chunk in stream_generator:
                try:
                    if hasattr(chunk, 'choices') and chunk.choices:
                        content = getattr(chunk.choices[0].delta, "content", "") or ""
                    else:
                        continue

                    if content:
                        if self.rimuovi_think:
                            import re
                            content = re.sub(r'</?think>', '', content)
                        if self.delay_ms > 0:
                            time.sleep(self.delay_ms)
                        testo_completo += content
                        out = {
                            "id": f"chatcmpl-{int(time.time())}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": "zentra-local",
                            "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}]
                        }
                        yield f"data: {json.dumps(out)}\n\n"
                except Exception as e:
                    bridge_logger.error(f"[STREAM] Chunk error: {e}")
                    continue

            # Chunk finale
            yield f"data: {json.dumps({'id': f'chatcmpl-{int(time.time())}', 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'zentra-local', 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
            yield "data: [DONE]\n\n"

            # Memoria + TTS locale (in background, non blocca)
            try:
                brain_interface.salva_messaggio("user", user_input)
                if testo_completo.strip():
                    brain_interface.salva_messaggio("assistant", testo_completo)
                    self._parla_locale(testo_completo)
                if self.debug_attivo:
                    bridge_logger.info(
                        f"[STREAM] DONE. Chars={len(testo_completo)} "
                        f"LocalTTS={'ON' if self.voce_locale else 'OFF'}"
                    )
            except Exception as e:
                bridge_logger.error(f"Memory/TTS error: {e}")

        except Exception as e:
            bridge_logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'error': {'message': str(e), 'type': 'internal_error'}})}\n\n"

    # ------------------------------------------------------------------
    # NON-STREAMING
    # ------------------------------------------------------------------
    def chat(self, user_input: str) -> str:
        # Ricarica la configurazione
        self.config = self.config_manager.reload()

        if self.debug_attivo:
            bridge_logger.info(f"[NON-STREAM] Input: {user_input}")
        try:
            risposta_grezza = brain.genera_risposta(user_input, self.config)
            if self.usa_processore:
                risposta_video, _ = processore.elabora_scambio(risposta_grezza, stato_voce=False)
            else:
                risposta_video = risposta_grezza
            brain_interface.salva_messaggio("user", user_input)
            brain_interface.salva_messaggio("assistant", risposta_video)
            self._parla_locale(risposta_video)
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