"""Constants for the Meteomatics integration."""

from __future__ import annotations

DOMAIN = "meteomatics"

# Update cadence is limited by the free/basic plan which allows one request
# every 20 minutes. We therefore keep a single default cadence for all
# installations.
DEFAULT_UPDATE_INTERVAL_MINUTES = 20

CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"

API_BASE_URL = "https://api.meteomatics.com"
DEFAULT_MODEL = "mix"

HOURLY_HOURS = 24
DAILY_DAYS = 9

# The free/basic plan exposes a total of 15 parameters but limits each
# request to 10 parameters. We split the data set between an hourly fetch,
# which is deliberately more verbose, and a complementary daily fetch.
MAX_PARAMETERS_PER_REQUEST = 10

HOURLY_PARAMETERS = [
    "t_2m:C",
    "msl_pressure:hPa",
    "wind_speed_10m:ms",
    "wind_dir_10m:d",
    "wind_gusts_10m_1h:ms",
    "uv:idx",
    "weather_symbol_1h:idx",
    "precip_1h:mm",
    "precip_24h:mm",
]

DAILY_PARAMETERS = [
    "t_max_2m_24h:C",
    "t_min_2m_24h:C",
    "wind_gusts_10m_24h:ms",
    "sunrise:sql",
    "sunset:sql",
    "wind_speed_10m:ms",
    "wind_dir_10m:d",
    "uv:idx",
    "precip_24h:mm",
    "weather_symbol_24h:idx",
]

BASIC_DAILY_FETCH_HOURS = (3, 9, 15, 21)

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
