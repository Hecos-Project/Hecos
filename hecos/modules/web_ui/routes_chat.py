"""
routes_chat.py
────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Chat Routes Orchestrator

Delegates to focused sub-modules:
  routes_chat_tts.py        → Piper TTS engine (generate, stop, path)
  routes_chat_inference.py  → _run_inference, shared _sessions dict
  routes_chat_api.py        → /chat, /api/chat, /api/stream, /api/history, /api/audio
  routes_chat_media.py      → /api/upload, /api/images, /static/*, /snapshots/*

Public symbols re-exported for backwards-compat with any external callers:
  set_last_audio_path()
  generate_voice_file()
  stop_voice_generation()
────────────────────────────────────────────────────────────────────────────
"""
# Re-export TTS helpers so any external callers (e.g. server.py) still work
from hecos.modules.web_ui.routes_chat_tts import (
    set_last_audio_path,
    generate_voice_file,
    stop_voice_generation,
)


def init_chat_routes(app, cfg_mgr, root_dir: str, logger):
    from hecos.modules.web_ui.routes_chat_api   import init_chat_api_routes
    from hecos.modules.web_ui.routes_chat_media import init_chat_media_routes

    init_chat_api_routes  (app, cfg_mgr, logger)
    init_chat_media_routes(app, logger)
