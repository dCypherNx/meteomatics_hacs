"""Constants for the Meteomatics integration."""

from __future__ import annotations

DOMAIN = "meteomatics"
DEFAULT_UPDATE_INTERVAL = 30  # minutes
MIN_UPDATE_INTERVAL = 15
MAX_UPDATE_INTERVAL = 180

CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_PLAN_TYPE = "plan_type"
CONF_BASIC_OPTIONAL_PARAMETERS = "basic_optional_parameters"

PLAN_TYPE_BASIC = "basic"
PLAN_TYPE_PAID_TRIAL = "paid_trial"

PLAN_TYPE_OPTIONS = {
    PLAN_TYPE_BASIC: "Basic",
    PLAN_TYPE_PAID_TRIAL: "Paid/Trial",
}

API_BASE_URL = "https://api.meteomatics.com"
DEFAULT_MODEL = "mix"

HOURLY_HOURS = 24
DAILY_DAYS = 7

HOURLY_PARAMETERS_PAID_TRIAL = [
    "t_2m:C",
    "weather_symbol_1h:idx",
    "wind_speed_10m:ms",
    "wind_dir_10m:d",
    "msl_pressure:hPa",
    "precip_1h:mm",
    "wind_gusts_10m_1h:ms",
    "relative_humidity_2m:p",
]

DAILY_PARAMETERS_PAID_TRIAL = [
    "t_max_2m_24h:C",
    "t_min_2m_24h:C",
    "weather_symbol_24h:idx",
    "precip_24h:mm",
    "wind_speed_10m:ms",
    "wind_gusts_10m_24h:ms",
]

BASIC_OPTIONAL_PARAMETER_LIMIT = 5

BASIC_FIXED_PARAMETERS_BY_SCOPE = {
    "hourly": (
        "t_2m:C",
        "precip_1h:mm",
    ),
    "daily": (
        "t_max_2m_24h:C",
        "t_min_2m_24h:C",
        "precip_24h:mm",
    ),
}

BASIC_OPTIONAL_PARAMETER_SCOPES = {
    "wind_speed_10m:ms": {"hourly", "daily"},
    "wind_dir_10m:d": {"hourly"},
    "wind_gusts_10m_1h:ms": {"hourly"},
    "wind_gusts_10m_24h:ms": {"daily"},
    "msl_pressure:hPa": {"hourly"},
    "weather_symbol_1h:idx": {"hourly"},
    "weather_symbol_24h:idx": {"daily"},
    "uv:idx": {"hourly"},
    "sunrise:sql": {"daily"},
    "sunset:sql": {"daily"},
}

BASIC_OPTIONAL_PARAMETER_LABELS = {
    "wind_speed_10m:ms": {
        "default": "Wind speed at 10m",
        "pt-BR": "Velocidade do vento a 10m",
    },
    "wind_dir_10m:d": {
        "default": "Wind direction at 10m",
        "pt-BR": "Direção do vento a 10m",
    },
    "wind_gusts_10m_1h:ms": {
        "default": "Wind gusts at 10m (1h)",
        "pt-BR": "Rajadas de vento a 10m (1h)",
    },
    "wind_gusts_10m_24h:ms": {
        "default": "Wind gusts at 10m (24h)",
        "pt-BR": "Rajadas de vento a 10m (24h)",
    },
    "msl_pressure:hPa": {
        "default": "Mean sea level pressure",
        "pt-BR": "Pressão ao nível do mar",
    },
    "weather_symbol_1h:idx": {
        "default": "Weather symbol (1h)",
        "pt-BR": "Símbolo do tempo (1h)",
    },
    "weather_symbol_24h:idx": {
        "default": "Weather symbol (24h)",
        "pt-BR": "Símbolo do tempo (24h)",
    },
    "uv:idx": {
        "default": "UV index",
        "pt-BR": "Índice UV",
    },
    "sunrise:sql": {
        "default": "Sunrise",
        "pt-BR": "Nascer do sol",
    },
    "sunset:sql": {
        "default": "Sunset",
        "pt-BR": "Pôr do sol",
    },
}

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
