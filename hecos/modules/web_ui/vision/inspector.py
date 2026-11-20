"""
hecos/modules/web_ui/vision/inspector.py
Vision Bridge / Sidecar Inspector.
Analyzes images using a dedicated multimodal worker (Gemini Cloud or local Ollama vision model)
and produces high-fidelity, objective descriptions for text-only models.
Strictly respects offline boundaries when local mode is selected.
"""
import os
import json
import logging
import base64
from typing import Optional, List

logger = logging.getLogger("hecos.web_ui.vision.inspector")


def _get_system_config() -> dict:
    """Helper to load system.yaml config safely from any context."""
    try:
        from hecos.core.processing import processore
        if getattr(processore, "current_config", None):
            return processore.current_config
    except Exception:
        pass
    try:
        from hecos.core.llm.brain import load_config
        cfg = load_config()
        if cfg:
            return cfg
    except Exception:
        pass
    try:
        import yaml
        root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        path = os.path.join(root, "config", "data", "system.yaml")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    except Exception:
        pass
    return {}


def inspect_image(
    image_dict: dict,
    custom_prompt: Optional[str] = None,
    config: Optional[dict] = None
) -> Optional[str]:
    """
    Analyzes an image and returns an objective textual description.

    Args:
        image_dict: Dict with "data_b64" and optionally "mime_type", "name".
        custom_prompt: Specific prompt to send to the inspector model.
        config: Full vision config dict (from load_vision_config()).

    Returns:
        String description of the image contents, or None if inspection fails.
    """
    if not image_dict or not image_dict.get("data_b64"):
        return None

    if config is None:
        from .config import load_vision_config
        config = load_vision_config()

    bridge_cfg = config.get("bridge", {})
    if not bridge_cfg.get("enabled", True):
        logger.debug("[VisionInspector] Bridge is disabled in config.")
        return None

    mode = bridge_cfg.get("mode", "local_ollama")
    prompt = custom_prompt or bridge_cfg.get(
        "inspection_prompt",
        "Describe in detail and objectively the visual elements of the image: subjects, actions, visible text, colors, setting, and notable details."
    )

    # 1. Active Chat Model Mode
    if mode == "active_model":
        desc = _inspect_via_active_model(image_dict, prompt)
        if desc:
            return desc
        return None

    # 2. Local-Only Mode (STRICT PRIVACY / OFFLINE BOUNDARY — NEVER CALLS CLOUD)
    if mode == "local_ollama":
        logger.info("[VisionInspector] Running in STRICT LOCAL OFFLINE mode (cloud calls forbidden).")
        return _inspect_via_ollama(image_dict, prompt, bridge_cfg)

    # 3. Cloud-Only Mode
    if mode == "cloud":
        return _inspect_via_cloud(image_dict, prompt, bridge_cfg)

    # 4. Auto Mode: try Local first; fallback to Cloud ONLY if no local model resolves.
    # If the active chat model is a local Ollama model, 'auto' stays local-only
    # to respect offline boundaries and avoid unexpected cloud calls.
    if mode == "auto":
        local_m = bridge_cfg.get("local_model", "default")
        # Resolve "default" to the active Ollama model from system config
        if local_m in ("default", None, ""):
            cfg = _get_system_config()
            local_m = (cfg.get("backend") or {}).get("ollama", {}).get("model", "")

        active_source = (_get_system_config().get("backend") or {}).get("active_model_source", "ollama")

        if local_m and local_m != "disabled":
            desc = _inspect_via_ollama(image_dict, prompt, {**bridge_cfg, "local_model": local_m})
            if desc:
                return desc
            # Local failed — only fallback to cloud if explicitly using cloud chat
            if active_source != "cloud":
                logger.warning(
                    "[VisionInspector] Auto mode: local Ollama inspection failed. "
                    "Cloud fallback suppressed (active model is local). "
                    "Hint: install a vision-capable Ollama model or switch mode to 'cloud'."
                )
                return None

        # Cloud fallback (only if active_model_source=cloud or no local model configured)
        logger.info("[VisionInspector] Auto mode: falling back to cloud inspector.")
        return _inspect_via_cloud(image_dict, prompt, bridge_cfg)

    return None


