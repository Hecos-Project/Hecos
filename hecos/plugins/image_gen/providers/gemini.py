import os
from .utils import log_debug, save_image_bytes, get_proxies, ensure_english_prompt


class GeminiProvider:
    NAME = "gemini"

    @staticmethod
    def get_models() -> list:
        return ["imagen-3.0-generate-001", "imagen-4.0"]

    @staticmethod
    def generate(prompt: str, width: int, height: int, model: str, api_key: str = "",
                 negative_prompt: str = "", guidance_scale: float = 7.5,
                 num_inference_steps: int = 30, seed: int = -1,
                 sampler: str = "", scheduler: str = "") -> str:
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise Exception("Gemini API key not set. Add GEMINI_API_KEY to .env")

        eng_prompt = ensure_english_prompt(prompt)
        log_debug(f"[Gemini] model={model} prompt={eng_prompt[:50]}")

        import requests
        if "imagen" not in model:
            model = "imagen-3.0-generate-001"
        if model == "imagen-3.0-generate-002":
            model = "imagen-3.0-generate-001"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict?key={api_key}"
        payload = {"instances": [{"prompt": eng_prompt}], "parameters": {"sampleCount": 1}}
        r = requests.post(url, json=payload, headers={"Content-Type": "application/json"},
                          timeout=60, proxies=get_proxies())
        log_debug(f"[Gemini] HTTP {r.status_code}")

        if r.status_code != 200:
            try:
                err_msg = r.json().get("error", {}).get("message", r.text[:200])
            except Exception:
                err_msg = r.text[:200]
            raise Exception(f"Gemini HTTP {r.status_code}: {err_msg}")

        data = r.json()
        predictions = data.get("predictions", [])
        if not predictions:
            raise Exception("Gemini returned zero predictions")
        b64_img = predictions[0].get("bytesBase64Encoded")
        if not b64_img:
            raise Exception("Gemini response missing bytesBase64Encoded data")

        import base64
        return save_image_bytes(base64.b64decode(b64_img), "png", prompt=prompt,
                                params={"provider": "gemini", "model": model})


class GeminiNativeProvider:
    NAME = "gemini_native"

    @staticmethod
    def get_models() -> list:
        return [
            "gemini-2.0-flash-preview-image-generation",
            "gemini-2.0-flash-exp-image-generation",
        ]

    @staticmethod
    def generate(prompt: str, width: int, height: int, model: str, api_key: str = "",
                 negative_prompt: str = "", guidance_scale: float = 7.5,
                 num_inference_steps: int = 30, seed: int = -1,
                 sampler: str = "", scheduler: str = "") -> str:
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise Exception("Gemini API key not set. Add GEMINI_API_KEY to .env")

        import requests, base64
        eng_prompt = ensure_english_prompt(prompt)
        log_debug(f"[GeminiNative] model={model} prompt={eng_prompt[:60]}")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": eng_prompt}]}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
        }
        r = requests.post(url, json=payload, headers={"Content-Type": "application/json"},
                          timeout=60, proxies=get_proxies())
        log_debug(f"[GeminiNative] HTTP {r.status_code}")

        if r.status_code != 200:
            try:
                err_msg = r.json().get("error", {}).get("message", r.text[:200])
            except Exception:
                err_msg = r.text[:200]
            raise Exception(f"GeminiNative HTTP {r.status_code}: {err_msg}")

        data = r.json()
        for candidate in data.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                inline = part.get("inlineData", {})
                if inline.get("mimeType", "").startswith("image/"):
                    ext = inline["mimeType"].split("/")[-1].replace("jpeg", "jpg")
                    return save_image_bytes(base64.b64decode(inline["data"]), ext,
                                           prompt=prompt, params={"provider": "gemini_native", "model": model})

        raise Exception("GeminiNative: no image found in response")
