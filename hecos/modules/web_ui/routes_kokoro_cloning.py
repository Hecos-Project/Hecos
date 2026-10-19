"""
hecos/modules/web_ui/routes_kokoro_cloning.py
Dedicated routes for Kokoro Voice Cloning and style pack management.
Completely isolated from routes_audio_config.py for maximum modularity.
"""

import os
import uuid
from flask import request, jsonify


def init_kokoro_cloning_routes(app, cfg_mgr, root_dir, logger):
    from hecos.core.audio.tts.kokoro.voice_manager import KokoroVoiceManager
    from hecos.modules.web_ui.routes_chat_tts import HISTORY_DIR

    @app.route('/api/audio/kokoro/clones/sources', methods=['GET'])
    def kokoro_clones_sources():
        """Lists available reference WAV audio tracks from assets/voice_clones."""
        try:
            sources = KokoroVoiceManager.list_sources()
            return jsonify({"ok": True, "sources": sources})
        except Exception as exc:
            logger.error(f"[KokoroCloner] Error listing sources: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route('/api/audio/kokoro/clones/installed', methods=['GET'])
    def kokoro_clones_installed():
        """Lists currently converted and installed custom Kokoro voice packs (.pt)."""
        try:
            voices = KokoroVoiceManager.list_custom_voices()
            return jsonify({"ok": True, "voices": voices})
        except Exception as exc:
            logger.error(f"[KokoroCloner] Error listing installed voices: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route('/api/audio/kokoro/clones/convert', methods=['POST'])
    def kokoro_clones_convert():
        """
        Converts a source WAV audio into a Kokoro style pack (.pt)
        and registers it in hecos/models/kokoro/voices.
        """
        try:
            data = request.get_json(force=True) or {}
            wav_filename = (data.get("wav_filename") or "").strip()
            custom_name = (data.get("custom_name") or "").strip()
            lang_prefix = (data.get("lang_prefix") or "af").strip()
            display_title = (data.get("display_title") or "").strip()
            prosody_mode = (data.get("prosody_mode") or "auto").strip()

            if not wav_filename:
                return jsonify({"ok": False, "error": "wav_filename is required"}), 400
            if not custom_name:
                return jsonify({"ok": False, "error": "custom_name is required"}), 400

            logger.info(f"[KokoroCloner] Starting enrollment for '{wav_filename}' -> '{custom_name}' ({lang_prefix}, prosody={prosody_mode})...")
            result = KokoroVoiceManager.create_clone(
                wav_filename=wav_filename,
                custom_name=custom_name,
                lang_prefix=lang_prefix,
                display_title=display_title,
                prosody_mode=prosody_mode
            )
            return jsonify(result)
        except Exception as exc:
            logger.error(f"[KokoroCloner] Conversion error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route('/api/audio/kokoro/clones/delete', methods=['POST'])
    def kokoro_clones_delete():
        """Deletes a custom Kokoro voice pack (.pt and .json)."""
        try:
            data = request.get_json(force=True) or {}
            voice_id = (data.get("voice_id") or "").strip()
            if not voice_id:
                return jsonify({"ok": False, "error": "voice_id is required"}), 400

            deleted = KokoroVoiceManager.delete_clone(voice_id)
            if deleted:
                logger.info(f"[KokoroCloner] Deleted custom voice '{voice_id}'")
                return jsonify({"ok": True, "deleted": True})
            else:
                return jsonify({"ok": False, "error": f"Voice '{voice_id}' not found"}), 404
        except Exception as exc:
            logger.error(f"[KokoroCloner] Deletion error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route('/api/audio/kokoro/clones/preview', methods=['POST'])
    def kokoro_clones_preview():
        """Generates a fast speech sample with the given Kokoro custom voice."""
        try:
            data = request.get_json(force=True) or {}
            voice_id = (data.get("voice_id") or "").strip()
            text = (data.get("text") or "Hello! This is a voice test with the custom Kokoro cloned voice.").strip()

            if not voice_id:
                return jsonify({"ok": False, "error": "voice_id is required"}), 400

            from hecos.core.audio.tts.kokoro_engine import KokoroEngine
            audio_id = uuid.uuid4().hex
            out_file = os.path.join(HISTORY_DIR, f"{audio_id}.wav")
            os.makedirs(HISTORY_DIR, exist_ok=True)

            logger.info(f"[KokoroCloner] Generating preview for voice '{voice_id}' -> {out_file}")
            engine = KokoroEngine()
            ok = engine.generate_wav(text, out_file, voice=voice_id)

            if ok and os.path.exists(out_file) and os.path.getsize(out_file) > 0:
                return jsonify({
                    "ok": True,
                    "audio_id": audio_id,
                    "url": f"/api/audio?id={audio_id}"
                })
            else:
                return jsonify({"ok": False, "error": "Audio preview synthesis failed"}), 500
        except Exception as exc:
            logger.error(f"[KokoroCloner] Preview error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route('/api/audio/kokoro/clones/open-folder', methods=['POST'])
    def kokoro_clones_open_folder():
        """Opens assets/voice_clones or models/kokoro/voices in Windows Explorer."""
        try:
            data = request.get_json(silent=True) or {}
            target = data.get("target", "sources")
            if target == "voices":
                folder = KokoroVoiceManager.get_voices_dir()
            else:
                folder = KokoroVoiceManager.get_source_audio_dir()
            os.makedirs(folder, exist_ok=True)
            if hasattr(os, "startfile"):
                os.startfile(folder)
            return jsonify({"ok": True, "path": folder})
        except Exception as exc:
            logger.error(f"[KokoroCloner] Error opening folder: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