def _inspect_via_active_model(image_dict: dict, prompt: str) -> Optional[str]:
    """Inspects image using the current active model configured in chat."""
    try:
        from app.model_manager import ModelManager
        cfg = _get_system_config()
        btype, active_m = ModelManager.get_effective_model_info(cfg)
        logger.info(f"[VisionInspector] Inspecting via active chat model: '{active_m}' ({btype})")

        if btype in ("cloud", "hybrid") or ("/" in active_m and not btype == "ollama"):
            return _inspect_via_cloud(image_dict, prompt, {"cloud_model": active_m})
        else:
            return _inspect_via_ollama(image_dict, prompt, {"local_model": active_m})
    except Exception as e:
        logger.warning(f"[VisionInspector] Failed inspecting via active chat model: {e}")
        return None


def _inspect_via_cloud(image_dict: dict, prompt: str, bridge_cfg: dict) -> Optional[str]:
    """Inspects image using LiteLLM cloud model (e.g. gemini/gemini-2.5-flash)."""
    model_name = bridge_cfg.get("cloud_model", "gemini/gemini-2.5-flash")
    if model_name == "default":
        cfg = _get_system_config()
        model_name = (cfg.get("backend") or {}).get("cloud", {}).get("model") or "gemini/gemini-2.5-flash"

    provider = model_name.split("/")[0] if "/" in model_name else "gemini"

    try:
        from hecos.core.keys import get_key_manager
        km = get_key_manager()
        api_key = km.get_key(provider)
        if not api_key and provider != "gemini":
            api_key = km.get_key("openai")
        if not api_key:
            logger.debug(f"[VisionInspector] No API key for cloud inspector '{provider}' in KeyManager.")
            return None

        os.environ["LITELLM_LOG"] = "WARNING"
        import litellm
        from hecos.core.logging.logger import sync_litellm_loggers
        sync_litellm_loggers()

        b64 = image_dict["data_b64"]
        mime = image_dict.get("mime_type", "image/jpeg")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"}
                    }
                ]
            }
        ]

        logger.info(f"[VisionInspector] Calling cloud vision inspector: model={model_name}")
        resp = litellm.completion(
            model=model_name,
            messages=messages,
            api_key=api_key,
            temperature=0.2,
            timeout=35
        )

        choice = resp.choices[0] if getattr(resp, "choices", None) else None
        if choice:
            finish_reason = getattr(choice, "finish_reason", None)
            if finish_reason == "content_filter":
                logger.warning(
                    f"[VisionInspector] Cloud model '{model_name}' BLOCKED the image: "
                    f"finish_reason='content_filter'. (The image contains NSFW/nudity/content rejected by the cloud provider's safety filter)."
                )
                return None

            content = getattr(choice.message, "content", None)
            if content and len(content.strip()) > 10:
                logger.info(f"[VisionInspector] Cloud inspection succeeded ({len(content)} chars)")
                return content.strip()

    except Exception as e:
        logger.warning(f"[VisionInspector] Cloud inspection failed: {e}")

    return None



