import urllib.request
import json
import ssl
from typing import List, Dict, Any
from hecos.core.logging import logger

def get_store_catalog() -> Dict[str, Any]:
    """
    Fetches the merged catalog from the internal Hecos API loopback if possible,
    or falls back to directly calling the multi-store fetcher function.
    """
    try:
        # First attempt: Call internal function directly if we are in the same python process
        from hecos.modules.web_ui.routes_packages_store import _fetch_remote_catalog, _load_stores
        import os
        
        hecos_src = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "hecos"))
        if not os.path.isdir(hecos_src):
            hecos_src = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

        # We pass None for cfg_mgr, it will fallback to stores.toml
        catalog = _fetch_remote_catalog(None, hecos_src=hecos_src)
        return catalog
    except Exception as e:
        logger.debug(f"[ModuleAwareness] Direct catalog fetch failed: {e}. Trying HTTP loopback.")
        
    # Second attempt: HTTP Loopback to WebUI
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        # WebUI might be on 5000 or from config, but this is harder to guess reliably without app context.
        # Assuming we can't easily guess port, we prefer the direct function call above.
        url = "http://127.0.0.1:5000/api/hpm/store/catalog?refresh=0"
        req = urllib.request.Request(url, headers={"User-Agent": "Hecos-ModuleAwareness"})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok") and "catalog" in data:
                return data["catalog"]
            return {"packages": []}
    except Exception as e:
        logger.error(f"[ModuleAwareness] Failed to fetch store catalog: {e}")
        return {"packages": []}

def search_store(query: str, type_filter: str = None) -> List[Dict[str, Any]]:
    """
    Searches the fetched catalog for modules matching the query.
    """
    catalog = get_store_catalog()
    packages = catalog.get("packages", [])
    
    if type_filter:
        packages = [p for p in packages if p.get("type") == type_filter]
        
    if query:
        query = query.lower()
        def _matches(pkg):
            haystack = " ".join([
                pkg.get("name", ""),
                pkg.get("description", ""),
                pkg.get("author", ""),
                " ".join(pkg.get("tags", []))
            ]).lower()
            return query in haystack
            
        packages = [p for p in packages if _matches(p)]
        
    return packages

def get_store_module_info(module_id: str) -> Dict[str, Any]:
    """Finds a specific module in the store by ID."""
    catalog = get_store_catalog()
    for p in catalog.get("packages", []):
        if p.get("id") == module_id:
            return p
    return {}
