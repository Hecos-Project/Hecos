"""
MODULE: MAP Plugin — Hecos GPS & Geolocation
DESCRIPTION: Provides geocoding and home-location tools using Nominatim (OpenStreetMap).
             Zero API keys required. Exposes LLM tools and backend data for the map_widget.
"""
import requests
from hecos.core.logging import logger


class MapPlugin:
    """
    Hecos GPS Map Plugin.
    Geocodes addresses via Nominatim (OSM) and retrieves the user's home position
    from their profile (city + address fields).
    """

    def __init__(self):
        self.tag = "MAP"
        self.icon = "🗺️"
        self.desc = "Geocoding e geolocalizzazione tramite OpenStreetMap (Nominatim)"
        self.status = "ONLINE"

        # Simple in-memory cache: query_string -> {lat, lon, display_name}
        self._geocode_cache: dict = {}

        self.config_schema = {
            "default_zoom": {
                "type": "int",
                "default": 13,
                "description": "Default zoom level for the map widget (1-19)."
            },
            "geocode_provider": {
                "type": "str",
                "default": "nominatim",
                "description": "Geocoding provider. Currently only 'nominatim' is supported."
            }
        }

    def on_load(self, config_manager=None, **kwargs):
        """Called automatically by Hecos ModuleLoader."""
        self.config_manager = config_manager

    # ─────────────────────────────────────────────────────────
    # GEOCODING
    # ─────────────────────────────────────────────────────────

    def geocode(self, query: str) -> dict:
        """
        Geocode a free-text address or city name using Nominatim (OpenStreetMap).
        Returns a dict with lat, lon, display_name — or an 'error' key on failure.
        Results are cached in-memory to avoid repeated API calls.
        """
        q = query.strip()
        if not q:
            return {"error": "Empty query provided to geocode."}

        if q in self._geocode_cache:
            logger.debug("MAP", f"Geocode cache hit: {q}")
            return self._geocode_cache[q]

        try:
            headers = {"User-Agent": "Hecos-AI-Assistant/1.0 (https://hecos-project.github.io/)"}
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": q,
                "format": "json",
                "limit": 1,
                "addressdetails": 0
            }
            r = requests.get(url, params=params, headers=headers, timeout=8)
            r.raise_for_status()
            results = r.json()
            if results:
                res = results[0]
                location = {
                    "lat": float(res["lat"]),
                    "lon": float(res["lon"]),
                    "display_name": res.get("display_name", q)
                }
                self._geocode_cache[q] = location
                logger.debug("MAP", f"Geocoded '{q}' → lat={location['lat']}, lon={location['lon']}")
                return location
            else:
                return {"error": f"Nessun risultato per: {q}"}
        except Exception as e:
            logger.debug("MAP", f"Geocode error for '{q}': {e}")
            return {"error": str(e)}

    def _build_home_query(self, profile: dict) -> str:
        """Builds the best possible geocoding query from the user profile."""
        parts = []
        address = (profile.get("address") or "").strip()
        city = (profile.get("city") or "").strip()
        if address:
            parts.append(address)
        if city:
            parts.append(city)
        return ", ".join(parts)

    def get_home_location(self, username: str = "admin") -> dict:
        """
        Returns the geographic coordinates for the user's home address.
        Reads city + address from the user profile (AuthManager), then geocodes.
        """
        try:
            from hecos.core.auth.auth_manager import auth_mgr
            profile = auth_mgr.get_profile(username)
        except Exception as e:
            logger.debug("MAP", f"AuthManager unavailable: {e}")
            profile = {}

        query = self._build_home_query(profile)

        if not query:
            return {
                "error": "Nessun indirizzo home trovato nel profilo. "
                         "Configura 'città' o 'indirizzo' nel profilo utente."
            }

        result = self.geocode(query)
        if "error" not in result:
            result["source"] = "profile"
            result["query"] = query
        return result

    # ─────────────────────────────────────────────────────────
    # LLM TOOLS EXPOSED TO THE AGENT
    # ─────────────────────────────────────────────────────────

    def MAP__get_home_location(self, username: str = "admin") -> str:
        """Get the lat/lon of the user's home, derived from their profile."""
        result = self.get_home_location(username)
        if "error" in result:
            return f"❌ {result['error']}"
        return (
            f"📍 Home location for '{username}':\n"
            f"  Address: {result.get('display_name')}\n"
            f"  Latitude: {result.get('lat')}\n"
            f"  Longitude: {result.get('lon')}"
        )

    def MAP__geocode(self, query: str) -> str:
        """Geocode a free-text address or city name."""
        result = self.geocode(query)
        if "error" in result:
            return f"❌ Geocoding failed: {result['error']}"
        return (
            f"📍 Location: {result.get('display_name')}\n"
            f"  Latitude: {result.get('lat')}\n"
            f"  Longitude: {result.get('lon')}"
        )


# ── Plugin Interface ──
tools = MapPlugin()


def info() -> dict:
    return {
        "tag": tools.tag,
        "icon": tools.icon,
        "desc": tools.desc,
    }


def execute(comando: str) -> str:
    return tools.MAP__get_home_location()
