"""
MODULE: zentra_bridge/webui/bridge.py
DESCRIPTION: Main ZentraWebUIBridge class.  Glues together all sub-modules and
             exposes the two public methods expected by Open WebUI:
               - chat(user_input)          -> str
               - chat_stream(user_input)   -> Generator[str, None, None]
"""

import os
import sys
import logging
from typing import Generator

# --- Ensure Zentra-Core root is importable ---
BRIDGE_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
if BRIDGE_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_DIR)

# --- Load .env variables (needed when running inside Open WebUI process) ---
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(BRIDGE_DIR, ".env")
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
except ImportError:
    pass

# --- Core Zentra imports ---
try:
    from core.llm import brain
    from core.processing import processore
    from core.logging import logger as core_logger
    from memory import brain_interface
    from app.config import ConfigManager
    from core.i18n import translator
except ImportError as _e:
    raise ImportError(f"[ZentraWebUIBridge] Cannot import core Zentra modules: {_e}") from _e

# --- Sub-module imports ---
from zentra_bridge.webui.audio        import speak_local
from zentra_bridge.webui.prompting    import build_system_prompt
from zentra_bridge.webui.streaming    import stream_response
from zentra_bridge.webui.tools        import build_tool_schemas
from plugins.web_ui.server           import start_if_needed as _start_config_server

# --- Bridge logger ---
bridge_logger = logging.getLogger("WebUI_Bridge")
bridge_logger.setLevel(logging.DEBUG)
os.makedirs(os.path.join(BRIDGE_DIR, "logs"), exist_ok=True)
_fh = logging.FileHandler(
    os.path.join(BRIDGE_DIR, "logs", "bridge_debug.log"), encoding="utf-8"
)
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
if not bridge_logger.handlers:
    bridge_logger.addHandler(_fh)

# Sentinel prefix used by streaming.py to pass the full text back
_FULL_TEXT_SENTINEL = "__ZENTRA_FULL_TEXT__"


