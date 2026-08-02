import urllib.request
import ssl
from hecos.core.logging import logger

def fetch_readme(url: str) -> str:
    """Downloads a README file from a URL."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(url, headers={"User-Agent": "Hecos-ModuleAwareness"})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        logger.error(f"[ModuleAwareness] Failed to fetch README from {url}: {e}")
        return ""

def parse_readme_features(readme_content: str) -> str:
    """
    Extracts the key features and description from a README markdown file.
    (Simplified implementation for now: returns the first 1000 characters).
    """
    if not readme_content:
        return "No README available."
        
    # In a full implementation, we could look for '## Features' headers,
    # but returning a truncated summary is often enough for the LLM to understand.
    return readme_content[:1500] + ("..." if len(readme_content) > 1500 else "")