# ---------------------------------------------------------------------------
# Known text-only / vision-capable model families for Ollama pre-flight check
# ---------------------------------------------------------------------------
# NOTE: _TEXT_ONLY_KEYWORDS is kept for documentation only — the heuristic
# now uses _VISION_KEYWORDS as a whitelist plus a runtime Ollama probe.
_TEXT_ONLY_KEYWORDS = (
    "mistral", "qwen", "phi", "deepseek", "vicuna",
    "wizard", "orca", "falcon", "mpt", "starcoder", "codellama",
    "solar", "yi", "command-r", "nous", "hermes",
)
_VISION_KEYWORDS = (
    # Dedicated vision model families
    "llava", "moondream", "bakllava", "cogvlm", "minicpm-v",
    "llama3.2-vision", "llama-3.2-vision", "qwen2-vl", "qwen-vl",
    "internvl", "phi3-vision", "phi-3-vision", "janus", "pixtral",
    "mistvision", "bunny", "idefics",
    # Gemma 4+ supports multimodal natively (confirmed via Ollama API test)
    "gemma-4", "gemma4",
    # Gemma 3 (some variants are multimodal)
    "gemma-3", "gemma3",
    # llama 3.2 / 4 general (vision variants)
    "llama-4", "llama4",
)

# Models explicitly tested and confirmed vision-capable at runtime.
# Add entries here to bypass the keyword heuristic (namespace/tag stripped).
_RUNTIME_CONFIRMED_VISION_MODELS: set = set()


def _is_ollama_model_vision_capable(model_name: str) -> bool:
    """
    Heuristic: returns True if the model name matches a known vision-capable
    family. Strips namespace prefixes (e.g. 'masska129/gemma-4-abliterated:12b-qat').

    Gemma-4 and newer multi-modal models that may carry text-only-looking
    name fragments (abliterated, uncensored, etc.) are now correctly identified
    by the base model family keyword (gemma-4, gemma4, llama-4…).
    """
    name_lower = model_name.lower()
    # Strip namespace (e.g. 'masska129/...' → '...')
    if "/" in name_lower:
        name_lower = name_lower.split("/", 1)[-1]
    # Strip tag (e.g. 'gemma-4-abliterated:12b-qat' → 'gemma-4-abliterated')
    base = name_lower.split(":")[0]

    # Check runtime confirmed set first
    if base in _RUNTIME_CONFIRMED_VISION_MODELS:
        return True

    # Vision-capable keyword whitelist
    for kw in _VISION_KEYWORDS:
        if kw in base:
            return True

    return False


def _inspect_via_ollama(image_dict: dict, prompt: str, bridge_cfg: dict) -> Optional[str]:
    """Inspects image using a local Ollama multimodal model."""
    model_name = bridge_cfg.get("local_model", "default")
    cfg = _get_system_config()

    if model_name == "default":
        model_name = (cfg.get("backend") or {}).get("ollama", {}).get("model") or "moondream"

    # Pre-flight: skip text-only models immediately to avoid 30-60s timeout
    if not _is_ollama_model_vision_capable(model_name):
        logger.warning(
            f"[VisionInspector] Model '{model_name}' is text-only — cannot process images. "
            f"Hint: Install a vision-capable model (moondream, llava, llama3.2-vision) or "
            f"switch Inspector Mode to 'cloud' or 'auto' in the Multimodal Perception settings."
        )
        return None

    try:
        import requests
        ollama_url = (cfg.get("backend") or {}).get("ollama", {}).get("url") or "http://localhost:11434"
        gen_url = f"{ollama_url.rstrip('/')}/api/generate"

        payload = {
            "model": model_name,
            "prompt": prompt,
            "images": [image_dict["data_b64"]],
            "stream": False,
            "options": {"temperature": 0.2}
        }
        logger.info(f"[VisionInspector] Calling local Ollama vision inspector: model={model_name} url={gen_url}")
        resp = requests.post(gen_url, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            response_text = data.get("response", "").strip()
            if response_text and len(response_text) > 10:
                logger.info(f"[VisionInspector] Local Ollama inspection succeeded ({len(response_text)} chars)")
                return response_text
        elif resp.status_code == 400:
            logger.warning(
                f"[VisionInspector] Ollama 400 for model '{model_name}' — "
                f"model likely does not support multimodal input. Raw: {resp.text[:200]}"
            )
        else:
            logger.warning(f"[VisionInspector] Ollama returned status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"[VisionInspector] Local Ollama inspection failed: {e}")

    return None
