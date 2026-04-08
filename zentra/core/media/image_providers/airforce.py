import urllib.parse
from core.media.image_providers.utils import log_debug, save_image_bytes, get_proxies, ensure_english_prompt

class AirforceProvider:
    NAME = "airforce"

    @staticmethod
    def get_models() -> list:
        return ["flux"]

    @staticmethod
    def generate(prompt: str, width: int, height: int, model: str, api_key: str = "") -> str:
        """Generate image via Airforce free API."""
        eng_prompt = ensure_english_prompt(prompt)
        import requests
        encoded = urllib.parse.quote(eng_prompt)
        url = f"https://api.airforce/v1/imagine2?model={model}&prompt={encoded}"
        log_debug(f"[Airforce] URL: {url}")
        
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=45, proxies=get_proxies(AirforceProvider.NAME))
        
        if r.status_code != 200:
            raise Exception(f"Airforce HTTP {r.status_code}")
            
        if r.content.startswith(b"<!DOCTYPE") or r.content.startswith(b"<html"):
            raise Exception("Airforce returned HTML")
            
        return save_image_bytes(r.content, "jpg")
