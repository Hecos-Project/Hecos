import os
import sys
import glob
from flask import request, jsonify
from hecos.core.constants import IMAGES_DIR, MEDIA_DIR

def init_media_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    def _sm():
        return get_sm() if callable(get_sm) else get_sm

    @app.route("/media/file")
    def serve_generic_file():
        """Serves any file from the local filesystem by its absolute path."""
        path = request.args.get("path")
        if not path:
            return jsonify({"ok": False, "error": "Path required"}), 400
        
        # Security: basic check (optional but good)
        if not os.path.exists(path):
            return jsonify({"ok": False, "error": f"File not found: {path}"}), 404
            
        allowed_exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg')
        if not path.lower().endswith(allowed_exts):
            # We still serve it if the user really wants, but maybe log it?
            pass

        try:
            from flask import send_file
            return send_file(path)
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/media/models", methods=["GET"])
    def get_media_models():
        """Returns available image generation models for the specified provider."""
        provider = request.args.get("provider", "pollinations")
        try:
            from hecos.core.media.image_providers import get_models_for_provider
            models = get_models_for_provider(provider)
            
            # Inject user custom models for Hugging Face
            if provider == "huggingface":
                media_cfg = cfg_mgr.config.get("media", {})
                custom_models = media_cfg.get("image_gen", {}).get("custom_hf_models", [])
                for m in custom_models:
                    if m not in models:
                        models.append(m)

            return jsonify({"ok": True, "provider": provider, "models": models})
        except Exception as exc:
            logger.error(f"[WebUI] get_media_models error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/hecos/api/media/open-folder", methods=["POST"])
    def open_media_folder():
        """Opens the root media/ folder in the OS file explorer."""
        try:
            os.makedirs(MEDIA_DIR, exist_ok=True)
            from hecos.core.system.os_adapter import OSAdapter
            OSAdapter.open_path(MEDIA_DIR)
            return jsonify({"ok": True, "message": "Folder opened"})
        except Exception as exc:
            logger.error(f"[WebUI] open_media_folder error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/hecos/api/media/clear", methods=["POST"])
    def clear_media_vault():
        """Deletes all generated items in centralized media/images/."""
        try:
            if not os.path.exists(IMAGES_DIR):
                return jsonify({"ok": True, "deleted": 0})
            
            files = glob.glob(os.path.join(IMAGES_DIR, "*"))
            count = 0
            for f in files:
                if os.path.isfile(f):
                    try:
                        os.remove(f)
                        count += 1
                    except Exception as e:
                        logger.error(f"[WebUI] Could not delete {f}: {e}")
            return jsonify({"ok": True, "deleted": count})
        except Exception as exc:
            logger.error(f"[WebUI] clear_media_vault error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/models/refresh", methods=["POST"])
    def refresh_models():
        from app.model_manager import ModelManager
        mm = ModelManager(cfg_mgr)
        mm.get_available_models() # This updates the cache in config
        return jsonify({"ok": True})

    @app.route("/hecos/api/media/refine-prompt", methods=["POST"])
    def refine_media_prompt():
        """Refines a draft prompt using Hecos's Brain for Flux."""
        try:
            data = request.json or {}
            prompt = data.get("prompt", "").strip()
            instructions = data.get("instructions", "").strip()
            if not prompt:
                return jsonify({"ok": False, "error": "Prompt is empty"})
                
            from hecos.core.llm import client
            from app.model_manager import ModelManager
            
            system_prompt = (
                "You are an expert prompt engineer specializing in the Flux image generation model. "
                "Flux prefers detailed, natural language descriptions over comma-separated tags. "
                f"{instructions}"
            )
            user_msg = f"Optimize this prompt for Flux: {prompt}"
            
            main_cfg = cfg_mgr.config
            effective_backend_type, effective_default_model = ModelManager.get_effective_model_info(main_cfg)
            backend_config = main_cfg.get('backend', {}).get(effective_backend_type, {}).copy()
            backend_config['model'] = effective_default_model
            backend_config['backend_type'] = effective_backend_type
            llm_cfg = main_cfg.get('llm', {})
            
            refined = client.generate(system_prompt, user_msg, backend_config, llm_cfg)
            
            if refined and not isinstance(refined, dict) and not refined.startswith("⚠️"):
                cleaned = refined.strip().strip('"').strip("'")
                return jsonify({"ok": True, "refined": cleaned})
                
            return jsonify({"ok": False, "error": "LLM returned empty or error"})
            
        except Exception as exc:
            logger.error(f"[WebUI] refine_media_prompt error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    # ── Preset System ──────────────────────────────────────────────────────────

    @app.route("/hecos/api/media/presets", methods=["GET"])
    def list_media_presets():
        """Returns all preset names (built-in + user) with metadata."""
        try:
            from hecos.plugins.image_gen.presets import BUILTIN_PRESETS
            from hecos.core.media_config import get_media_config
            media_cfg = get_media_config()
            user_presets = media_cfg.get("image_gen", {}).get("presets", {})
            result = []
            for name, data in BUILTIN_PRESETS.items():
                result.append({"name": name, "builtin": True,
                    "description": data.get("_description", ""),
                    "provider": data.get("provider", ""), "model": data.get("model", "")})
            for name, data in user_presets.items():
                result.append({"name": name, "builtin": False,
                    "description": data.get("_description", "User preset"),
                    "provider": data.get("provider", ""), "model": data.get("model", "")})
            return jsonify({"ok": True, "presets": result})
        except Exception as exc:
            logger.error(f"[WebUI] list_media_presets error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/hecos/api/media/presets/load/<path:name>", methods=["GET"])
    def load_media_preset(name):
        """Returns the full config dict for a named preset."""
        try:
            from hecos.plugins.image_gen.presets import get_preset
            from hecos.core.media_config import get_media_config
            user_presets = get_media_config().get("image_gen", {}).get("presets", {})
            preset = get_preset(name, user_presets)
            if preset is None:
                return jsonify({"ok": False, "error": f"Preset '{name}' not found"}), 404
            clean = {k: v for k, v in preset.items() if not k.startswith("_")}
            return jsonify({"ok": True, "name": name, "config": clean})
        except Exception as exc:
            logger.error(f"[WebUI] load_media_preset error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/hecos/api/media/presets/save", methods=["POST"])
    def save_media_preset():
        """Saves the current config as a named user preset."""
        try:
            data = request.json or {}
            name = data.get("name", "").strip()
            config_snapshot = data.get("config", {})
            if not name:
                return jsonify({"ok": False, "error": "Preset name is required"}), 400
            from hecos.plugins.image_gen.presets import save_user_preset
            ok = save_user_preset(name, config_snapshot)
            return jsonify({"ok": ok, "name": name})
        except Exception as exc:
            logger.error(f"[WebUI] save_media_preset error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/hecos/api/media/presets/delete/<path:name>", methods=["DELETE"])
    def delete_media_preset(name):
        """Deletes a user preset by name. Built-ins cannot be deleted."""
        try:
            from hecos.plugins.image_gen.presets import delete_user_preset
            ok = delete_user_preset(name)
            if not ok:
                return jsonify({"ok": False, "error": f"Cannot delete '{name}'"}), 400
            return jsonify({"ok": True, "deleted": name})
        except Exception as exc:
            logger.error(f"[WebUI] delete_media_preset error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    # ── Hugging Face Hub Explorer ─────────────────────────────────────────────

    @app.route("/hecos/api/media/hf-search", methods=["GET"])
    def search_huggingface_hub():
        """
        Proxies search requests to the Hugging Face Hub API for text-to-image models.
        Query params: q (search string), limit (default 20).
        """
        try:
            import requests
            query = request.args.get("q", "").strip()
            limit = int(request.args.get("limit", 20))
            
            # API endpoint for searching models
            url = f"https://huggingface.co/api/models?pipeline_tag=text-to-image&sort=downloads&direction=-1&limit={limit}"
            if query:
                import urllib.parse
                url += f"&search={urllib.parse.quote(query)}"
                
            headers = {"User-Agent": "Hecos/0.18.2"}
            from hecos.core.media.image_providers.utils import get_proxies
            prox = get_proxies("huggingface")
            
            r = requests.get(url, headers=headers, timeout=15, proxies=prox)
            if r.status_code != 200:
                logger.error(f"[WebUI] HF Hub API error: {r.status_code} {r.text[:200]}")
                return jsonify({"ok": False, "error": f"HF Hub returned HTTP {r.status_code}"}), 502
                
            data = r.json()
            models = []
            for m in data:
                # Extract interesting tags (architecture/base model)
                raw_tags = m.get("tags", [])
                
                # Filter out LoRAs because standard HF serverless inference cannot run them directly without a base model
                if "lora" in [t.lower() for t in raw_tags]:
                    continue

                if "flux" in raw_tags: arch = "Flux"
                elif "stable-diffusion-xl" in raw_tags: arch = "SDXL"
                elif "stable-diffusion" in raw_tags: arch = "SD 1.5"
                else: arch = "Other"

                # Detect NSFW manually from tags since API field is sometimes unreliable
                is_nsfw = "not-for-all-audiences" in raw_tags or "nsfw" in raw_tags

                models.append({
                    "id": m.get("id"),
                    "author": m.get("author", "unknown"),
                    "downloads": m.get("downloads", 0),
                    "likes": m.get("likes", 0),
                    "arch": arch,
                    "inference_status": m.get("inference", "unknown"),
                    "is_nsfw": is_nsfw,
                    "is_gated": str(m.get("gated", "false")).lower() != "false",
                    "tags": raw_tags[:5] # Send up to 5 tags for UI
                })
            
            return jsonify({"ok": True, "models": models})
        except Exception as exc:
            logger.error(f"[WebUI] search_huggingface_hub error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500
