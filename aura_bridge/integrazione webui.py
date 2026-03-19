import sys
import os
import json
import time
from typing import Generator, Union

class Pipe:
    def __init__(self):
        self.aura_path = r"C:\AuraCoAuraCore_V0.9.3"
        if self.aura_path not in sys.path:
            sys.path.insert(0, self.aura_path)
        self.bridge = None
        self.debug_mode = True  # Metti a False in produzione

    def _log(self, msg):
        if self.debug_mode:
            print(f"[AURA PIPE] {msg}")

    def pipe(self, body: dict) -> Union[str, Generator]:
        messages = body.get("messages", [])
        if not messages:
            return ""

        last_message = messages[-1].get("content", "")

        # Filtro task automatici di WebUI
        if any(x in last_message for x in ["### Task:", "### Guidelines:"]):
            return ""

        if self.bridge is None:
            try:
                os.chdir(self.aura_path)
                from aura_webui_bridge import AuraWebUIBridge
                self.bridge = AuraWebUIBridge()
                self._log("Bridge inizializzato correttamente.")
            except Exception as e:
                self._log(f"FALLIMENTO INIZIALIZZAZIONE: {str(e)}")
                return f"Errore caricamento Aura: {str(e)}"

        # Determina se la richiesta è in streaming
        is_stream = body.get("stream", False)

        if is_stream:
            return self._stream_handler(last_message)
        else:
            # Risposta completa (non streaming)
            risposta = self.bridge.chat(last_message)
            # Formato OpenAI compatibile
            result = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "aura-local",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": risposta
                    },
                    "finish_reason": "stop"
                }]
            }
            return json.dumps(result)

    def _stream_handler(self, message: str) -> Generator:
        self._log(f"Inizio ricezione stream...")
        # Il bridge produce già eventi SSE formattati, li inoltriamo direttamente
        for event in self.bridge.chat_stream(message):
            yield event