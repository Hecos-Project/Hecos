"""
weather_pro — Plugin AI
═══════════════════════════════════════════════════════════════
Hecos hybrid plugin: exposes weather data to the AI agent
AND serves live data to the weather_pro_widget via HTTP API.

Uses Open-Meteo (free, no API key required).
"""
from __future__ import annotations

import requests

from hecos.core.logging import logger


class WeatherProPlugin:
    """
    Hybrid weather plugin for Hecos.

    Exposed to the AI agent as:
        WEATHER_PRO__get_current_weather(city?)
        WEATHER_PRO__get_weather_forecast(city?)

    Also called directly by the weather_pro_widget extension routes
    to serve /api/weather_pro/data without duplicating logic.
    """

    tag = "WEATHER_PRO"
    desc = "Real-time weather data and 7-day forecast via Open-Meteo. No API key required."

    def __init__(self):
        self.config_manager = None
        self._ip_cache = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_load(self, config_manager=None, **kwargs):
        self.config_manager = config_manager
        logger.info("WEATHER_PRO", "Plugin loaded.")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_active_city(self) -> str:
        """Priority: user profile city → plugin config → empty string."""
        # 1. User profile (AuthManager)
        try:
            from hecos.core.auth.auth_manager import auth_mgr
            profile = auth_mgr.get_profile("admin")
            if profile and profile.get("city"):
                return profile["city"].strip()
        except Exception as e:
            logger.debug("WEATHER_PRO", f"AuthManager lookup failed: {e}")

        # 2. Plugin config default_city
        if self.config_manager and hasattr(self.config_manager, "config"):
            city = (
                self.config_manager.config
                .get("plugins", {})
                .get("WEATHER_PRO", {})
                .get("default_city", "")
            )
            if city:
                return city.strip()

        return ""

    def _get_units(self) -> str:
        """Return 'celsius' or 'fahrenheit' from plugin config."""
        if self.config_manager and hasattr(self.config_manager, "config"):
            return (
                self.config_manager.config
                .get("plugins", {})
                .get("WEATHER_PRO", {})
                .get("units", "celsius")
            )
        return "celsius"

    def _get_location_from_ip(self) -> dict | None:
        if self._ip_cache:
            return self._ip_cache
        try:
            r = requests.get("http://ip-api.com/json/", timeout=5)
            if r.status_code == 200:
                d = r.json()
                if d.get("status") == "success":
                    self._ip_cache = {
                        "name": f"{d.get('city', 'Unknown')}, {d.get('country', '')}",
                        "lat": d.get("lat", 0.0),
                        "lon": d.get("lon", 0.0),
                    }
                    return self._ip_cache
        except Exception as e:
            logger.debug("WEATHER_PRO", f"IP geolocation failed: {e}")
        return None

    def _geocode(self, city: str) -> dict | None:
        try:
            r = requests.get(
                f"https://geocoding-api.open-meteo.com/v1/search"
                f"?name={city}&count=1&language=en&format=json",
                timeout=5,
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("results"):
                    res = data["results"][0]
                    return {
                        "name": f"{res.get('name')}, {res.get('country')}",
                        "lat": res.get("latitude"),
                        "lon": res.get("longitude"),
                    }
        except Exception as e:
            logger.debug("WEATHER_PRO", f"Geocode failed: {e}")
        return None

    def _resolve_location(self, city: str = "") -> dict | None:
        """Resolve to {name, lat, lon} with full fallback chain."""
        if city:
            loc = self._geocode(city)
            if loc:
                return loc
        active = self._get_active_city()
        if active:
            loc = self._geocode(active)
            if loc:
                return loc
        return self._get_location_from_ip()

    @staticmethod
    def _wmo_description(code: int) -> str:
        mapping = {
            0: "Clear sky",
            1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
            77: "Snow grains",
            80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
            85: "Slight snow showers", 86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
        }
        return mapping.get(code, f"Unknown ({code})")

    # ── Core data method (shared with widget API route) ───────────────────────

    def get_weather_data(self, city: str = "") -> dict:
        """
        Returns the full Open-Meteo JSON payload enriched with:
          - location: str  (resolved city name)
          - error: str     (only on failure)

        Called by both LLM tools and the widget HTTP endpoint.
        """
        loc = self._resolve_location(city)
        if not loc:
            return {"error": "Location unknown. Set a city in your User Profile."}

        units_param = "celsius" if self._get_units() != "fahrenheit" else "fahrenheit"
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={loc['lat']}&longitude={loc['lon']}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
            f"is_day,precipitation,weather_code,wind_speed_10m"
            f"&daily=weather_code,temperature_2m_max,temperature_2m_min,"
            f"precipitation_probability_max,sunrise,sunset"
            f"&temperature_unit={units_param}"
            f"&timezone=auto"
        )
        try:
            r = requests.get(url, timeout=6)
            r.raise_for_status()
            data = r.json()
            data["location"] = loc["name"]
            data["units"] = units_param
            return data
        except Exception as e:
            logger.warning("WEATHER_PRO", f"Fetch failed: {e}")
            return {"error": str(e)}

    # ── LLM Tool Methods ──────────────────────────────────────────────────────

    def get_current_weather(self, city: str = "") -> str:
        """
        Get the current weather conditions for a specific city.
        If city is omitted, uses the user's profile city or IP geolocation.
        """
        data = self.get_weather_data(city)
        if "error" in data:
            return f"Error: {data['error']}"

        c = data.get("current", {})
        u = data.get("current_units", {})
        loc = data.get("location", "Unknown")

        temp = c.get("temperature_2m")
        temp_u = u.get("temperature_2m", "°C")
        humidity = c.get("relative_humidity_2m")
        wind = c.get("wind_speed_10m")
        wind_u = u.get("wind_speed_10m", "km/h")
        apparent = c.get("apparent_temperature")
        wcode = c.get("weather_code", 0)
        desc = self._wmo_description(wcode)

        return (
            f"Current weather in {loc}:\n"
            f"  🌡️  Temperature: {temp}{temp_u} (feels like {apparent}{temp_u})\n"
            f"  💧 Humidity: {humidity}%\n"
            f"  💨 Wind: {wind} {wind_u}\n"
            f"  ⛅ Condition: {desc}"
        )

    def get_weather_forecast(self, city: str = "") -> str:
        """
        Get a 7-day daily weather forecast for a specific city.
        """
        data = self.get_weather_data(city)
        if "error" in data:
            return f"Error: {data['error']}"

        daily = data.get("daily", {})
        loc = data.get("location", "Unknown")
        u_label = "°F" if data.get("units") == "fahrenheit" else "°C"

        dates = daily.get("time", [])
        tmax = daily.get("temperature_2m_max", [])
        tmin = daily.get("temperature_2m_min", [])
        wcs = daily.get("weather_code", [])
        prec = daily.get("precipitation_probability_max", [])

        lines = [f"7-day forecast for {loc}:"]
        for i in range(min(7, len(dates))):
            desc = self._wmo_description(wcs[i])
            rain = prec[i] if i < len(prec) else "?"
            lines.append(
                f"  {dates[i]}: {tmin[i]}–{tmax[i]}{u_label}  {desc}  🌧 {rain}%"
            )
        return "\n".join(lines)


# ── Plugin interface ───────────────────────────────────────────────────────────
tools = WeatherProPlugin()


def info() -> dict:
    return {"tag": tools.tag, "desc": tools.desc}


def execute(comando: str) -> str:
    return tools.get_current_weather()
