"""
Hecos Web UI - Audio TTS Engines & Local Server Routes
Endpoints for on-demand installation, readiness diagnostic badges, Fish Speech local daemon management,
and local checkpoint folder exploration for Kokoro and Fish Speech.
"""

import os
import sys
import glob
import threading
import subprocess
from flask import request, jsonify


def register_audio_engines_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    """Registers TTS engines installer, status check, and local server daemon management routes."""

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
        """Returns availability status for each TTS engine so the UI can show badges."""
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
            lib_ok = XttsEngine.is_available()
            model_ok = XttsEngine.model_ready() if lib_ok else False
            status["xtts2"] = lib_ok and model_ok
            status["xtts2_lib"] = lib_ok
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

    @app.route('/api/audio/engines/status', methods=['GET'])
    def tts_all_engines_runtime_status():
        """Returns live runtime status (PID, RAM/VRAM, state, autostart) for all 4 TTS engines."""
        try:
            from hecos.core.audio.tts_manager import get_all_engines_status
            return jsonify(get_all_engines_status())
        except Exception as exc:
            logger.error(f"[WebUI] tts_all_engines_runtime_status error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route('/api/audio/engines/<engine>/action', methods=['POST'])
    def tts_engine_runtime_action(engine):
        """Controls runtime lifecycle (start/load, stop/unload, restart) of any TTS engine or 'all'."""
        try:
            data = request.get_json(force=True) or {}
            action = str(data.get("action", "")).strip().lower()
            from hecos.core.audio.tts_manager import perform_engine_action, get_all_engines_status, normalize_engine_name
            logger.info(f"[WebUI] TTS runtime action requested: engine='{engine}', action='{action}'")
            ok, msg = perform_engine_action(engine, action)
            all_st = get_all_engines_status()
            eng_st = all_st.get("engines", {}).get(normalize_engine_name(engine))
            return jsonify({
                "ok": ok,
                "engine": engine,
                "action": action,
                "message": msg,
                "error": None if ok else msg,
                "status": eng_st,
                "engines": all_st.get("engines", {}),
            })
        except Exception as exc:
            logger.error(f"[WebUI] tts_engine_runtime_action error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

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

            for pth in glob.glob(os.path.join(models_dir, "*.pth")):
                fname = os.path.basename(pth)
                size_mb = round(os.path.getsize(pth) / (1024 * 1024), 1)
                models.append({
                    "id": pth,
                    "name": f"{fname} ({size_mb} MB)",
                    "path": pth,
                    "type": "file"
                })

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

