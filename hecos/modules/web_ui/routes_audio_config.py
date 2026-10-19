import os
import sys
from flask import request, jsonify

def init_audio_config_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    def _sm():
        return get_sm() if callable(get_sm) else get_sm

    _speaking_timer = None

    @app.route("/api/audio/speaking/start", methods=["POST"])
    def speaking_start():
        nonlocal _speaking_timer
        sm = _sm()
        if sm:
            sm.system_speaking = True
            logger.debug("[WebUI] Audio speaking started on browser, pausing system mic.")
            if _speaking_timer:
                try: _speaking_timer.cancel()
                except: pass
            def _auto_reset():
                if sm:
                    sm.system_speaking = False
                    logger.debug("[WebUI] Auto-reset system_speaking to False after safety timeout.")
            import threading
            _speaking_timer = threading.Timer(90.0, _auto_reset)
            _speaking_timer.daemon = True
            _speaking_timer.start()
        return jsonify({"ok": True})

    @app.route("/api/audio/speaking/stop", methods=["POST"])
    def speaking_stop():
        nonlocal _speaking_timer
        if _speaking_timer:
            try: _speaking_timer.cancel()
            except: pass
            _speaking_timer = None
        sm = _sm()
        if sm:
            sm.system_speaking = False
            logger.debug("[WebUI] Audio speaking stopped on browser, resuming system mic.")
        return jsonify({"ok": True})

    @app.route("/api/audio/toggle/mic", methods=["POST"])
    def toggle_mic():
        """Toggle listening_status (MIC continuous listening).
        If MIC is turned OFF, also force PTT off to prevent a silent PTT state."""
        try:
            from hecos.core.audio.device_manager import get_audio_config, _save_audio_config
            acfg = get_audio_config()
            new_mic = not acfg.get("listening_status", True)

            sm = _sm()
            if sm is not None:
                sm.listening_status = new_mic

            acfg["listening_status"] = new_mic

            # Auto-disable PTT when MIC is turned OFF
            forced_ptt_off = False
            if not new_mic and acfg.get("push_to_talk", False):
                acfg["push_to_talk"] = False
                forced_ptt_off = True
                if sm is not None:
                    sm.push_to_talk = False
                logger.info("[WebUI] PTT auto-disabled because MIC was turned OFF.")

            if _save_audio_config(acfg):
                logger.info(f"[WebUI] MIC toggled to {new_mic} and saved.")
            else:
                logger.error("[WebUI] Failed to save MIC toggle.")

            try:
                from hecos.core.audio import ptt_bus
                ptt_bus.update_cache()
            except Exception:
                pass

            try:
                from hecos.core.processing import processore
                processore.configure(cfg_mgr.config)
            except Exception:
                pass

            return jsonify({
                "ok": True,
                "listening_status": new_mic,
                "push_to_talk": acfg.get("push_to_talk", False),
                "ptt_forced_off": forced_ptt_off
            })
        except Exception as exc:
            logger.error(f"[WebUI] toggle_mic error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/toggle/tts", methods=["POST"])
    def toggle_tts():
        """Toggle voice_status — mirrors F5 on the console."""
        try:
            from hecos.core.audio.device_manager import get_audio_config, _save_audio_config
            acfg = get_audio_config()
            new_val = not acfg.get("voice_status", True)

            sm = _sm()
            if sm is not None:
                sm.voice_status = new_val

            acfg["voice_status"] = new_val
            if _save_audio_config(acfg):
                logger.info(f"[WebUI] TTS toggled to {new_val} and saved.")
            else:
                logger.error("[WebUI] Failed to save TTS toggle.")
            try:
                from hecos.core.processing import processore
                processore.configure(cfg_mgr.config)
            except Exception:
                pass
            return jsonify({"ok": True, "voice_status": new_val})
        except Exception as exc:
            logger.error(f"[WebUI] toggle_tts error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/audio/toggle/ptt", methods=["POST"])
    def toggle_ptt():
        """Toggle push_to_talk flag.
        PTT can only be ENABLED if listening_status (continuous MIC) is also ON."""
        try:
            sm = _sm()
            from hecos.core.audio.device_manager import get_audio_config, _save_audio_config
            acfg = get_audio_config()
            current_ptt = acfg.get("push_to_talk", False)
            new_val = not current_ptt

            # Guard: PTT cannot be enabled if MIC is OFF
            if new_val and not acfg.get("listening_status", True):
                return jsonify({
                    "ok": False,
                    "error": "Enable MIC (continuous listening) before activating PTT.",
                    "push_to_talk": False
                }), 400

            acfg["push_to_talk"] = new_val
            if _save_audio_config(acfg):
                logger.info(f"[WebUI] PTT toggled to {new_val} and saved.")
            else:
                logger.error("[WebUI] Failed to save PTT toggle.")
            if sm is not None:
                sm.push_to_talk = new_val
            try:
                from hecos.core.audio import ptt_bus
                ptt_bus.update_cache()
            except Exception:
                pass
            return jsonify({"ok": True, "push_to_talk": new_val})
        except Exception as exc:
            logger.error(f"[WebUI] toggle_ptt error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

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
                for k in ["active_engine", "kokoro", "xtts", "xtts_presets", "xtts_inference_presets", "fish_speech", "fish_speech_presets", "fish_speech_inference_presets", "voice_status", "listening_status",
                          "piper_path", "onnx_model", "speed", "noise_scale", "noise_w",
                          "sentence_silence", "piper_timeout", "energy_threshold",
                          "silence_timeout", "phrase_limit", "tts_history_max_files", "push_to_talk"]:
                    if k in data:
                        cfg[k] = data[k]

                _save_audio_config(cfg)

                # Auto-start Fish Speech server if active_engine changed to fish_speech
                if data.get("active_engine") in ("fish_speech", "fish"):
                    try:
                        from hecos.core.audio.tts.fish_speech_daemon import FishSpeechDaemon
                        daemon = FishSpeechDaemon.get_instance()
                        if daemon.is_local_target() and not daemon.is_healthy():
                            daemon.preload(delay=0.2)
                            logger.info("[WebUI] Active engine switched to fish_speech: triggered background auto-startup.")
                    except Exception as _fe:
                        logger.warning(f"[WebUI] Fish Speech auto-startup on switch failed: {_fe}")

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

    # ── Audio Stop ────────────────────────────────────────────────────────────────

    @app.route("/api/audio/stop", methods=["POST"])
    def audio_stop():
        """Stop any active TTS playback."""
        try:
            from hecos.core.audio.tts_manager import TTSManager
            TTSManager.stop()
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── Audio History Management ──────────────────────────────────────────────────

    @app.route("/api/audio/history/info", methods=["GET"])
    def audio_history_info():
        """Returns count and total size of WAV files in media/audio/history/."""
        try:
            import os, glob
            from hecos.modules.web_ui.routes_chat_tts import HISTORY_DIR
            files = glob.glob(os.path.join(HISTORY_DIR, "*.wav"))
            total_bytes = sum(os.path.getsize(f) for f in files if os.path.exists(f))
            size_mb = round(total_bytes / (1024 * 1024), 2)
            return jsonify({"ok": True, "count": len(files), "size_mb": size_mb})
        except Exception as e:
            logger.error(f"[WebUI] audio_history_info error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/audio/history/clear", methods=["POST"])
    def audio_history_clear():
        """Deletes all WAV files in media/audio/history/."""
        try:
            import os, glob
            from hecos.modules.web_ui.routes_chat_tts import HISTORY_DIR
            files = glob.glob(os.path.join(HISTORY_DIR, "*.wav"))
            deleted = 0
            for f in files:
                try:
                    os.remove(f)
                    deleted += 1
                except Exception:
                    pass
            logger.info(f"[WebUI] audio_history_clear: deleted {deleted} file(s).")
            return jsonify({"ok": True, "deleted": deleted})
        except Exception as e:
            logger.error(f"[WebUI] audio_history_clear error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── TTS Voices API ────────────────────────────────────────────────────────────

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

    # ── On-Demand TTS Engine Installer ───────────────────────────────────────────

    @app.route('/api/audio/install-engine', methods=['POST'])
    def install_tts_engine():
        """On-demand installation of a TTS engine (kokoro, xtts2, or fish_speech)."""
        data = request.get_json(force=True) or {}
        engine = data.get("engine", "").lower()
        if engine not in ("kokoro", "xtts2", "fish_speech", "fish"):
            logger.warning(f"[WebUI] install_tts_engine rejected unknown engine: '{engine}'")
            return jsonify({"ok": False, "error": f"Unknown engine: {engine}"}), 400
        try:
            from hecos.setup.engine import download_kokoro_engine, download_xtts_engine, download_fish_speech_engine
            from hecos.core.progress import progress
            import threading

            task_id = f"tts_engine_{engine}"
            existing_task = progress.get_task(task_id)
            if existing_task and existing_task.state in ("pending", "running"):
                return jsonify({"ok": True, "engine": engine, "task_id": task_id, "status": "already_running"})

            logger.info(f"[WebUI] Request to install TTS engine: '{engine}' - Starting progress task...")

            def _install():
                logger.info(f"[WebUI] Installation thread active for: {engine}")
                phases = [
                    ("deps", 85, "Installing dependencies"),
                    ("verify", 15, "Verifying engine availability"),
                ]
                with progress.task(task_id, title=f"TTS Engine {engine.upper()}", source="AUDIO", phases=phases) as pt:
                    pt.phase("deps")
                    if engine == "kokoro":
                        download_kokoro_engine()
                    elif engine == "xtts2":
                        download_xtts_engine()
                    else:
                        download_fish_speech_engine()
                    pt.phase("verify", message="Verifying engine availability...")

            t = threading.Thread(target=_install, daemon=True)
            t.start()

            # Return immediately so the client can track via SSE / HecosProgress
            if data.get("async", True):
                return jsonify({"ok": True, "engine": engine, "task_id": task_id, "status": "started"})

            t.join(timeout=1800)  # Max 30 min wait for synchronous calls

            if t.is_alive():
                return jsonify({"ok": False, "error": "Installation timed out after 30 minutes. It may still be running in the background."}), 500

            # Verify it's now importable
            if engine == "kokoro":
                from hecos.core.audio.tts.kokoro_engine import KokoroEngine
                ok = KokoroEngine.is_available()
            elif engine == "xtts2":
                from hecos.core.audio.tts.xtts_engine import XttsEngine
                ok = XttsEngine.is_available()
            else:
                from hecos.core.audio.tts.fish_speech_engine import FishSpeechEngine
                ok = FishSpeechEngine.is_available()

            if ok:
                logger.info(f"[WebUI] TTS engine '{engine}' installed successfully.")
                return jsonify({"ok": True, "engine": engine})
            else:
                return jsonify({"ok": False, "error": "Installation completed but engine is still not importable. Check logs."})
        except Exception as e:
            logger.error(f"[WebUI] install_tts_engine error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route('/api/audio/tts-status', methods=['GET'])
    def tts_engine_status():
        """Returns availability status for each TTS engine so the UI can show badges.
        - piper: always true if path is configured
        - kokoro: True if kokoro library is importable
        - xtts2: True only if TTS is installed AND the model files are cached on disk
        - fish_speech: True if requests/client available; fish_speech_ready if server responding or key present
        """
        status = {"piper": False, "kokoro": False, "xtts2": False, "fish_speech": False, "fish_speech_ready": False}
        try:
            import shutil
            status["piper"] = bool(shutil.which("piper") or cfg_mgr.config.get("audio", {}).get("piper_path"))
        except Exception:
            pass
        try:
            from hecos.core.audio.tts.kokoro_engine import KokoroEngine
            status["kokoro"] = KokoroEngine.is_available()
        except Exception:
            pass
        try:
            from hecos.core.audio.tts.xtts_engine import XttsEngine
            # is_available = library importable; model_ready = model files on disk
            lib_ok = XttsEngine.is_available()
            model_ok = XttsEngine.model_ready() if lib_ok else False
            status["xtts2"] = lib_ok and model_ok
            status["xtts2_lib"] = lib_ok   # library installed (but model may not be downloaded)
        except Exception:
            pass
        try:
            from hecos.core.audio.tts.fish_speech_engine import FishSpeechEngine
            status["fish_speech"] = FishSpeechEngine.is_available()
            status["fish_speech_ready"] = FishSpeechEngine.model_ready() if status["fish_speech"] else False
            from hecos.setup.engine import check_fish_speech_engine
            _, diag = check_fish_speech_engine()
            status["fish_speech_diag"] = diag
        except Exception:
            pass
        return jsonify({"ok": True, **status})

    @app.route('/api/audio/fish/server-status', methods=['GET'])
    def fish_server_status():
        """Returns real-time status of the local Fish Speech server."""
        try:
            from hecos.core.audio.tts.fish_speech_daemon import FishSpeechDaemon
            daemon = FishSpeechDaemon.get_instance()
            host, port = daemon._resolve_target()
            is_local = daemon.is_local_target()
            healthy = daemon.is_healthy(host, port, timeout=1.5)
            listening = daemon.is_port_listening(host, port)
            
            # Check model name / checkpoint info
            s2_pro_dir = os.path.join(root_dir, "hecos", "engines", "fish_speech", "checkpoints", "s2-pro")
            model_installed = os.path.exists(s2_pro_dir)
            
            state = "online" if healthy else ("starting" if (listening or daemon.is_starting()) else "offline")
            return jsonify({
                "ok": True,
                "is_local": is_local,
                "host": host,
                "port": port,
                "listening": listening,
                "healthy": healthy,
                "status": state,
                "model_installed": model_installed,
                "model_name": "Fish Speech S2-Pro (Dual-AR)",
                "last_error": daemon.get_last_error()
            })
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route('/api/audio/fish/server-action', methods=['POST'])
    def fish_server_action():
        """Controls the local Fish Speech daemon process: restart, start, stop."""
        try:
            data = request.get_json(force=True) or {}
            action = data.get("action", "restart").lower()
            from hecos.core.audio.tts.fish_speech_daemon import FishSpeechDaemon
            daemon = FishSpeechDaemon.get_instance()
            
            if action == "restart":
                logger.info("[WebUI] User requested Fish Speech server RESTART.")
                ok, msg = daemon.restart(timeout=75.0)
                return jsonify({"ok": ok, "message": msg, "action": "restart"})
            elif action == "start":
                logger.info("[WebUI] User requested Fish Speech server START.")
                ok, msg = daemon.ensure_running(timeout=75.0)
                return jsonify({"ok": ok, "message": msg, "action": "start"})
            elif action == "stop":
                logger.info("[WebUI] User requested Fish Speech server STOP.")
                daemon.stop()
                return jsonify({"ok": True, "message": "Fish Speech local server stopped and VRAM released.", "action": "stop"})
            else:
                return jsonify({"ok": False, "error": f"Unknown action: {action}"}), 400
        except Exception as exc:
            logger.error(f"[WebUI] fish_server_action error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

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

    @app.route('/api/audio/fish/models', methods=['GET'])
    def fish_list_models():
        """Lists available model checkpoints on disk and known model specifications."""
        try:
            from hecos.core.audio.device_manager import get_audio_config
            acfg = get_audio_config()
            active_ckpt = acfg.get("fish_speech", {}).get("model_checkpoint", "s2-pro")
            checkpoints_dir = os.path.join(root_dir, "hecos", "engines", "fish_speech", "checkpoints")

            installed_models = []
            if os.path.exists(checkpoints_dir):
                for entry in sorted(os.listdir(checkpoints_dir)):
                    entry_path = os.path.join(checkpoints_dir, entry)
                    if os.path.isdir(entry_path):
                        total_bytes = 0
                        files = []
                        for root_sub, _, filenames in os.walk(entry_path):
                            for fn in filenames:
                                fp = os.path.join(root_sub, fn)
                                sz = os.path.getsize(fp)
                                total_bytes += sz
                                files.append(fn)

                        is_active = (entry == active_ckpt)
                        friendly_name = entry
                        desc = f"Local checkpoint in checkpoints/{entry}"
                        if entry == "s2-pro":
                            friendly_name = "Fish Speech S2-Pro (Dual-AR 36L FP16)"
                            desc = "High-fidelity local model with native support for expressive emotion tags ([whisper], [laughing], etc.) and zero-shot voice cloning."
                        elif entry == "fish-speech-1.5":
                            friendly_name = "Fish Speech 1.5 (Dual-AR + Firefly GAN)"
                            desc = "Legacy lightweight version with 44.1kHz Firefly GAN vocoder for low VRAM systems."

                        installed_models.append({
                            "id": entry,
                            "name": friendly_name,
                            "description": desc,
                            "installed": True,
                            "active": is_active,
                            "size_mb": round(total_bytes / (1024 * 1024), 1),
                            "files": files[:8]
                        })

            # Sort so s2-pro is first
            installed_models.sort(key=lambda m: 0 if m["id"] == "s2-pro" else (1 if m["id"] == "fish-speech-1.5" else 2))

            catalog = [
                {
                    "id": "s2-pro",
                    "name": "Fish Speech S2-Pro (Dual-AR FP16)",
                    "type": "Local Weights (~10 GB)",
                    "recommended": True,
                    "architecture": "36-layer Dual-AR Transformer + DAC Codec",
                    "description": "Optimized for consumer GPUs (8-16 GB VRAM). Supports zero-shot voice cloning and native emotion tags.",
                    "repo": "fishaudio/s2-pro"
                },
                {
                    "id": "fish-speech-1.5",
                    "name": "Fish Speech 1.5 (Legacy)",
                    "type": "Local Weights (~2 GB)",
                    "recommended": False,
                    "architecture": "Dual-AR + Firefly GAN",
                    "description": "Ultra-lightweight legacy version designed for systems with limited VRAM.",
                    "repo": "fishaudio/fish-speech-1.5"
                },
                {
                    "id": "drama-3",
                    "name": "Fish Audio Drama 3 (MoE 35B)",
                    "type": "Cloud API / Multi-Character MoE",
                    "recommended": False,
                    "architecture": "35B Parameter Mixture-of-Experts (3B active) + Codebook-MTP",
                    "description": "Theatrical multi-character model (up to 16 voices) for complex dramatic acting and script reading. Requires ~70 GB VRAM locally; recommended via Fish Audio Cloud API.",
                    "repo": "fishaudio/drama-3",
                    "cloud_recommended": True
                }
            ]

            return jsonify({
                "ok": True,
                "active_checkpoint": active_ckpt,
                "checkpoints_dir": checkpoints_dir,
                "installed_models": installed_models,
                "catalog": catalog
            })
        except Exception as exc:
            logger.error(f"[WebUI] fish_list_models error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route('/api/audio/fish/select-model', methods=['POST'])
    def fish_select_model():
        """Switches active Fish Speech checkpoint and restarts daemon."""
        try:
            data = request.get_json(force=True) or {}
            checkpoint = str(data.get("checkpoint", "s2-pro")).strip()
            from hecos.core.audio.device_manager import get_audio_config, _save_audio_config
            from hecos.core.audio.tts.fish_speech_daemon import FishSpeechDaemon

            acfg = get_audio_config()
            if "fish_speech" not in acfg:
                acfg["fish_speech"] = {}
            acfg["fish_speech"]["model_checkpoint"] = checkpoint
            _save_audio_config(acfg)

            logger.info(f"[WebUI] Selected Fish Speech checkpoint '{checkpoint}'. Restarting daemon...")
            daemon = FishSpeechDaemon.get_instance()
            ok, msg = daemon.restart(timeout=85.0)

            return jsonify({
                "ok": ok,
                "checkpoint": checkpoint,
                "message": f"Checkpoint switched to '{checkpoint}'. Server reload: {msg}"
            })
        except Exception as exc:
            logger.error(f"[WebUI] fish_select_model error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route('/api/audio/fish/open-folder', methods=['POST'])
    def fish_open_checkpoints_folder():
        """Opens the checkpoints directory in Windows File Explorer."""
        try:
            import subprocess
            checkpoints_dir = os.path.join(root_dir, "hecos", "engines", "fish_speech", "checkpoints")
            checkpoints_dir = os.path.normpath(os.path.abspath(checkpoints_dir))
            os.makedirs(checkpoints_dir, exist_ok=True)
            if sys.platform == "win32":
                try:
                    subprocess.Popen(f'explorer.exe "{checkpoints_dir}"', shell=True)
                except Exception:
                    os.startfile(checkpoints_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", checkpoints_dir])
            else:
                subprocess.Popen(["xdg-open", checkpoints_dir])
            return jsonify({"ok": True, "path": checkpoints_dir})
        except Exception as exc:
            logger.error(f"[WebUI] fish_open_checkpoints_folder error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route('/api/audio/kokoro/open-folder', methods=['POST'])
    def kokoro_open_models_folder():
        """Opens the Kokoro models directory in Windows File Explorer."""
        try:
            import subprocess
            models_dir = os.path.join(root_dir, "hecos", "models", "kokoro")
            models_dir = os.path.normpath(os.path.abspath(models_dir))
            os.makedirs(models_dir, exist_ok=True)
            if sys.platform == "win32":
                try:
                    subprocess.Popen(f'explorer.exe "{models_dir}"', shell=True)
                except Exception:
                    os.startfile(models_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", models_dir])
            else:
                subprocess.Popen(["xdg-open", models_dir])
            return jsonify({"ok": True, "path": models_dir})
        except Exception as exc:
            logger.error(f"[WebUI] kokoro_open_models_folder error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route('/api/audio/kokoro/models', methods=['GET'])
    def kokoro_get_models():
        """Lists available local Kokoro models and checkpoints."""
        try:
            import glob
            models_dir = os.path.join(root_dir, "hecos", "models", "kokoro")
            models_dir = os.path.normpath(os.path.abspath(models_dir))
            os.makedirs(models_dir, exist_ok=True)

            models = [
                {
                    "id": "",
                    "name": "Kokoro-82M v1.0 (Integrated Default)",
                    "path": "Default integrated local model",
                    "type": "integrated"
                }
            ]

            # Scan .pth files in models_dir
            for pth in glob.glob(os.path.join(models_dir, "*.pth")):
                fname = os.path.basename(pth)
                size_mb = round(os.path.getsize(pth) / (1024 * 1024), 1)
                models.append({
                    "id": pth,
                    "name": f"{fname} ({size_mb} MB)",
                    "path": pth,
                    "type": "file"
                })

            # Scan subdirectories in models_dir
            for item in os.listdir(models_dir):
                item_path = os.path.join(models_dir, item)
                if os.path.isdir(item_path):
                    pths = glob.glob(os.path.join(item_path, "*.pth"))
                    if pths or os.path.exists(os.path.join(item_path, "config.json")):
                        models.append({
                            "id": item_path,
                            "name": f"{item} (Directory)",
                            "path": item_path,
                            "type": "directory"
                        })

            return jsonify({
                "ok": True,
                "models": models,
                "folder": models_dir
            })
        except Exception as exc:
            logger.error(f"[WebUI] kokoro_get_models error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500



