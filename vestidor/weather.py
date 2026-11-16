"""Clima vía Open-Meteo (gratis, sin API key)."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import date, timedelta

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "vestidorOM/0.1"

WMO_ES = {
    0: "despejado", 1: "mayormente despejado", 2: "parcialmente nublado", 3: "nublado",
    45: "niebla", 48: "niebla con escarcha",
    51: "llovizna débil", 53: "llovizna", 55: "llovizna intensa", 56: "llovizna helada", 57: "llovizna helada",
    61: "lluvia débil", 63: "lluvia", 65: "lluvia intensa", 66: "lluvia helada", 67: "lluvia helada",
    71: "nieve débil", 73: "nieve", 75: "nieve intensa", 77: "granizo fino",
    80: "chubascos débiles", 81: "chubascos", 82: "chubascos fuertes",
    85: "chubascos de nieve", 86: "chubascos de nieve fuertes",
    95: "tormenta", 96: "tormenta con granizo", 99: "tormenta con granizo",
}

DAY_HOURS = range(9, 21)  # 9:00-20:00, las horas en que llevas la ropa


def _get(url: str, params: dict) -> dict:
    full = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_date(value: str | None) -> date:
    v = (value or "today").strip().lower()
    if v in ("today", "hoy"):
        return date.today()
    if v in ("tomorrow", "mañana", "manana"):
        return date.today() + timedelta(days=1)
    return date.fromisoformat(v)


def geocode(name: str) -> dict:
    data = _get(GEO_URL, {"name": name, "count": 1, "language": "es", "format": "json"})
    results = data.get("results") or []
    if not results:
        raise ValueError(f"No encuentro la ubicación '{name}'")
    r = results[0]
    return {
        "name": r.get("name"),
        "admin": r.get("admin1"),
        "country": r.get("country"),
        "latitude": r["latitude"],
        "longitude": r["longitude"],
        "timezone": r.get("timezone", "auto"),
    }


def forecast(location: dict, day: date) -> dict:
    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "timezone": location.get("timezone", "auto"),
        "hourly": "temperature_2m,apparent_temperature,precipitation_probability,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
        "start_date": day.isoformat(),
        "end_date": day.isoformat(),
    }
    data = _get(FORECAST_URL, params)
    return summarize(data, location, day)


def summarize(data: dict, location: dict, day: date) -> dict:
    hourly = data["hourly"]
    daily = data["daily"]
    idx = [i for i, t in enumerate(hourly["time"]) if int(t[11:13]) in DAY_HOURS]
    feels = [hourly["apparent_temperature"][i] for i in idx if hourly["apparent_temperature"][i] is not None]
    rain = [hourly["precipitation_probability"][i] or 0 for i in idx]
    wind = [hourly["wind_speed_10m"][i] or 0 for i in idx]
    code = daily["weather_code"][0]
    return {
        "date": day.isoformat(),
        "location": location.get("name"),
        "tmin": daily["temperature_2m_min"][0],
        "tmax": daily["temperature_2m_max"][0],
        "feels": round(sum(feels) / len(feels), 1) if feels else daily["temperature_2m_max"][0],
        "feels_min": min(feels) if feels else daily["temperature_2m_min"][0],
        "feels_max": max(feels) if feels else daily["temperature_2m_max"][0],
        "rain_prob": max(rain) if rain else (daily["precipitation_probability_max"][0] or 0),
        "wind_max": max(wind) if wind else 0,
        "code": code,
        "description": WMO_ES.get(code, "desconocido"),
        "source": "open-meteo",
    }


def manual(day: date, feels: float, rain_prob: float = 0, location: str | None = None) -> dict:
    """Clima indicado a mano (sin conexión o para pruebas)."""
    return {
        "date": day.isoformat(), "location": location, "tmin": feels - 4, "tmax": feels + 4,
        "feels": feels, "feels_min": feels - 3, "feels_max": feels + 3, "rain_prob": rain_prob,
        "wind_max": 0, "code": None, "description": "manual", "source": "manual",
    }
