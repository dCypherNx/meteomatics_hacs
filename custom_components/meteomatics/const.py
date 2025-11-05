"""Constants for the Meteomatics integration."""

from __future__ import annotations

DOMAIN = "meteomatics"
DEFAULT_UPDATE_INTERVAL = 30  # minutes
MIN_UPDATE_INTERVAL = 15
MAX_UPDATE_INTERVAL = 180

CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_UPDATE_INTERVAL = "update_interval"

API_BASE_URL = "https://api.meteomatics.com"

HOURLY_HOURS = 24
DAILY_DAYS = 7

WEATHER_SYMBOL_MAP = {
    1: "sunny",
    2: "partlycloudy",
    3: "partlycloudy",
    4: "cloudy",
    5: "fog",
    6: "rainy",
    7: "rainy",
    8: "rainy",
    9: "rainy",
    10: "rainy",
    11: "snowy",
    12: "snowy",
    13: "snowy",
    14: "snowy",
    15: "snowy",
    16: "hail",
    17: "lightning",
    18: "lightning-rainy",
    19: "tornado",
    20: "windy",
    21: "windy-variant",
    22: "exceptional",
}

ATTRIBUTION = "Weather data provided by Meteomatics"
