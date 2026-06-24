"""
voice_visualizer/main.py
─────────────────────────────────────────────────────────────────
Hecos Widget — Voice Visualizer
Exposes a lightweight polling endpoint that reports whether
Hecos is currently speaking.  Completely TTS-agnostic: it reads
state.system_speaking which is set by any TTS backend (Piper,
ElevenLabs, OpenAI TTS, etc.)
─────────────────────────────────────────────────────────────────
"""
import os
from flask import jsonify, send_from_directory


def init_routes(app):
    _static_dir = os.path.join(os.path.dirname(__file__), "static")

    @app.route("/ext/voice_visualizer/<path:filename>")
    def voice_visualizer_static(filename):
        return send_from_directory(_static_dir, filename)

    @app.route("/api/widgets/voice_visualizer/status", methods=["GET"])
    def voice_visualizer_status():
        """
        Returns whether the system is currently speaking.
        TTS-agnostic: reads StateManager.system_speaking.
        Also checks voice.is_speaking as a fallback.
        No auth required intentionally — it's a lightweight polling target
        called from inside an authenticated iframe.
        """
        speaking = False

        # Primary: StateManager (shared across all TTS backends)
        try:
            from hecos.modules.web_ui.server import get_state_manager
            sm = get_state_manager()
            if sm is not None:
                speaking = bool(sm.system_speaking)
        except Exception:
            pass

        # Fallback: voice module flag
        if not speaking:
            try:
                from hecos.core.audio import voice
                speaking = bool(getattr(voice, "is_speaking", False))
            except Exception:
                pass

        return jsonify({"speaking": speaking})
