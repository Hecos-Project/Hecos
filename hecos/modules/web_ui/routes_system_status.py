"""
routes_system_status.py
────────────────────────────────────────────────────────────────────────────
Hecos WebUI — System Status API
Registers: GET /hecos/status
────────────────────────────────────────────────────────────────────────────
"""
import os
import yaml
import urllib.parse
from datetime import datetime
from flask import jsonify


def init_system_status_routes(app, cfg_mgr, root_dir, logger, get_sm, cpu_cache, get_vram_usage):
    """Register the /hecos/status endpoint."""

    def _sm():
        return get_sm() if callable(get_sm) else get_sm

    @app.route("/hecos/status", methods=["GET"])
    def get_status():
        try:
            import psutil
            cfg     = cfg_mgr.config
            backend = cfg.get("backend", {}).get("type", "?")
            if   backend == "cloud":  model = cfg.get("backend", {}).get("cloud",  {}).get("model", "?")
            elif backend == "ollama": model = cfg.get("backend", {}).get("ollama", {}).get("model", "?")
            elif backend == "kobold": model = cfg.get("backend", {}).get("kobold", {}).get("model", "?")
            else: model = "?"

            br    = cfg.get("bridge", {})
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
                mic_on          = sm.listening_status
                tts_on          = sm.voice_status
                last_tool       = sm.last_tool
                tokens_p        = sm.last_tokens_prompt
                tokens_c        = sm.last_tokens_completion
                last_model_live = sm.last_model
            else:
                from hecos.core.audio.device_manager import get_audio_config
                acfg   = get_audio_config()
                mic_on = acfg.get("listening_status", False)
                tts_on = acfg.get("voice_status", False)

            active_model = last_model_live if last_model_live else model
            mic_status   = "ON" if mic_on else "OFF"
            tts_status   = "ON" if tts_on else "OFF"

            from hecos.core.audio.device_manager import get_audio_config
            acfg       = get_audio_config()
            ptt_status = "ON" if acfg.get("push_to_talk", False) else "OFF"

            config_path = cfg_mgr.yaml_path
            mtime = os.path.getmtime(config_path) if os.path.exists(config_path) else 0
            ts    = datetime.fromtimestamp(mtime).strftime("%H:%M:%S") if mtime else "?"

            persona = cfg.get("ai", {}).get("active_personality", "Hecos_System_Soul")
            if persona.endswith(".yaml"):
                persona = persona[:-5]

            avatar_path = "/assets/Hecos_Logo_NBG.png"
            try:
                p_dir  = os.path.join(root_dir, "hecos", "personality")
                p_file = os.path.join(p_dir, f"{persona}.yaml")
                if not os.path.exists(p_file):
                    persona = "Hecos_System_Soul"
                    p_file  = os.path.join(p_dir, f"{persona}.yaml")
                if os.path.exists(p_file):
                    with open(p_file, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if data and data.get("avatar_image"):
                        encoded_path = urllib.parse.quote(data.get("avatar_image"))
                        avatar_path  = "/assets/" + encoded_path
            except Exception:
                pass

            # Telemetry
            dsb_cfg          = cfg.get("plugins", {}).get("DASHBOARD", {})
            global_enabled   = dsb_cfg.get("enabled", True)
            webui_telemetry  = dsb_cfg.get("webui_telemetry_enabled", True)
            telemetry_active = global_enabled and webui_telemetry

            cpu_cache["enabled"] = telemetry_active and dsb_cfg.get("track_cpu", True)

            cpu_val = ram_val = vram_val = None
            if telemetry_active:
                if dsb_cfg.get("track_cpu",  True): cpu_val  = cpu_cache.get("value", 0)
                if dsb_cfg.get("track_ram",  True): ram_val  = psutil.virtual_memory().percent
                if dsb_cfg.get("track_vram", True): vram_val = get_vram_usage()

            return jsonify({
                "backend":    backend.upper(),
                "model":      active_model,
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
                "tokens_c":   tokens_c,
            })
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500
