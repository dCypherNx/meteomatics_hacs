"""Constants for the Meteomatics integration."""

from __future__ import annotations

DOMAIN = "meteomatics"

# Update cadence is fixed per plan. The free/basic plan is limited to
# one request every 20 minutes, which we also use as the default cadence
# for the paid plan unless a future requirement specifies otherwise.
DEFAULT_UPDATE_INTERVAL_MINUTES = 20

CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_PLAN_TYPE = "plan_type"

PLAN_TYPE_BASIC = "basic"
PLAN_TYPE_PAID_TRIAL = "paid_trial"

PLAN_TYPE_OPTIONS = {
    PLAN_TYPE_BASIC: "Basic",
    PLAN_TYPE_PAID_TRIAL: "Paid/Trial",
}

API_BASE_URL = "https://api.meteomatics.com"
DEFAULT_MODEL = "mix"

HOURLY_HOURS = 24
DAILY_DAYS = 10

# Parameter sets for each plan type. The basic plan follows the
# restrictions from the free tier documentation, while the paid/trial plan
# retains additional data that remains available.
HOURLY_PARAMETERS_BASIC = [
    "t_2m:C",
    "precip_1h:mm",
    "wind_speed_10m:ms",
    "wind_dir_10m:d",
    "wind_gusts_10m_1h:ms",
    "msl_pressure:hPa",
    "uv:idx",
    "weather_symbol_1h:idx",
    "precip_24h:mm",
    "wind_gusts_10m_24h:ms",
]

HOURLY_PARAMETERS_PAID_TRIAL = [
    "t_2m:C",
    "precip_1h:mm",
    "wind_speed_10m:ms",
    "wind_dir_10m:d",
    "wind_gusts_10m_1h:ms",
    "msl_pressure:hPa",
    "uv:idx",
    "weather_symbol_1h:idx",
    "precip_24h:mm",
    "wind_gusts_10m_24h:ms",
    "relative_humidity_2m:p",
]

DAILY_PARAMETERS_BASIC = [
    "t_max_2m_24h:C",
    "t_min_2m_24h:C",
    "precip_24h:mm",
    "wind_gusts_10m_24h:ms",
    "wind_speed_10m:ms",
    "wind_dir_10m:d",
    "msl_pressure:hPa",
    "uv:idx",
    "sunrise:sql",
    "sunset:sql",
    "weather_symbol_24h:idx",
]

DAILY_PARAMETERS_PAID_TRIAL = [
    "t_max_2m_24h:C",
    "t_min_2m_24h:C",
    "precip_24h:mm",
    "wind_gusts_10m_24h:ms",
    "wind_speed_10m:ms",
    "wind_dir_10m:d",
    "msl_pressure:hPa",
    "uv:idx",
    "sunrise:sql",
    "sunset:sql",
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
