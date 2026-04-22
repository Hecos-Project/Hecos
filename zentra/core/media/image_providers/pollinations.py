import urllib.parse
from zentra.core.media.image_providers.utils import log_debug, save_image_bytes, get_proxies

class PollinationsProvider:
    NAME = "pollinations"
    MODELS_URL = "https://image.pollinations.ai/models"

    @staticmethod
    def get_models() -> list:
        """Fetch model list from Pollinations API dynamically."""
        try:
            import requests
            r = requests.get(PollinationsProvider.MODELS_URL, timeout=5, proxies=get_proxies(PollinationsProvider.NAME))
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    return [m if isinstance(m, str) else m.get("name", str(m)) for m in data]
        except Exception as e:
            log_debug(f"Pollinations model fetch failed: {e}")
        # Static fallback
        return ["flux", "flux-pro", "turbo", "midjourney", "flux-realism"]

    @staticmethod
    def generate(prompt: str, width: int, height: int, model: str, api_key: str = "",
                 negative_prompt: str = "", guidance_scale: float = 7.5,
                 num_inference_steps: int = 30, seed: int = -1,
                 sampler: str = "", scheduler: str = "") -> str:
        """Returns filename on success, raises Exception on failure."""
        import requests
        encoded = urllib.parse.quote(prompt.strip())
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width={width}&height={height}&model={model}&nologo=true"
            f"&negative={urllib.parse.quote(negative_prompt)}"
        )
        # Seed support (Pollinations accepts &seed=N)
        if seed is not None and seed != -1:
            url += f"&seed={seed}"
        log_debug(f"[Pollinations] URL: {url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        }
        if api_key and len(api_key) > 20:
            headers["Authorization"] = f"Bearer {api_key}"

        r = requests.get(url, headers=headers, timeout=30, proxies=get_proxies(PollinationsProvider.NAME))
        log_debug(f"[Pollinations] HTTP {r.status_code}, bytes={len(r.content)}")

        if r.status_code != 200:
            raise Exception(f"Pollinations HTTP {r.status_code}")
        if r.content.startswith(b"<!DOCTYPE") or r.content.startswith(b"<html"):
            raise Exception(f"Pollinations returned HTML (not an image)")

        return save_image_bytes(r.content, "jpg", prompt=prompt, params={
            "provider": "pollinations",
            "model": model,
            "guidance_scale": guidance_scale,
            "inference_steps": num_inference_steps
        })
