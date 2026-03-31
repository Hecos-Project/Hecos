"""
Plugin: Image Generation
Delegates image generation to core/media/image_providers.py (multi-provider engine).
"""
try:
    from core.logging import logger
    from core.media_config import get_media_config
    from core.media.image_providers import generate_image, get_models_for_provider
except ImportError as _e:
    class _DummyLogger:
        def error(self, *a): print("[IMAGE_GEN ERR]", *a)
        def info(self, *a): print("[IMAGE_GEN]", *a)
    logger = _DummyLogger()
    def get_media_config(): return {"image_gen": {}}
    def generate_image(prompt, provider, model, width, height, api_key): raise Exception("Core imports failed")
    def get_models_for_provider(p): return []


class ImageGenTools:
    """
    Plugin: Image Generation
    Generates images from text prompts using external AI services.
    Supports: Pollinations (free), Gemini Imagen, OpenAI DALL-E, Stability.ai
    """

    def __init__(self):
        self.tag = "IMAGE_GEN"
        self.desc = "Generates images from text descriptions using AI image models."
        self.status = "ONLINE"

    def generate_image(self, prompt: str) -> str:
        """
        Generates an image from a text description. Uses the configured provider.
        
        :param prompt: Detailed description of the image to generate.
        """
        import os
        try:
            cfg = get_media_config().get("image_gen", {})
            provider = cfg.get("provider", "pollinations")
            model    = cfg.get("model", "flux")
            width    = int(cfg.get("width", 1024))
            height   = int(cfg.get("height", 1024))
            api_key  = cfg.get("api_key", "").strip()

            # Also check .env for provider-specific key if not in config_media.json
            env_map = {
                "gemini":        "GEMINI_API_KEY",
                "gemini_native": "GEMINI_API_KEY",
                "openai":        "OPENAI_API_KEY",
                "stability":     "STABILITY_API_KEY",
            }
            if not api_key and provider in env_map:
                api_key = os.environ.get(env_map[provider], "").strip()

            logger.info(f"[IMAGE_GEN] Generating via {provider}/{model}: {prompt[:60]}")

            filename = generate_image(prompt, provider, model, width, height, api_key)
            clean_prompt = prompt.strip()[:80]
            return f"Here is the image of **{clean_prompt}**:\n\n[[IMG:{filename}]]"

        except Exception as e:
            logger.error(f"[IMAGE_GEN] Generation failed: {e}")
            return f"⚠️ Image generation failed ({e}). Check that the provider is configured in the Media tab."


# Export instance
tools = ImageGenTools()

def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status
