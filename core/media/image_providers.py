"""
core/media/image_providers.py
Multi-provider image generation engine for Zentra Core.
Providers: Pollinations (free), Gemini, OpenAI DALL-E, Stability.ai
"""
import os
import uuid
import urllib.parse
import datetime

try:
    from core.logging import logger
except ImportError:
    class _Logger:
        def info(self, *a): print("[IMGPROVIDER]", *a)
        def error(self, *a): print("[IMGPROVIDER ERROR]", *a)
        def debug(self, *a): pass
    logger = _Logger()

OUTPUT_DIR = "data/images"

def _log_debug(msg: str):
    log_file = "logs/image_gen_debug.txt"
    now = datetime.datetime.now().strftime("%H:%M:%S")
    try:
        os.makedirs("logs", exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{now}] {msg}\n")
    except Exception:
        pass

def _save_image_bytes(data: bytes, ext: str = "jpg") -> str:
    """Save raw image bytes to data/images/ and return filename."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"gen_{uuid.uuid4().hex[:8]}.{ext}"
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "wb") as f:
        f.write(data)
    return filename

def _get_proxies(provider: str = "") -> dict:
    """
    Read proxy configuration from SYS_NET plugin settings.
    Bypass proxy for free APIs (Pollinations/Airforce) to avoid timeouts over Tor.
    """
    if provider in ["pollinations", "airforce"]:
        return {}
        
    try:
        from app.config import ConfigManager
        cfg = ConfigManager()
        proxy_url = cfg.get_plugin_config("SYS_NET", "proxy_url", "").strip()
        if proxy_url:
            return {"http": proxy_url, "https": proxy_url}
    except Exception as e:
        _log_debug(f"[Engine] Proxy config error: {e}")
    return {}


def _ensure_english_prompt(prompt: str) -> str:
    """
    Translates prompt to English using googletrans (lightweight).
    Falls back to original prompt if translation fails.
    Required for providers that only accept English (Stability, OpenAI).
    """
    try:
        from googletrans import Translator
        t = Translator()
        detected = t.detect(prompt)
        if detected and detected.lang and detected.lang != 'en':
            result = t.translate(prompt, dest='en')
            translated = result.text
            _log_debug(f"[Engine] Auto-translated prompt: '{prompt[:40]}' -> '{translated[:40]}'")
            return translated
    except ImportError:
        pass  # googletrans not installed, try Google translate via requests
    except Exception as e:
        _log_debug(f"[Engine] Auto-translate error: {e}")

    # Fallback: use Google Translate unofficial API via requests (no key needed)
    try:
        import requests as _req
        enc = urllib.parse.quote(prompt)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q={enc}"
        r = _req.get(url, timeout=5, proxies=_get_proxies())
        if r.status_code == 200:
            data = r.json()
            translated = "".join([item[0] for item in data[0] if item[0]])
            if translated and translated.lower() != prompt.lower():
                _log_debug(f"[Engine] Auto-translated (API): '{prompt[:40]}' -> '{translated[:40]}'")
                return translated
    except Exception as e2:
        _log_debug(f"[Engine] Google Translate API fallback error: {e2}")

    return prompt  # Return original if all translation fails


# ── 1. Pollinations (Free, no key required) ──────────────────────────────────

class PollinationsProvider:
    NAME = "pollinations"
    MODELS_URL = "https://image.pollinations.ai/models"

    @staticmethod
    def get_models() -> list:
        """Fetch model list from Pollinations API dynamically."""
        try:
            import requests
            r = requests.get(PollinationsProvider.MODELS_URL, timeout=5, proxies=_get_proxies(PollinationsProvider.NAME))
            if r.status_code == 200:
                data = r.json()
                # API returns a list of model names or dicts
                if isinstance(data, list):
                    return [m if isinstance(m, str) else m.get("name", str(m)) for m in data]
        except Exception as e:
            _log_debug(f"Pollinations model fetch failed: {e}")
        # Static fallback
        return ["flux", "flux-pro", "turbo", "midjourney", "flux-realism"]

    @staticmethod
    def generate(prompt: str, width: int, height: int, model: str, api_key: str = "") -> str:
        """Returns filename on success, raises Exception on failure."""
        import requests
        encoded = urllib.parse.quote(prompt.strip())
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width={width}&height={height}&model={model}&nologo=true"
        )
        _log_debug(f"[Pollinations] URL: {url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        }
        # ONLY add key if the user explicitly provided one (paid tier)
        if api_key and len(api_key) > 20:
            headers["Authorization"] = f"Bearer {api_key}"

        r = requests.get(url, headers=headers, timeout=30, proxies=_get_proxies(PollinationsProvider.NAME))
        _log_debug(f"[Pollinations] HTTP {r.status_code}, bytes={len(r.content)}")

        if r.status_code != 200:
            raise Exception(f"Pollinations HTTP {r.status_code}")
        if r.content.startswith(b"<!DOCTYPE") or r.content.startswith(b"<html"):
            raise Exception(f"Pollinations returned HTML (not an image)")

        return _save_image_bytes(r.content, "jpg")


# ── 2. Google Gemini Imagen ────────────────────────────────────────────────────

class GeminiProvider:
    NAME = "gemini"

    @staticmethod
    def get_models() -> list:
        return ["imagen-3.0-generate-001", "imagen-4.0"]

    @staticmethod
    def generate(prompt: str, width: int, height: int, model: str, api_key: str = "") -> str:
        """Generate image via Google Gemini Imagen. Uses imagen models only."""
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise Exception("Gemini API key not set. Add GEMINI_API_KEY to .env")

        # Translate to English (Gemini Imagen works best with English prompts)
        eng_prompt = _ensure_english_prompt(prompt)
        _log_debug(f"[Gemini] model={model} prompt={eng_prompt[:50]}")

        try:
            import requests

            # Ensure a valid Gemini image model
            # (If user forgot to refresh models in UI and 'stable-image-core' is still selected)
            if "imagen" not in model:
                model = "imagen-3.0-generate-001"
            
            if model == "imagen-3.0-generate-002":
                model = "imagen-3.0-generate-001"

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict?key={api_key}"
            
            payload = {
                "instances": [{"prompt": eng_prompt}],
                "parameters": {"sampleCount": 1}
            }
            headers = {"Content-Type": "application/json"}

            r = requests.post(url, json=payload, headers=headers, timeout=60, proxies=_get_proxies())
            
            _log_debug(f"[Gemini] HTTP {r.status_code}, bytes={len(r.content)}")

            if r.status_code != 200:
                try:
                    err_msg = r.json().get("error", {}).get("message", r.text[:200])
                except:
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
            img_bytes = base64.b64decode(b64_img)
            return _save_image_bytes(img_bytes, "png")

        except Exception as e:
            raise Exception(f"Gemini API Error: {e}")


# ── 2b. Google Gemini Native (generateContent with image modality) ─────────────

class GeminiNativeProvider:
    """
    Uses the standard Gemini generateContent API with responseModalities: ["IMAGE"].
    Works with a standard AI Studio API key — no Vertex AI needed.
    Supported models: gemini-2.0-flash-preview-image-generation, etc.
    """
    NAME = "gemini_native"

    @staticmethod
    def get_models() -> list:
        return [
            "gemini-2.0-flash-preview-image-generation",
            "gemini-2.0-flash-exp-image-generation",
        ]

    @staticmethod
    def generate(prompt: str, width: int, height: int, model: str, api_key: str = "") -> str:
        """Generate image via Gemini generateContent with IMAGE modality."""
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise Exception("Gemini API key not set. Add GEMINI_API_KEY to .env")

        import requests
        import base64

        eng_prompt = _ensure_english_prompt(prompt)
        _log_debug(f"[GeminiNative] model={model} prompt={eng_prompt[:60]}")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": eng_prompt}]}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
        }
        headers = {"Content-Type": "application/json"}

        r = requests.post(url, json=payload, headers=headers, timeout=60, proxies=_get_proxies())
        _log_debug(f"[GeminiNative] HTTP {r.status_code}, bytes={len(r.content)}")

        if r.status_code != 200:
            try:
                err_msg = r.json().get("error", {}).get("message", r.text[:200])
            except Exception:
                err_msg = r.text[:200]
            raise Exception(f"GeminiNative HTTP {r.status_code}: {err_msg}")

        data = r.json()
        # Parse response: image data is in parts with inlineData
        try:
            candidates = data.get("candidates", [])
            for candidate in candidates:
                for part in candidate.get("content", {}).get("parts", []):
                    inline = part.get("inlineData", {})
                    if inline.get("mimeType", "").startswith("image/"):
                        img_bytes = base64.b64decode(inline["data"])
                        ext = inline["mimeType"].split("/")[-1].replace("jpeg", "jpg")
                        return _save_image_bytes(img_bytes, ext)
        except Exception as parse_err:
            raise Exception(f"GeminiNative response parse error: {parse_err}")

        raise Exception("GeminiNative: nessuna immagine trovata nella risposta")


# ── 3. OpenAI DALL-E ──────────────────────────────────────────────────────────

class OpenAIProvider:
    NAME = "openai"

    @staticmethod
    def get_models() -> list:
        return ["dall-e-3", "dall-e-2"]

    @staticmethod
    def generate(prompt: str, width: int, height: int, model: str, api_key: str = "") -> str:
        """Generate image via OpenAI DALL-E API."""
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise Exception("OpenAI API key not set. Add OPENAI_API_KEY to .env")

        _log_debug(f"[OpenAI] model={model} prompt={prompt[:50]}")

        try:
            import openai
            import requests as req_lib
            import base64
            import httpx

            proxies = _get_proxies()
            if proxies and "http" in proxies:
                http_client = httpx.Client(proxies=proxies["http"])
                client = openai.OpenAI(api_key=api_key, http_client=http_client)
            else:
                client = openai.OpenAI(api_key=api_key)

            # DALL-E 3 supports 1024x1024, DALL-E 2 up to 1024x1024
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
            return _save_image_bytes(img_bytes, "png")

        except ImportError:
            raise Exception("openai not installed. Run: pip install openai")


# ── 4. Stability.ai ───────────────────────────────────────────────────────────

class StabilityProvider:
    NAME = "stability"

    @staticmethod
    def get_models() -> list:
        return ["sd3-turbo", "sd3", "stable-image-core", "stable-image-ultra"]

    @staticmethod
    def generate(prompt: str, width: int, height: int, model: str, api_key: str = "") -> str:
        """
        Generate image via Stability.ai v2beta API.
        All endpoints return binary image data directly — no JSON parsing needed.
        """
        if not api_key:
            api_key = os.environ.get("STABILITY_API_KEY", "").strip()
        if not api_key:
            raise Exception("Stability API key not set. Add STABILITY_API_KEY to .env")

        # Translate to English (Stability.ai only supports English)
        eng_prompt = _ensure_english_prompt(prompt)
        _log_debug(f"[Stability] model={model} prompt={eng_prompt[:50]}")

        import requests

        model_lower = model.lower()
        if "sd3" in model_lower:
            endpoint = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
        elif "ultra" in model_lower:
            endpoint = "https://api.stability.ai/v2beta/stable-image/generate/ultra"
        else:
            # Default: stable-image-core (fast, affordable)
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

        _log_debug(f"[Stability] endpoint={endpoint}")
        r = requests.post(endpoint, headers=headers, files={"none": ""}, data=data, timeout=60, proxies=_get_proxies())
        _log_debug(f"[Stability] HTTP {r.status_code}, bytes={len(r.content)}")

        if r.status_code != 200:
            try:
                err_detail = r.json().get("errors", [r.text[:200]])
            except Exception:
                err_detail = r.text[:200]
            raise Exception(f"Stability HTTP {r.status_code}: {err_detail}")

        if r.content.startswith(b"<!DOCTYPE") or r.content.startswith(b"<html"):
            raise Exception("Stability returned HTML instead of image")

        return _save_image_bytes(r.content, "jpg")


# ── 5. Airforce (Free API) ──────────────────────────────────────────────────────

class AirforceProvider:
    NAME = "airforce"

    @staticmethod
    def get_models() -> list:
        return ["flux"]

    @staticmethod
    def generate(prompt: str, width: int, height: int, model: str, api_key: str = "") -> str:
        """Generate image via Airforce free API."""
        eng_prompt = _ensure_english_prompt(prompt)
        import requests
        encoded = urllib.parse.quote(eng_prompt)
        # Using the known working endpoint from legacy plugin
        url = f"https://api.airforce/v1/imagine2?model={model}&prompt={encoded}"
        _log_debug(f"[Airforce] URL: {url}")
        
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=45, proxies=_get_proxies(AirforceProvider.NAME))
        
        if r.status_code != 200:
            raise Exception(f"Airforce HTTP {r.status_code}")
            
        if r.content.startswith(b"<!DOCTYPE") or r.content.startswith(b"<html"):
            raise Exception("Airforce returned HTML")
            
        return _save_image_bytes(r.content, "jpg")

# ── Registry & Engine ─────────────────────────────────────────────────────────

PROVIDERS = {
    "pollinations":   PollinationsProvider,
    "gemini":         GeminiProvider,
    "gemini_native":  GeminiNativeProvider,
    "openai":         OpenAIProvider,
    "stability":      StabilityProvider,
    "airforce":       AirforceProvider,
}


def get_models_for_provider(provider_name: str) -> list:
    """Return the model list for a given provider. Fetches dynamically if possible."""
    cls = PROVIDERS.get(provider_name.lower())
    if cls:
        try:
            return cls.get_models()
        except Exception as e:
            logger.error(f"[ImageEngine] Model list error for {provider_name}: {e}")
    return []


def generate_image(prompt: str, provider: str, model: str, width: int, height: int, api_key: str) -> str:
    """
    Main entry point. Returns the filename of the saved image.
    Tries active provider first, then Pollinations free as fallback.
    Raises Exception if everything fails.
    """
    provider = provider.lower()
    cls = PROVIDERS.get(provider)

    _log_debug(f"[ImageEngine] START provider={provider} model={model} prompt={prompt[:60]}")

    if cls:
        try:
            filename = cls.generate(prompt, width, height, model, api_key)
            _log_debug(f"[ImageEngine] SUCCESS via {provider} → {filename}")
            return filename
        except Exception as e:
            _log_debug(f"[ImageEngine] {provider} failed: {e}")
            logger.error(f"[ImageEngine] {provider} failed: {e}. No automatic fallback.")
            raise Exception(f"{provider.capitalize()} failed to generate image: {e}")

    # If the provider is not mapped in our image PROVIDERS dict (e.g., groq, anthropic)
    raise Exception(f"Il provider '{provider}' non possiede un motore nativo per la generazione di immagini. Selezionare un provider compatibile (es. OpenAI, Gemini Native, Pollinations).")
