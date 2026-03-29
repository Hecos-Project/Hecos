# This code should be pasted as a function in Open WebUI

import sys
import os
import json
import time
from typing import Generator, Union
from pydantic import BaseModel, Field

class Pipe:
    class Valves(BaseModel):
        config_port: int = Field(
            default=7070,
            description="The port on which to start the integrated web configuration panel."
        )

    def __init__(self):
        self.zentra_path = r"C:\Zentra-Core"
        if self.zentra_path not in sys.path:
            sys.path.insert(0, self.zentra_path)
        self.bridge = None
        self.debug_mode = True  # Set to False in production
        self.valves = self.Valves()
        self._welcome_sent = False

    def _log(self, msg):
        if self.debug_mode:
            print(f"[ZENTRA PIPE] {msg}")

    def pipe(self, body: dict) -> Union[str, Generator]:
        messages = body.get("messages", [])
        if not messages:
            return ""

        last_message = messages[-1].get("content", "")

        # Filter automatic WebUI tasks
        if any(x in last_message for x in ["### Task:", "### Guidelines:"]):
            return ""

        if self.bridge is None:
            try:
                os.chdir(self.zentra_path)
                from zentra_bridge.webui.bridge import ZentraWebUIBridge
                # Set port before init so config server picks it up
                os.environ["ZENTRA_WEBUI_CONFIG_PORT"] = str(self.valves.config_port)
                self.bridge = ZentraWebUIBridge()
                self._log("Bridge initialized successfully.")
            except Exception as e:
                self._log(f"INITIALIZATION FAILURE: {str(e)}")
                return f"Zentra loading error: {str(e)}"

        # Inject welcome message with config panel link on the very first interaction
        welcome_prefix = ""
        if not self._welcome_sent:
            self._welcome_sent = True
            port = self.valves.config_port
            welcome_prefix = (
                f"> **Zentra Bridge Connected!** ⚡\n"
                f"> [Open Configuration Panel](http://localhost:{port}/zentra/config/ui)\n\n---\n\n"
            )

        # Determine if the request is streaming
        is_stream = body.get("stream", False)

        if is_stream:
            def stream_with_prefix():
                if welcome_prefix:
                    chunk = {
                        "id": f"chatcmpl-{int(time.time())}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": "zentra",
                        "choices": [{"index": 0, "delta": {"content": welcome_prefix}}]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                yield from self._stream_handler(last_message)
            return stream_with_prefix()
        else:
            # Full response (non-streaming)
            response = self.bridge.chat(last_message)
            final_response = welcome_prefix + response if welcome_prefix else response
            # OpenAI compatible format
            result = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "zentra-local",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": final_response
                    },
                    "finish_reason": "stop"
                }]
            }
            return json.dumps(result)

    def _stream_handler(self, message: str) -> Generator:
        self._log(f"Starting stream reception...")
        # The bridge already produces formatted SSE events, forward them directly
        for event in self.bridge.chat_stream(message):
            yield event