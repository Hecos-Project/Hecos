"""
Hecos Web UI - Audio Settings, Filters and Cache Routes
Endpoints for audio configuration, active TTS presets, regex filters, available voices, and audio cache management.
"""

from flask import request, jsonify


def register_audio_settings_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    """Registers audio settings, filters, voices and cache stats endpoints."""
    def _sm():
        return get_sm() if callable(get_sm) else get_sm

    @app.route("/api/audio/config", methods=["GET", "POST"])
    def manage_audio_config():
        """Gets or updates advanced audio settings in config_audio.json."""
        from hecos.core.audio.device_manager import get_audio_config, _save_audio_config

        if request.method == "GET":
            try:
                return jsonify({"ok": True, "config": get_audio_config()})
            except Exception as exc:
                return jsonify({"ok": False, "error": str(exc)}), 500

        if request.method == "POST":
            try:
                data = request.get_json(force=True) or {}
                cfg = get_audio_config()
                prev_active = cfg.get("active_engine", "piper")
                prev_piper_auto = bool(cfg.get("piper_autostart", True))
                allow_empty_presets = bool(data.get("_allow_empty_presets"))
                preset_dict_keys = {
                    "kokoro_presets", "kokoro_inference_presets",
                    "xtts_presets", "xtts_inference_presets",
                    "fish_speech_presets", "fish_speech_inference_presets",
                    "piper_presets", "piper_inference_presets"
                }
                for k in [
                    "active_engine", "kokoro", "kokoro_presets", "kokoro_inference_presets",
                    "xtts", "xtts_presets", "xtts_inference_presets", "fish_speech",
                    "fish_speech_presets", "fish_speech_inference_presets", "voice_status",
                    "listening_status", "piper_autostart", "piper_path", "onnx_model", "speed", "noise_scale",
                    "noise_w", "sentence_silence", "volume", "piper_timeout", "energy_threshold",
                    "silence_timeout", "phrase_limit", "tts_history_max_files", "push_to_talk",
                    "ptt_hotkey", "ptt_sources", "custom_ptt_key",
                    "piper_current_preset", "piper_presets", "piper_current_inference_preset", "piper_inference_presets"
                ]:
                    if k in data:
                        if (k in preset_dict_keys and isinstance(data[k], dict) and
                                len(data[k]) == 0 and len(cfg.get(k) or {}) > 0 and not allow_empty_presets):
                            logger.warning(f"[WebUI] Prevented accidental empty overwrite of '{k}' in audio.yaml.")
                            continue
                        cfg[k] = data[k]

                _save_audio_config(cfg)

                # Coordinate TTS runtime lifecycle on engine switch or autostart toggle
                try:
                    from hecos.core.audio.tts_manager import handle_active_engine_switch, get_piper
                    new_active = cfg.get("active_engine", "piper")
                    if new_active != prev_active:
                        handle_active_engine_switch(prev_active, new_active, cfg)
                    if not prev_piper_auto and bool(cfg.get("piper_autostart", True)):
                        get_piper().preload(delay=0.1, blocking=False)
                except Exception as _tle:
                    logger.warning(f"[WebUI] TTS lifecycle sync on config save notice: {_tle}")

                # Sync with running StateManager
                sm = _sm()
                if sm:
                    if "listening_status" in data:
                        sm.listening_status = data["listening_status"]
                    if "voice_status" in data:
                        sm.voice_status = data["voice_status"]
                    if "push_to_talk" in data:
                        sm.push_to_talk = data["push_to_talk"]

                try:
                    from hecos.core.audio import ptt_bus
                    ptt_bus.update_cache()
                except Exception:
                    pass

                # If voice capabilities changed, we must update the processor
                if any(k in data for k in ["voice_status", "listening_status"]):
                    try:
                        from hecos.core.processing import processore
                        processore.configure(cfg_mgr.config)
                    except Exception:
                        pass

                return jsonify({"ok": True})
            except Exception as exc:
                logger.error(f"[WebUI] manage_audio_config POST error: {exc}")
                return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/filters", methods=["GET", "POST"])
    def manage_tts_filters():
        """Gets or updates TTS filters config."""
        try:
            from hecos.core.audio.tts_filter.config import get_filter_config, save_filter_config
            if request.method == "GET":
                return jsonify({"ok": True, "config": get_filter_config()})
            elif request.method == "POST":
                data = request.get_json(force=True) or {}
                if save_filter_config(data):
                    return jsonify({"ok": True})
                else:
                    return jsonify({"ok": False, "error": "Failed to save filters"}), 500
        except Exception as exc:
            logger.error(f"[WebUI] manage_tts_filters error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route('/api/audio/voices', methods=['GET'])
    def get_audio_voices():
        """Returns available voices for all or a specific TTS engine."""
        engine = request.args.get('engine', 'all')
        try:
            from hecos.core.audio.tts_manager import TTSManager
            if engine == 'all':
                return jsonify({
                    "piper": TTSManager.get_available_voices("piper"),
                    "kokoro": TTSManager.get_available_voices("kokoro"),
                    "xtts2": TTSManager.get_available_voices("xtts2"),
                    "fish_speech": TTSManager.get_available_voices("fish_speech")
                })
            else:
                return jsonify(TTSManager.get_available_voices(engine))
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/audio/cache/stats', methods=['GET'])
    def tts_cache_stats():
        """Returns statistics of the TTS persistent audio cache."""
        try:
            from hecos.core.audio.tts_cache import TTSCache
            stats = TTSCache.get_instance().get_stats()
            return jsonify({"ok": True, "stats": stats})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route('/api/audio/cache/clear', methods=['POST'])
    def tts_cache_clear():
        """Clears all cached TTS audio files."""
        try:
            from hecos.core.audio.tts_cache import TTSCache
            deleted = TTSCache.get_instance().clear()
            logger.info(f"[WebUI] User cleared TTS cache ({deleted} files deleted).")
            return jsonify({"ok": True, "deleted_count": deleted})
        except Exception as exc:
            logger.error(f"[WebUI] tts_cache_clear error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

