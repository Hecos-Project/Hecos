import os
from zentra.core.media.image_providers.utils import log_debug, save_image_bytes, get_proxies

class OpenAIProvider:
    NAME = "openai"

    @staticmethod
    def get_models() -> list:
        return ["dall-e-3", "dall-e-2"]

    @staticmethod
    def generate(prompt: str, width: int, height: int, model: str, api_key: str = "",
                 negative_prompt: str = "", guidance_scale: float = 7.5, 
                 num_inference_steps: int = 30) -> str:
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise Exception("OpenAI API key not set. Add OPENAI_API_KEY to .env")

        log_debug(f"[OpenAI] model={model} prompt={prompt[:50]}")

        try:
            import openai
            import base64
            import httpx

            proxies = get_proxies()
            if proxies and "http" in proxies:
                http_client = httpx.Client(proxies=proxies["http"])
                client = openai.OpenAI(api_key=api_key, http_client=http_client)
            else:
                client = openai.OpenAI(api_key=api_key)

            size_map = {
                (1024, 1024): "1024x1024",
                (1792, 1024): "1792x1024",
                (1024, 1792): "1024x1792",
                (512, 512):   "512x512",
                (256, 256):   "256x256",
            }
            size_key = (width, height)
            size_str = size_map.get(size_key, "1024x1024")

            response = client.images.generate(
                model=model,
                prompt=prompt,
                size=size_str,
                n=1,
                response_format="b64_json"
            )
            img_bytes = base64.b64decode(response.data[0].b64_json)
            return save_image_bytes(img_bytes, "png", prompt=prompt)

        except ImportError:
            raise Exception("openai not installed. Run: pip install openai")
