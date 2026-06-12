"""
weather_tools.py
Implements the two agent tools:
  - get_current_weather(location)
  - get_weather_forecast(location, days)
Uses Open-Meteo (free, no API key required) + geocoding.
"""

import httpx
from typing import Any

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES: dict[int, str] = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Heavy thunderstorm with hail",
}

WMO_ICONS: dict[int, str] = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌧️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "❄️", 75: "❄️",
    80: "🌦️", 81: "🌧️", 82: "⛈️",
    85: "🌨️", 86: "❄️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}


async def geocode_location(location: str) -> tuple[float, float, str, str]:
    """Geocode a city name to lat/lon. Returns (lat, lon, resolved_name, country)."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(GEOCODING_URL, params={
            "name": location,
            "count": 1,
            "language": "en",
            "format": "json",
        })
        resp.raise_for_status()
        data = resp.json()

    if not data.get("results"):
        raise ValueError(f"Location '{location}' not found. Please try a different city name.")

    result = data["results"][0]
    return (
        result["latitude"],
        result["longitude"],
        result.get("name", location),
        result.get("country", ""),
    )


async def get_current_weather(location: str) -> dict[str, Any]:
    """
    Tool: get_current_weather
    Fetches real-time weather for a given city.
    Returns structured weather data.
    """
    lat, lon, city_name, country = await geocode_location(location)

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(WEATHER_URL, params={
            "latitude": lat,
            "longitude": lon,
            "current": [
                "temperature_2m",
                "apparent_temperature",
                "relative_humidity_2m",
                "wind_speed_10m",
                "wind_direction_10m",
                "precipitation",
                "weather_code",
                "uv_index",
                "surface_pressure",
                "visibility",
            ],
            "wind_speed_unit": "kmh",
            "timezone": "auto",
        })
        resp.raise_for_status()
        data = resp.json()

    current = data.get("current", {})
    code = current.get("weather_code", 0)

    return {
        "type": "current_weather",
        "location": f"{city_name}, {country}",
        "latitude": lat,
        "longitude": lon,
        "timezone": data.get("timezone", "UTC"),
        "temperature_c": current.get("temperature_2m"),
        "feels_like_c": current.get("apparent_temperature"),
        "humidity_percent": current.get("relative_humidity_2m"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "wind_direction_deg": current.get("wind_direction_10m"),
        "precipitation_mm": current.get("precipitation"),
        "uv_index": current.get("uv_index"),
        "pressure_hpa": current.get("surface_pressure"),
        "visibility_m": current.get("visibility"),
        "condition": WMO_CODES.get(code, "Unknown"),
        "icon": WMO_ICONS.get(code, "🌡️"),
        "weather_code": code,
    }


async def get_weather_forecast(location: str, days: int = 5) -> dict[str, Any]:
    """
    Tool: get_weather_forecast
    Fetches a daily weather forecast (1–7 days) for a given city.
    Returns structured forecast data.
    """
    days = max(1, min(7, days))  # clamp to 1-7
    lat, lon, city_name, country = await geocode_location(location)

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(WEATHER_URL, params={
            "latitude": lat,
            "longitude": lon,
            "daily": [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "apparent_temperature_max",
                "apparent_temperature_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "wind_speed_10m_max",
                "uv_index_max",
                "sunrise",
                "sunset",
            ],
            "forecast_days": days,
            "wind_speed_unit": "kmh",
            "timezone": "auto",
        })
        resp.raise_for_status()
        data = resp.json()

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    forecast_days = []

    for i, date in enumerate(dates):
        code = daily.get("weather_code", [0])[i] if daily.get("weather_code") else 0
        forecast_days.append({
            "date": date,
            "condition": WMO_CODES.get(code, "Unknown"),
            "icon": WMO_ICONS.get(code, "🌡️"),
            "weather_code": code,
            "temp_max_c": daily.get("temperature_2m_max", [None])[i],
            "temp_min_c": daily.get("temperature_2m_min", [None])[i],
            "feels_max_c": daily.get("apparent_temperature_max", [None])[i],
            "feels_min_c": daily.get("apparent_temperature_min", [None])[i],
            "precipitation_mm": daily.get("precipitation_sum", [None])[i],
            "precipitation_probability": daily.get("precipitation_probability_max", [None])[i],
            "wind_speed_max_kmh": daily.get("wind_speed_10m_max", [None])[i],
            "uv_index_max": daily.get("uv_index_max", [None])[i],
            "sunrise": daily.get("sunrise", [None])[i],
            "sunset": daily.get("sunset", [None])[i],
        })

    return {
        "type": "weather_forecast",
        "location": f"{city_name}, {country}",
        "latitude": lat,
        "longitude": lon,
        "days_requested": days,
        "forecast": forecast_days,
    }
