import os
from zentra.core.media.image_providers.utils import log_debug, save_image_bytes, get_proxies, ensure_english_prompt

class StabilityProvider:
    NAME = "stability"

    @staticmethod
    def get_models() -> list:
        return ["sd3-turbo", "sd3", "stable-image-core", "stable-image-ultra"]

    @staticmethod
    def generate(prompt: str, width: int, height: int, model: str, api_key: str = "",
                 negative_prompt: str = "", guidance_scale: float = 7.5, 
                 num_inference_steps: int = 30) -> str:
        if not api_key:
            api_key = os.environ.get("STABILITY_API_KEY", "").strip()
        if not api_key:
            raise Exception("Stability API key not set. Add STABILITY_API_KEY to .env")

        eng_prompt = ensure_english_prompt(prompt)
        log_debug(f"[Stability] model={model} prompt={eng_prompt[:50]}")

        import requests

        model_lower = model.lower()
        if "sd3" in model_lower:
            endpoint = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
        elif "ultra" in model_lower:
            endpoint = "https://api.stability.ai/v2beta/stable-image/generate/ultra"
        else:
            endpoint = "https://api.stability.ai/v2beta/stable-image/generate/core"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "image/*"
        }
        data = {
            "prompt": eng_prompt,
            "output_format": "jpeg",
        }
        if "sd3" in model_lower:
            data["model"] = "sd3-turbo" if "turbo" in model_lower else "sd3"
            
        # Advanced Parameters
        data["negative_prompt"] = negative_prompt
        data["cfg_scale"] = guidance_scale
        if "ultra" not in model_lower:
            data["aspect_ratio"] = "1:1" # Standard for our UI

        log_debug(f"[Stability] endpoint={endpoint}")
        r = requests.post(endpoint, headers=headers, files={"none": ""}, data=data, timeout=60, proxies=get_proxies())
        log_debug(f"[Stability] HTTP {r.status_code}, bytes={len(r.content)}")

        if r.status_code != 200:
            try:
                err_detail = r.json().get("errors", [r.text[:200]])
            except Exception:
                err_detail = r.text[:200]
            raise Exception(f"Stability HTTP {r.status_code}: {err_detail}")

        if r.content.startswith(b"<!DOCTYPE") or r.content.startswith(b"<html"):
            raise Exception("Stability returned HTML instead of image")

        return save_image_bytes(r.content, "jpg")
