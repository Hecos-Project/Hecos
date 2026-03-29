import urllib.parse
try:
    from core.logging import logger
    from core.i18n import translator
    from app.config import ConfigManager
except ImportError:
    class DummyLogger:
        def error(self, *args): print("[IMAGE_GEN_ERR]", *args)
    logger = DummyLogger()
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()
    class DummyConfig:
        def get_plugin_config(self, tag, key, default): return default
    def FakeConfigManager(): return DummyConfig()
    ConfigManager = FakeConfigManager

class ImageGenTools:
    """
    Plugin: Image Generation
    Allows generating images from external AI servers (e.g. Pollinations.ai).
    """

    def __init__(self):
        self.tag = "IMAGE_GEN"
        self.desc = "Genera immagini da prompt testuali tramite server esterni."
        self.status = "ONLINE"
        
        self.config_schema = {
            "width": {
                "type": "int",
                "default": 1024,
                "description": "Larghezza dell'immagine generata (in pixel)"
            },
            "height": {
                "type": "int",
                "default": 1024,
                "description": "Altezza dell'immagine generata (in pixel)"
            },
            "nologo": {
                "type": "bool",
                "default": True,
                "description": "Rimuove il watermark/logo di Pollinations.ai"
            },
            "api_key": {
                "type": "string",
                "default": "",
                "description": "API Key obbligatoria per Pollinations.ai (previene l'errore 401)"
            }
        }

    def generate_image(self, prompt: str) -> str:
        """
        Generates an image from a text description using an external AI server.
        
        :param prompt: Detailed description of the image to generate.
        """
        log_file = "logs/image_gen_debug.txt"
        with open(log_file, "a", encoding="utf-8") as debug:
            import datetime
            now = datetime.datetime.now().strftime("%H:%M:%S")
            debug.write(f"[{now}] START: {prompt}\n")
            
            try:
                import requests
                import os
                import uuid
                
                cfg = ConfigManager()
                width = cfg.get_plugin_config(self.tag, "width", 1024)
                height = cfg.get_plugin_config(self.tag, "height", 1024)
                nologo = cfg.get_plugin_config(self.tag, "nologo", True)
                
                # First check .env to avoid github leaks, then fallback to config.json
                api_key = os.environ.get("POLLINATIONS_API_KEY", "").strip()
                if not api_key:
                    api_key = cfg.get_plugin_config(self.tag, "api_key", "").strip()
                
                directory = "data/images"
                if not os.path.exists(directory):
                    os.makedirs(directory)
                
                filename = f"gen_{uuid.uuid4().hex[:8]}.jpg"
                file_path = os.path.join(directory, filename)
                
                # Clean and encode the prompt
                clean_prompt = prompt.strip().replace('\n', ' ').replace('[', '').replace(']', '')
                encoded_prompt = urllib.parse.quote(clean_prompt)
                
                # Try the primary URL
                image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo={nologo}"
                
                # Professional headers
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                    "Referer": "https://pollinations.ai/"
                }
                
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                
                debug.write(f"[{now}] URL: {image_url}\n")
                
                response = requests.get(image_url, headers=headers, timeout=30)
                
                # Validation: check if it's REALLY an image and not HTML error page
                is_html = response.content.startswith(b"<!DOCTYPE") or response.content.startswith(b"<html")
                
                if response.status_code == 200 and not is_html:
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    
                    file_size = len(response.content)
                    debug.write(f"[{now}] SUCCESS. Saved {file_size} bytes as {filename}\n")
                    return f"Risultato: **{clean_prompt}**\n\n[[IMG:{filename}]]"
                
                # Fallback 1: Airforce (Attempt only if Pollinations fails)
                debug.write(f"[{now}] Pollinations failed ({response.status_code}). Trying Airforce...\n")
                airforce_url = f"https://api.airforce/v1/imagine2?prompt={encoded_prompt}"
                response = requests.get(airforce_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
                is_html_af = response.content.startswith(b"<!DOCTYPE") or response.content.startswith(b"<html")
                
                if response.status_code == 200 and not is_html_af:
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    debug.write(f"[{now}] SUCCESS with Airforce.\n")
                    return f"Risultato (Airforce): **{clean_prompt}**\n\n[[IMG:{filename}]]"
                
                # Fallback 2: Simple Pollinations prompt
                debug.write(f"[{now}] ERROR {response.status_code}. Trying simple Pollinations fallback...\n")
                simple_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                response = requests.get(simple_url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    debug.write(f"[{now}] SUCCESS with Simple Fallback.\n")
                    return f"Risultato (simple): **{clean_prompt}**\n\n[[IMG:{filename}]]"
                
                if response.status_code == 401:
                    if api_key:
                         return "⚠️ Errore 401: La API Key di Pollinations fornita in .env è INVALIDA e le API alternative (Airforce) sono offline."
                    else:
                         return "⚠️ Errore 401: Pollinations richiede una API Key (inseriscila nel file .env) e le API di backup sono momentaneamente offline."
                
                debug.write(f"[{now}] ERROR: All attempts failed. Code: {response.status_code}\n")
                return f"⚠️ Errore critico server immagine ({response.status_code}). Tutti i servizi gratuiti sono temporaneamente non disponibili."
                
            except Exception as e:
                debug.write(f"[{now}] CRITICAL ERROR: {str(e)}\n")
                logger.error(f"IMAGE_GEN: Error during generation: {e}")
                return f"⚠️ Errore durante la generazione dell'immagine: {str(e)}"

# Export instance
tools = ImageGenTools()

# Shims for legacy/plugin_loader compatibility
def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status
