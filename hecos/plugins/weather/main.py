"""
MODULE: Weather Plugin
DESCRIPTION: Provides real-time weather and forecasting using Open-Meteo API.
"""
import requests
from datetime import datetime
from hecos.core.logging import logger

class WeatherPlugin:
    """
    Hecos Weather Plugin — Fetches live weather and forecasts natively without API keys.
    """
    def __init__(self):
        self.tag = "WEATHER"
        self.desc = "Real-time weather and forecasting using the open-source Open-Meteo API."
        self.status = "ONLINE"
        
        self.config_schema = {
            "default_city": {
                "type": "str",
                "default": "",
                "description": "Fallback city if user context is missing. If empty, uses IP detection."
            }
        }
        self.config_manager = None
        self._ip_cache = None

    def on_load(self, config_manager=None, **kwargs):
        """Called automatically by Hecos ModuleLoader"""
        self.config_manager = config_manager
        
    def _get_active_city(self):
        c_p = ""
        # 1. Config Manager - User Contact Info
        if self.config_manager and hasattr(self.config_manager, 'config'):
            c_p = self.config_manager.config.get("users", {}).get("contact_info", {}).get("city", "")
            if not c_p:
               # 2. Plugin config
               c_p = self.config_manager.config.get("plugins", {}).get("WEATHER", {}).get("default_city", "")
        return c_p.strip()
        
    def _get_location_from_ip(self):
        if self._ip_cache: return self._ip_cache
        try:
            r = requests.get("http://ip-api.com/json/", timeout=5)
            if r.status_code == 200:
                 d = r.json()
                 if d.get("status") == "success":
                     self._ip_cache = {
                         "name": f"{d.get('city', 'Unknown')}, {d.get('country', '')}",
                         "lat": d.get("lat", 0.0),
                         "lon": d.get("lon", 0.0)
                     }
                     return self._ip_cache
        except Exception as e:
            logger.debug("WEATHER", f"IP Geolocation failed: {e}")
        return None

    def _geocode(self, city):
        try:
             # Standard open-meteo geocoding
             r = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json", timeout=5)
             if r.status_code == 200:
                 data = r.json()
                 if data.get("results"):
                     res = data["results"][0]
                     return {
                         "name": f"{res.get('name')}, {res.get('country')}",
                         "lat": res.get("latitude"),
                         "lon": res.get("longitude")
                     }
        except Exception as e:
             logger.debug("WEATHER", f"Geocode failed: {e}")
        return None

    def get_weather_data(self, city=None) -> dict:
        """Fetches unified weather block for the Frontend Widget and Backend Tools."""
        loc = None
        if city:
            loc = self._geocode(city)
        if not loc:
            active_c = self._get_active_city()
            if active_c:
                loc = self._geocode(active_c)
        if not loc:
             loc = self._get_location_from_ip()
             
        if not loc:
            return {"error": "Località sconosciuta. Inserisci la Città nel Profilo Utente."}
            
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={loc['lat']}&longitude={loc['lon']}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m"
            f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset"
            f"&timezone=auto"
        )
        try:
            r = requests.get(url, timeout=5)
            r.raise_for_status()
            data = r.json()
            data["location"] = loc["name"]
            return data
        except Exception as e:
            return {"error": str(e)}

    def _get_wmo_description(self, code):
        mapping = {
            0: "Clear sky",
            1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            56: "Light freezing drizzle", 57: "Dense freezing drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            66: "Light freezing rain", 67: "Heavy freezing rain",
            71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
            77: "Snow grains",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            85: "Slight snow showers", 86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
        }
        return mapping.get(code, f"Unknown code ({code})")

    # ─────────────────────────────────────────────────────────
    # LLM TOOLS EXPOSED TO THE AGENT
    # ─────────────────────────────────────────────────────────

    def get_current_weather(self, city: str = "") -> str:
        """
        Get the current weather conditions for a specific city.
        If city is omitted, uses the user's primary residence.
        """
        data = self.get_weather_data(city)
        if "error" in data:
            return f"Error: {data['error']}"
            
        c = data.get("current", {})
        u = data.get("current_units", {})
        loc = data.get("location", "Unknown Location")
        
        t = c.get("temperature_2m")
        tu = u.get("temperature_2m", "°C")
        h = c.get("relative_humidity_2m")
        hu = u.get("relative_humidity_2m", "%")
        wc = c.get("weather_code", 0)
        
        weather_desc = self._get_wmo_description(wc)
        
        return f"Current weather in {loc}: {t}{tu}, Humidity: {h}{hu}, Condition: {weather_desc}"
        
    def get_weather_forecast(self, city: str = "") -> str:
        """
        Get the daily weather forecast for the next 7 days for a specific city.
        """
        data = self.get_weather_data(city)
        if "error" in data:
            return f"Error: {data['error']}"
            
        daily = data.get("daily", {})
        loc = data.get("location", "Unknown Location")
        
        dates = daily.get("time", [])
        tmax = daily.get("temperature_2m_max", [])
        tmin = daily.get("temperature_2m_min", [])
        wcs = daily.get("weather_code", [])
        
        res = [f"Forecast for {loc}:"]
        for i in range(min(7, len(dates))):
             desc = self._get_wmo_description(wcs[i])
             res.append(f"{dates[i]}: {tmin[i]} - {tmax[i]}°C ({desc})")
             
        return "\n".join(res)


# ── Plugin Interface ──
tools = WeatherPlugin()

def info() -> dict:
    return {
        "tag": "WEATHER",
        "desc": tools.desc
    }

def execute(comando: str) -> str:
    return tools.get_current_weather()
