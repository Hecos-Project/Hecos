import os
import json
import time
import threading
import sys
import yaml
import urllib.parse
import psutil
from datetime import datetime
from flask import request, jsonify, render_template
from hecos.core.constants import LOGS_DIR
from hecos.core.logging.hub import get_hub
import subprocess

# ── CPU background sampler ─────────────────────────────────────────────────────
# psutil.cpu_percent() without interval= always returns 0.0 or 100% on first
# call because it has no baseline. We cache a reading every 2 seconds instead.
_cpu_cache = {"value": 0.0, "enabled": True}

def _cpu_sampler():
    # Prime the baseline sample (discarded)
    psutil.cpu_percent(interval=None)
    while True:
        try:
            if _cpu_cache.get("enabled", True):
                _cpu_cache["value"] = psutil.cpu_percent(interval=2)
            else:
                # When disabled, we sleep longer and do nothing to save resources
                time.sleep(5)
        except Exception:
            time.sleep(5)

_cpu_thread = threading.Thread(target=_cpu_sampler, daemon=True)
_cpu_thread.start()
# ──────────────────────────────────────────────────────────────────────────────

def get_vram_usage():
    """Returns VRAM usage percentage via nvidia-smi, or 0 if fails."""
    try:
        cmd = ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"]
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000 # CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kwargs["startupinfo"] = startupinfo
            
        res = subprocess.check_output(cmd, encoding="utf-8", timeout=2, **kwargs).strip()
        if res:
            used, total = [int(x.strip()) for x in res.split(",")]
            if total > 0:
                return round((used / total) * 100, 1)
    except Exception:
        pass
    return 0