class ZentraWebUIBridge:
    """
    Orchestrates the Zentra bridge for Open WebUI.

    Config keys read from ``config.json → bridge``:
      - use_processor        (bool)  : pass response through the text processor
      - chunk_delay_ms       (int)   : artificial chunk delay in ms
      - debug_log            (bool)  : verbose bridge logging
      - remove_think_tags    (bool)  : strip <think>…</think> tags
      - local_voice_enabled  (bool)  : enable local Piper TTS
      - enable_tools         (bool)  : expose Zentra plugins as LLM tools
    """

    def __init__(self) -> None:
        os.chdir(BRIDGE_DIR)

        self.config_manager = ConfigManager()
        self.config         = self.config_manager.config
        self._refresh_valves()

        # Pre-build tool schemas (cached; rebuilt on config reload)
        self._tool_schemas = []
        if self.enable_tools:
            self._rebuild_tool_schemas()

        try:
            brain_interface.initialize_vault()
        except Exception as exc:
            bridge_logger.error(f"Memory vault init error: {exc}")

        # Start the config panel HTTP server (singleton — safe to call multiple times)
        try:
            port = int(os.environ.get("ZENTRA_WEBUI_CONFIG_PORT", "7070"))
            _start_config_server(self.config_manager, BRIDGE_DIR, port)
        except Exception as exc:
            bridge_logger.warning(f"Config panel server could not start: {exc}")

        if self.debug_active:
            bridge_logger.info("=" * 50)
            bridge_logger.info("ZENTRA WEBUI BRIDGE V3 READY")
            bridge_logger.info(
                f"Processor={self.use_processor} | Delay={self.delay_ms}s | "
                f"Think-strip={self.remove_think} | TTS={self.local_voice} | "
                f"Tools={'ON' if self.enable_tools else 'OFF'}"
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh_valves(self) -> None:
        """Reads bridge config values into instance attributes."""
        bridge_cfg = self.config.get("bridge", {})
        self.use_processor = bridge_cfg.get("use_processor",       False)
        self.delay_ms      = bridge_cfg.get("chunk_delay_ms",      0) / 1000.0
        self.debug_active  = bridge_cfg.get("debug_log",           True)
        self.remove_think  = bridge_cfg.get("remove_think_tags",   True)
        self.local_voice   = bridge_cfg.get("local_voice_enabled", False)
        self.enable_tools  = bridge_cfg.get("enable_tools",        True)
        self.voice_cfg     = self.config.get("voice", {})

    def _rebuild_tool_schemas(self) -> None:
        """Rebuilds the tool schema list from the plugin registry."""
        registry_path = os.path.join(BRIDGE_DIR, "core", "registry.json")
        self._tool_schemas = build_tool_schemas(registry_path)

    def _resolve_backend_cfg(self) -> dict:
        """Extracts and returns the active backend sub-config dict."""
        from core.llm.manager import manager
        backend_type = self.config.get("backend", {}).get("type", "ollama")
        backend_cfg  = self.config.get("backend", {}).get(backend_type, {}).copy()
        model = manager.resolve_model()
        if model:
            backend_cfg["model"] = model
        backend_cfg["backend_type"] = backend_type
        return backend_cfg

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat_stream(self, user_input: str) -> Generator[str, None, None]:
        """
        Streams the LLM reply as SSE events compatible with Open WebUI.
        Tool calls are transparently resolved and re-fed to the model.
        """
        # Reload config on every request (picks up F7 panel changes)
        self.config = self.config_manager.reload()
        self._refresh_valves()
        if self.enable_tools:
            self._rebuild_tool_schemas()

        if self.debug_active:
            bridge_logger.info(f"[STREAM] >>> {user_input[:120]}")

        system_prompt = build_system_prompt(self.config, BRIDGE_DIR)
        backend_cfg   = self._resolve_backend_cfg()

        if self.debug_active:
            bridge_logger.info(
                f"[STREAM] Backend={backend_cfg.get('backend_type')} "
                f"Model={backend_cfg.get('model')}"
            )

        testo_completo = ""

        try:
            gen = stream_response(
                system_prompt  = system_prompt,
                user_input     = user_input,
                backend_cfg    = backend_cfg,
                llm_config     = self.config.get("llm", {}),
                tool_schemas   = self._tool_schemas,
                remove_think   = self.remove_think,
                delay_ms       = self.delay_ms,
            )

            for event in gen:
                if event.startswith(_FULL_TEXT_SENTINEL):
                    # Strip the sentinel — this is the full assembled text
                    testo_completo = event[len(_FULL_TEXT_SENTINEL):]
                else:
                    yield event

        except Exception as exc:
            bridge_logger.error(f"[STREAM] Fatal error: {exc}")
            import json
            yield f"data: {json.dumps({'error': {'message': str(exc), 'type': 'internal_error'}})}\n\n"

        # Post-stream: save to memory and trigger local TTS (non-blocking)
        try:
            brain_interface.save_message("user", user_input)
            if testo_completo.strip():
                brain_interface.save_message("assistant", testo_completo)
                if self.local_voice:
                    speak_local(testo_completo, self.voice_cfg, BRIDGE_DIR)
        except Exception as exc:
            bridge_logger.error(f"[STREAM] Memory/TTS post-processing error: {exc}")

        if self.debug_active:
            bridge_logger.info(
                f"[STREAM] DONE. Chars={len(testo_completo)} "
                f"TTS={'ON' if self.local_voice else 'OFF'}"
            )

    def chat(self, user_input: str) -> str:
        """
        Non-streaming chat.  Returns the full response text.
        Non-streaming chat. Returns the full response text.
        Falls back to text-processor if ``use_processor`` is True.
        """
        self.config = self.config_manager.reload()
        self._refresh_valves()

        if self.debug_active:
            bridge_logger.info(f"[NON-STREAM] >>> {user_input[:120]}")

        try:
            raw_response = brain.generate_response(user_input, self.config)
            if self.use_processor:
                video_response, _ = processore.process_exchange(
                    raw_response, voice_status=False
                )
            else:
                video_response = raw_response

            # brain_interface.save_message already called inside process_exchange if needed, 
            # but here we do it explicitly to be sure.
            brain_interface.save_message("user",      user_input)
            brain_interface.save_message("assistant", video_response)
            if self.local_voice:
                speak_local(video_response, self.voice_cfg, BRIDGE_DIR)
            return video_response

        except Exception as exc:
            bridge_logger.error(f"[NON-STREAM] Error: {exc}")
            try:
                return f"{translator.t('error')}: {exc}"
            except Exception:
                return f"Error: {exc}"


# --- Standalone test ---
if __name__ == "__main__":
    bridge = ZentraWebUIBridge()
    print("\n--- TEST STREAMING ---")
    for token in bridge.chat_stream("Ciao, chi sei?"):
        print(token, end="", flush=True)
    print("\n")
