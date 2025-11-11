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

# Map Meteomatics weather symbols (aligned with WMO weather codes as documented
# in https://www.meteomatics.com/en/api/available-parameters/weather-parameter/general-weather-state/#weather_symb)
# to Home Assistant weather conditions.
_BASE_WEATHER_SYMBOL_MAP = {
    **dict.fromkeys((0, 1), "sunny"),
    2: "partlycloudy",
    **dict.fromkeys((3, 4), "cloudy"),
    5: "fog",
    **dict.fromkeys((6, 7, 8, 9), "exceptional"),
    **dict.fromkeys((10, 11, 12), "fog"),
    13: "lightning",
    **dict.fromkeys((14, 15, 16, 17, 18, 19), "partlycloudy"),
    **dict.fromkeys((20, 21), "rainy"),
    22: "snowy",
    23: "snowy-rainy",
    24: "rainy",
    25: "rainy",
    26: "snowy",
    **dict.fromkeys((27, 28), "hail"),
    29: "lightning",
    **dict.fromkeys((30, 31, 32, 33, 34, 35, 36), "windy"),
    **dict.fromkeys((37, 38, 39), "snowy"),
    **dict.fromkeys((40, 41, 42, 43, 44, 45, 46, 47, 48, 49), "fog"),
    **dict.fromkeys((50, 51, 52, 53, 54, 55), "rainy"),
    **dict.fromkeys((56, 57, 58, 59), "snowy-rainy"),
    **dict.fromkeys((60, 61, 62, 63), "rainy"),
    **dict.fromkeys((64, 65), "pouring"),
    **dict.fromkeys((66, 67, 68, 69), "snowy-rainy"),
    **dict.fromkeys((70, 71, 72, 73, 74, 75, 76, 77, 78), "snowy"),
    79: "snowy-rainy",
    **dict.fromkeys((80, 81), "rainy"),
    82: "pouring",
    **dict.fromkeys((83, 84), "snowy-rainy"),
    **dict.fromkeys((85, 86), "snowy"),
    **dict.fromkeys((87, 88, 89, 90), "hail"),
    91: "rainy",
    92: "pouring",
    **dict.fromkeys((93, 94), "snowy-rainy"),
    **dict.fromkeys((95, 96, 97, 98, 99), "lightning-rainy"),
}

# Meteomatics documents that weather symbols above 100 repeat the same weather
# states with alternative icon variants that are used at night. We therefore map
# them to the same Home Assistant conditions, except for explicitly mapping the
# daytime "sunny" condition to the night-time "clear-night" equivalent.
_NIGHT_CONDITION_MAP = {
    "sunny": "clear-night",
}

WEATHER_SYMBOL_MAP = {
    **_BASE_WEATHER_SYMBOL_MAP,
    **{
        symbol + 100: _NIGHT_CONDITION_MAP.get(condition, condition)
        for symbol, condition in _BASE_WEATHER_SYMBOL_MAP.items()
    },
}

ATTRIBUTION = "Weather data provided by Meteomatics"