def init_system_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    # Set global telemetry flag based on DASHBOARD plugin status
    global _cpu_cache
    dsb_cfg = cfg_mgr.config.get("plugins", {}).get("DASHBOARD", {})
    global_enabled = dsb_cfg.get("enabled", True)
    webui_telemetry = dsb_cfg.get("webui_telemetry_enabled", True)
    _cpu_cache["enabled"] = global_enabled and webui_telemetry

    def _sm():
        return get_sm() if callable(get_sm) else get_sm

    @app.route("/hecos/logs")
    def standalone_logs():
        try:
            from hecos.core.i18n.translator import get_translator
            translations = get_translator().get_translations()
            return render_template("standalone_logs.html", 
                                 zconfig=cfg_mgr.config, 
                                 translations=translations)
        except Exception as e:
            logger.error(f"Error serving standalone logs: {e}")
            return str(e), 500


    @app.route("/hecos/heartbeat", methods=["POST"])
    def heartbeat():
        try:
            data = request.get_json(force=True) or {}
            page_type = data.get("type", "unknown")
            import tempfile
            hb_file = os.path.join(tempfile.gettempdir(), "hecos_webui_heartbeat.json")
            hb_data = {}
            if os.path.exists(hb_file):
                try:
                    with open(hb_file, "r") as f: hb_data = json.load(f)
                except: pass
            hb_data[page_type] = time.time()
            os.makedirs(os.path.dirname(hb_file), exist_ok=True)
            with open(hb_file, "w") as f: json.dump(hb_data, f)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/assets/<path:filename>")
    def serve_assets(filename):
        from flask import send_from_directory, make_response
        import mimetypes
        assets_dir = os.path.join(root_dir, "hecos", "assets")
        
        # Flask's send_from_directory prefers forward slashes even on Windows
        resp = make_response(send_from_directory(assets_dir, filename))
        
        # Ensure correct mimetype, especially on Windows where registry might be broken
        mtype, _ = mimetypes.guess_type(filename)
        if mtype:
            resp.headers["Content-Type"] = mtype
        # Prevent aggressive browser caching for assets to ensure UI updates are seen
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
    
    @app.route("/hecos/status", methods=["GET"])
    def get_status():
        try:
            cfg     = cfg_mgr.config
            backend = cfg.get("backend", {}).get("type", "?")
            if   backend == "cloud":  model = cfg.get("backend", {}).get("cloud",  {}).get("model", "?")
            elif backend == "ollama": model = cfg.get("backend", {}).get("ollama", {}).get("model", "?")
            elif backend == "kobold": model = cfg.get("backend", {}).get("kobold", {}).get("model", "?")
            else: model = "?"

            br      = cfg.get("bridge", {})
            flags = [k for k, v in [
                ("proc",        br.get("use_processor")),
                ("think-strip", br.get("remove_think_tags")),
                ("tools",       br.get("enable_tools")),
            ] if v]

            sm = _sm()
            last_tool = None
            tokens_p = 0
            tokens_c = 0
            last_model_live = None

            if sm is not None:
                mic_on     = sm.listening_status
                tts_on     = sm.voice_status
                last_tool  = sm.last_tool
                tokens_p   = sm.last_tokens_prompt
                tokens_c   = sm.last_tokens_completion
                last_model_live = sm.last_model
            else:
                from hecos.core.audio.device_manager import get_audio_config
                acfg = get_audio_config()
                mic_on     = acfg.get("listening_status", False)
                tts_on     = acfg.get("voice_status", False)

            # Prefers the dynamic last_model over static config 'model'
            active_model = last_model_live if last_model_live else model

            mic_status = "ON" if mic_on else "OFF"
            tts_status = "ON" if tts_on else "OFF"
            
            from hecos.core.audio.device_manager import get_audio_config, _save_audio_config
            acfg = get_audio_config()
            ptt_on = acfg.get("push_to_talk", False)
            if not mic_on and ptt_on:
                ptt_on = False
                acfg["push_to_talk"] = False
                try: _save_audio_config(acfg)
                except Exception: pass
            
            ptt_status = "ON" if ptt_on else "OFF"

            from datetime import datetime
            config_path = cfg_mgr.yaml_path
            mtime = os.path.getmtime(config_path) if os.path.exists(config_path) else 0
            ts    = datetime.fromtimestamp(mtime).strftime("%H:%M:%S") if mtime else "?"

            persona = cfg.get("ai", {}).get("active_personality", "Hecos_System_Soul")
            if persona.endswith(".yaml"): persona = persona[:-5]
            
            avatar_path = "/assets/Hecos_Logo_NBG.png"
            try:
                p_dir = os.path.join(root_dir, "hecos", "personality")
                p_file = os.path.join(p_dir, f"{persona}.yaml")
                
                # Check for existence of the persona file. Fallback if not found.
                if not os.path.exists(p_file):
                    persona = "Hecos_System_Soul"
                    p_file = os.path.join(p_dir, f"{persona}.yaml")
                    
                if os.path.exists(p_file):
                    with open(p_file, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if data and data.get("avatar_image"):
                            encoded_path = urllib.parse.quote(data.get("avatar_image"))
                            avatar_path = "/assets/" + encoded_path
            except Exception: pass
            
            # --- Optimized Telemetry ---
            dsb_cfg = cfg.get("plugins", {}).get("DASHBOARD", {})
            global_enabled = dsb_cfg.get("enabled", True)
            webui_telemetry = dsb_cfg.get("webui_telemetry_enabled", True)
            telemetry_active = global_enabled and webui_telemetry
            
            # Sync background CPU thread enabled state
            _cpu_cache["enabled"] = telemetry_active and dsb_cfg.get("track_cpu", True)

            cpu_val  = None
            ram_val  = None
            vram_val = None

            if telemetry_active:
                if dsb_cfg.get("track_cpu", True):
                    cpu_val  = _cpu_cache.get("value", 0)
                if dsb_cfg.get("track_ram", True):
                    ram_val  = psutil.virtual_memory().percent
                if dsb_cfg.get("track_vram", True):
                    vram_val = get_vram_usage()
            
            return jsonify({
                "backend":    backend.upper(),
                "model":      active_model,   # Dynamically updated
                "persona":    persona,
                "avatar":     avatar_path,
                "avatar_size": cfg.get("ai", {}).get("avatar_size", "medium"),
                "bridge":     ", ".join(flags) if flags else "default",
                "mic":        mic_status,
                "tts":        tts_status,
                "ptt":        ptt_status,
                "cpu":        cpu_val,
                "ram":        ram_val,
                "vram":       vram_val,
                "config":     f"last save {ts}",
                "last_tool":  last_tool,
                "tokens_p":   tokens_p,
                "tokens_c":   tokens_c
            })
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # ── Payload Inspection API ─────────────────────────────────────────────────────

    @app.route("/api/system/payload", methods=["GET"])
    def get_system_payload():
        """Returns the last LLM payload sizes for context usage optimization."""
        try:
            from hecos.core.llm.client import LAST_PAYLOAD_INFO
            return jsonify({"ok": True, "payload": LAST_PAYLOAD_INFO})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    # ── Generation Control API ─────────────────────────────────────────────────────

    @app.route("/api/system/stop", methods=["POST"])
    def system_stop():
        """Interrupts any ongoing backend generation (Console/Voice input)."""
        try:
            sm = _sm()
            if sm:
                sm.webui_stop_requested = True
            logger.info("[WebUI] User requested generation stop.")
            return jsonify({"ok": True, "message": "Stop requested."})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    # ── Memory Control API ─────────────────────────────────────────────────────

    @app.route("/api/memory/clear", methods=["POST"])
    def memory_clear():
        """Wipes the episodic history from the DB (optionally granular)."""
        try:
            data = request.get_json(force=True) or {}
            days = data.get("days") if data.get("days") != "all" else None
            if days is not None:
                try: days = int(days)
                except: days = None
            
            from hecos.memory.brain_interface import clear_history
            cleared = clear_history(days=days)
            if cleared:
                msg = f"History cleared (days={days if days else 'all'})."
                logger.info(f"[WebUI] {msg}")
                return jsonify({"ok": True, "message": msg})
            return jsonify({"ok": False, "error": "Failed to clear."}), 500
        except Exception as exc:
            logger.error(f"[WebUI] memory_clear error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/memory/status", methods=["GET"])
    def memory_status():
        """Returns memory row count and config."""
        try:
            from hecos.memory.brain_interface import get_memory_stats
            stats = get_memory_stats()
            cog = cfg_mgr.config.get("cognition", {})
            return jsonify({
                "ok": True, 
                "total_messages": stats.get("total_messages", 0), 
                "cognition": cog
            })
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500


    @app.route("/api/events")
    def stream_events():
        from flask import Response, stream_with_context
        import time
        def generate():
            while True:
                # Dynamic SM resolution: ensures we pick up the Correct state manager 
                # even if it's injected/swapped after the SSE connection is established.
                sm_live = _sm()
                if sm_live:
                    # Drain the event queue — voice_detected is emitted by handle_voice_input()
                    # via add_event(), NOT via detected_voice_command directly (race condition risk)
                    events = sm_live.pop_events()
                    for ev in events:
                        out_ev = {"type": ev.get("type")}
                        data = ev.get("data")
                        if isinstance(data, dict):
                            out_ev.update(data)
                        elif data is not None:
                            out_ev["data"] = data
                        yield f"data: {json.dumps(out_ev)}\n\n"

                time.sleep(0.1)
        
        return Response(stream_with_context(generate()), mimetype="text/event-stream")

    @app.route("/api/persona/avatar", methods=["GET"])
    def persona_avatar_get():
        """Returns the avatar URL for a given persona name."""
        persona = request.args.get("persona", "").strip()
        if not persona:
            return jsonify({"ok": False, "error": "Missing persona name"}), 400
        
        # Strip .yaml if sent from frontend
        if persona.endswith(".yaml"):
            persona = persona[:-5]
        
        p_dir = os.path.join(root_dir, "hecos", "personality")
        p_file = os.path.join(p_dir, f"{persona}.yaml")
        
        default_avatar = "/assets/Hecos_Logo_NBG.png"
        
        if not os.path.exists(p_file):
            return jsonify({"ok": True, "avatar_path": default_avatar})
        
        try:
            with open(p_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            ai = data.get("avatar_image", "")
            if ai:
                encoded = urllib.parse.quote(ai)
                return jsonify({"ok": True, "avatar_path": f"/assets/{encoded}"})
            else:
                return jsonify({"ok": True, "avatar_path": default_avatar})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/persona/avatar/upload", methods=["POST"])

    def persona_avatar_upload():
        """Handles image upload for a specific personality."""
        try:
            if 'file' not in request.files:
                return jsonify({"ok": False, "error": "No file part"}), 400
            file = request.files['file']
            persona = request.form.get("persona")
            if not file or not persona:
                return jsonify({"ok": False, "error": "Missing file or persona name"}), 400
            
            # 1. Prepare directories (Inside hecos/assets/avatars/)
            assets_dir = os.path.join(root_dir, "hecos", "assets")
            avatar_base_dir = os.path.join(assets_dir, "avatars")
            
            # Use secure_filename for the folder as well to avoid space/special char issues
            from werkzeug.utils import secure_filename
            safe_persona = secure_filename(persona)
            persona_avatar_dir = os.path.join(avatar_base_dir, safe_persona)
            os.makedirs(persona_avatar_dir, exist_ok=True)
            
            # 2. Save file
            filename = secure_filename(file.filename)
            save_path = os.path.join(persona_avatar_dir, filename)
            file.save(save_path)
            
            # 3. Update YAML
            import yaml
            p_dir = os.path.join(root_dir, "hecos", "personality")
            p_file = os.path.join(p_dir, f"{persona}.yaml")
            
            if os.path.exists(p_file):
                with open(p_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                
                # Update the path relative to avatars/
                data["avatar_image"] = f"avatars/{safe_persona}/{filename}"
                
                with open(p_file, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, allow_unicode=True, sort_keys=False)
            
            logger.info(f"[WebUI] Avatar uploaded for persona {persona}: {filename}")
            return jsonify({"ok": True, "avatar_path": f"/assets/avatars/{safe_persona}/{filename}"})
        except Exception as exc:
            logger.error(f"[WebUI] persona_avatar_upload error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/system/reboot", methods=["POST"])
    def system_reboot():
        """Reboots the entire Hecos system via os._exit(0)."""
        try:
            logger.info("[WebUI] User requested system reboot from Web UI.")
            
            # Start a background thread to allow the HTTP response to complete first
            def do_reboot():
                import time, os, winsound
                from hecos.core.i18n.translator import t
                time.sleep(1.0)
                print(f"\n\033[91m[WEB_UI] Riavvio del sistema in corso...\033[0m")
                winsound.Beep(600, 150)
                winsound.Beep(400, 150)
                os._exit(42)
                
            threading.Thread(target=do_reboot, daemon=True).start()
            return jsonify({"ok": True, "message": "Reboot initiated"})
        except Exception as exc:
            logger.error(f"[WebUI] system_reboot error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    # ── SysNet Proxy Test (SSE streaming) ─────────────────────────────────────────

    @app.route("/api/sysnet/test-proxy")
    def sysnet_test_proxy():
        """SSE endpoint: tests the proxy URL passed as query param ?url=... step by step."""
        from flask import Response, stream_with_context, request as flask_req
        import time

        proxy_url = flask_req.args.get("url", "").strip()

        def generate():
            def emit(msg, level="INFO"):
                data = json.dumps({"msg": msg, "level": level, "ts": time.strftime("%H:%M:%S")})
                return f"data: {data}\n\n"

            yield emit("🔍 Avvio test connettività proxy...")
            time.sleep(0.1)

            if not proxy_url:
                yield emit("⚠️  Nessun proxy configurato — test della connessione diretta.", "WARN")
                time.sleep(0.2)
                try:
                    import urllib.request
                    yield emit("→ Contatto api.ipify.org (connessione diretta)...")
                    ip = urllib.request.urlopen("https://api.ipify.org", timeout=6).read().decode()
                    yield emit(f"✅ Connessione diretta OK. IP pubblico: {ip}", "OK")
                except Exception as e:
                    yield emit(f"❌ Connessione diretta fallita: {e}", "ERR")
                yield emit("--- Fine test ---", "DONE")
                return

            # Proxy URL provided
            import re
            m = re.match(r'^(\w+)://(?:[^@]+@)?([^:/]+):(\d+)', proxy_url)
            if m:
                proto, host, port = m.group(1), m.group(2), m.group(3)
                yield emit(f"📡 Proxy rilevato: protocollo={proto.upper()}, host={host}, porta={port}")
            else:
                yield emit(f"📡 Proxy URL: {proxy_url}")
            time.sleep(0.1)

            # Step 1: DNS resolve the proxy host
            if m:
                yield emit(f"→ Risoluzione DNS di {host}...")
                try:
                    import socket
                    ip_resolved = socket.gethostbyname(host)
                    yield emit(f"✅ DNS risolto: {host} → {ip_resolved}", "OK")
                except Exception as e:
                    yield emit(f"❌ DNS fallito: {e}. Verificare che l'host del proxy sia corretto.", "ERR")
                    yield emit("--- Interruzione test: host non raggiungibile ---", "DONE")
                    return
                time.sleep(0.1)

                # Step 2: TCP port check
                yield emit(f"→ Test connessione TCP su {host}:{port}...")
                try:
                    import socket
                    sock = socket.create_connection((host, int(port)), timeout=5)
                    sock.close()
                    yield emit(f"✅ Porta {port} aperta e raggiungibile.", "OK")
                except Exception as e:
                    yield emit(f"❌ Porta {port} non raggiungibile: {e}", "ERR")
                    yield emit("--- Interruzione test: porta chiusa o firewall ---", "DONE")
                    return
                time.sleep(0.1)

            # Step 3: HTTP request through proxy
            yield emit("→ Tentativo richiesta HTTP tramite proxy (ipinfo.io)...")
            try:
                import requests as req_lib
                proxies = {"http": proxy_url, "https": proxy_url}
                r = req_lib.get("https://ipinfo.io/json", proxies=proxies, timeout=12)
                if r.status_code == 200:
                    data = r.json()
                    ext_ip = data.get("ip", "N/A")
                    city = data.get("city", "Sconosciuta")
                    country = data.get("country", "??")
                    region_str = f"{city}, {country}"
                    
                    yield emit(f"✅ PROXY FUNZIONANTE! IP: {ext_ip} ({region_str})", "OK")
                    yield emit(f"ℹ️  Le richieste Hecos useranno questo IP in questa regione.", "OK")
                    
                    # Invia un evento payload speciale per aggiornare l'UI
                    payload = json.dumps({"ip": ext_ip, "loc": region_str, "status": "active"})
                    yield emit(payload, "PAYLOAD")
                else:
                    yield emit(f"⚠️  Proxy raggiunto ma risposta inattesa: HTTP {r.status_code}", "WARN")
            except Exception as e:
                err_msg = str(e)
                if "timed out" in err_msg.lower():
                    yield emit(f"⏱️  Timeout: il proxy non ha risposto entro 12s. Prova un proxy più veloce.", "ERR")
                elif "refused" in err_msg.lower():
                    yield emit(f"🚫 Connessione rifiutata dal proxy. Verificare porta e indirizzo.", "ERR")
                elif "SOCKS" in err_msg:
                    yield emit(f"❌ Errore SOCKS: {err_msg[:120]}", "ERR")
                else:
                    yield emit(f"❌ Errore: {err_msg[:150]}", "ERR")

            yield emit("--- Fine test ---", "DONE")
        return Response(stream_with_context(generate()), mimetype="text/event-stream",
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    # ── Diagnostic & Maintenance Endpoints ─────────────────────────────────────

    @app.route("/api/system/diagnostic/full-check", methods=["POST"])
    def diagnostic_full_check():
        try:
            from hecos.setup.engine import check_python_version, check_dependencies, auto_fix_piper_path
            import io
            from contextlib import redirect_stdout
            
            output = io.StringIO()
            with redirect_stdout(output):
                check_python_version()
                check_dependencies()
                auto_fix_piper_path()
            
            return jsonify({"ok": True, "log": output.getvalue()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/system/diagnostic/fix-paths", methods=["POST"])
    def diagnostic_fix_paths():
        try:
            from hecos.setup.engine import auto_fix_piper_path
            import io
            from contextlib import redirect_stdout
            
            output = io.StringIO()
            with redirect_stdout(output):
                auto_fix_piper_path()
            
            return jsonify({"ok": True, "log": output.getvalue()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── Explorer & Bridge Roots ──────────────────────────────────────────────
    from hecos.modules.web_ui.routes_explorer import init_explorer_routes
    from hecos.modules.web_ui.routes_bridge import init_bridge_routes
    init_explorer_routes(app, logger)
    init_bridge_routes(app, logger)





