"""Meteomatics data coordinator."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_BASE_URL,
    BASIC_DAILY_FETCH_HOURS,
    DAILY_DAYS,
    DAILY_PARAMETERS_BASIC,
    DAILY_PARAMETERS_PAID_TRIAL,
    DEFAULT_MODEL,
    HOURLY_HOURS,
    HOURLY_PARAMETERS_BASIC,
    HOURLY_PARAMETERS_PAID_TRIAL,
    PLAN_TYPE_BASIC,
    PLAN_TYPE_PAID_TRIAL,
    WEATHER_SYMBOL_MAP,
)


LOGGER = logging.getLogger(__name__)


class MeteomaticsDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch Meteomatics data."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        username: str,
        password: str,
        latitude: float,
        longitude: float,
        update_interval: timedelta,
        plan_type: str = PLAN_TYPE_PAID_TRIAL,
        config_entry: ConfigEntry | None = None,
    ) -> None:
        self._username = username
        self._password = password
        self._latitude = latitude
        self._longitude = longitude
        self._plan_type = plan_type
        self._daily_fetch_hours: tuple[int, ...] | None = (
            BASIC_DAILY_FETCH_HOURS if plan_type == PLAN_TYPE_BASIC else None
        )
        time_zone_name = hass.config.time_zone
        self._time_zone = (
            dt_util.get_time_zone(time_zone_name)
            if time_zone_name
            else dt_util.UTC
        )
        self._rate_limit_reset: datetime | None = None
        self._daily_data: list[dict[str, Any]] = []
        self._next_daily_fetch: datetime | None = None
        self._hourly_symbol_entries: list[tuple[datetime, str | None]] = []
        super().__init__(
            hass,
            LOGGER,
            name="Meteomatics",
            update_interval=update_interval,
            config_entry=config_entry,
        )

    def update_credentials(self, username: str, password: str) -> bool:
        """Update the credentials used for Meteomatics requests."""

        if username == self._username and password == self._password:
            return False

        self._username = username
        self._password = password
        self._rate_limit_reset = None
        return True

    def update_plan_type(self, plan_type: str) -> bool:
        """Update the plan type used for Meteomatics requests."""

        if plan_type == self._plan_type:
            return False

        self._plan_type = plan_type
        self._daily_fetch_hours = (
            BASIC_DAILY_FETCH_HOURS if plan_type == PLAN_TYPE_BASIC else None
        )
        self._next_daily_fetch = None
        self._daily_data = []
        self._rate_limit_reset = None
        return True

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Meteomatics."""
        if self._rate_limit_reset and dt_util.utcnow() < self._rate_limit_reset:
            raise UpdateFailed(
                "Meteomatics rate limit reached; waiting to retry until "
                f"{self._rate_limit_reset.isoformat()}"
            )

        session = async_get_clientsession(self.hass)
        now_local = dt_util.utcnow().astimezone(self._time_zone)
        try:
            current, hourly = await self._fetch_hourly(session)
            daily = await self._ensure_daily_data(session, now_local)
            self._rate_limit_reset = None
        except UpdateFailed:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Error communicating with Meteomatics: {err}") from err

        return {
            "current": current,
            "hourly": hourly,
            "daily": daily,
        }

    async def _fetch_hourly(self, session: aiohttp.ClientSession) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        now = dt_util.utcnow().astimezone(self._time_zone)
        now = now.replace(minute=0, second=0, microsecond=0)
        end = (now + timedelta(hours=HOURLY_HOURS)).astimezone(self._time_zone)
        timerange = f"{self._format_datetime(now)}--{self._format_datetime(end)}:PT1H"
        parameters = ",".join(self._hourly_parameters)

        data = await self._request(session, timerange, parameters)
        parsed = self._parse_response(data)

        current = self._build_current(parsed, now)
        hourly_forecast = self._build_hourly_forecast(parsed)
        self._hourly_symbol_entries = self._extract_hourly_symbol_entries(parsed)
        if self._daily_data:
            self._update_cached_daily_conditions()
        return current, hourly_forecast

    async def _fetch_daily(self, session: aiohttp.ClientSession) -> list[dict[str, Any]]:
        now = dt_util.utcnow().astimezone(self._time_zone)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = (start + timedelta(days=DAILY_DAYS)).astimezone(self._time_zone)
        timerange = f"{self._format_datetime(start)}--{self._format_datetime(end)}:P1D"
        parameters = ",".join(self._daily_parameters)

        data = await self._request(session, timerange, parameters)
        parsed = self._parse_response(data)

        return self._build_daily_forecast(parsed)

    async def _ensure_daily_data(
        self, session: aiohttp.ClientSession, now_local: datetime
    ) -> list[dict[str, Any]]:
        if self._daily_fetch_hours is None:
            daily = await self._fetch_daily(session)
            self._daily_data = daily
            self._next_daily_fetch = None
            return daily

        if (
            not self._daily_data
            or self._next_daily_fetch is None
            or now_local >= self._next_daily_fetch
        ):
            daily = await self._fetch_daily(session)
            self._daily_data = daily
            self._next_daily_fetch = self._calculate_next_daily_fetch(now_local)
            return daily

        self._update_cached_daily_conditions()
        return self._daily_data

    def _calculate_next_daily_fetch(self, reference: datetime) -> datetime:
        assert self._daily_fetch_hours is not None
        hours = sorted(self._daily_fetch_hours)
        for hour in hours:
            candidate = reference.replace(
                hour=hour, minute=0, second=0, microsecond=0
            )
            if candidate > reference:
                return candidate

        next_day = (reference + timedelta(days=1)).replace(
            hour=hours[0], minute=0, second=0, microsecond=0
        )
        return next_day

    async def _request(self, session: aiohttp.ClientSession, timerange: str, parameters: str) -> dict[str, Any]:
        url = f"{API_BASE_URL}/{timerange}/{parameters}/{self._latitude},{self._longitude}/json"
        async with session.get(
            url,
            auth=aiohttp.BasicAuth(self._username, self._password),
            params={"model": DEFAULT_MODEL},
            timeout=30,
        ) as response:
            if response.status == 429:
                self._handle_rate_limit()
            response.raise_for_status()
            return await response.json()

    def _handle_rate_limit(self) -> None:
        self._rate_limit_reset = dt_util.utcnow() + timedelta(hours=1)
        LOGGER.warning(
            "Meteomatics API rate limit reached. Waiting until %s before retrying.",
            self._rate_limit_reset.isoformat(),
        )
        raise UpdateFailed(
            "Meteomatics API rate limit reached. Waiting one hour before retrying."
        )

    def _parse_response(self, data: dict[str, Any]) -> dict[str, dict[str, list[dict[str, Any]]]]:
        parsed: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for parameter in data.get("data", []):
            param_name = parameter.get("parameter")
            if not param_name:
                continue
            coordinates = parameter.get("coordinates", [])
            if not coordinates:
                continue
            dates = coordinates[0].get("dates", [])
            parsed[param_name] = {"dates": dates}
        return parsed

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        return value.isoformat(timespec="seconds")

    def _build_current(self, parsed: dict[str, dict[str, list[dict[str, Any]]]], now: datetime) -> dict[str, Any]:
        current_time = now.replace(minute=0, second=0, microsecond=0)
        temperature = self._value_at(parsed, "t_2m:C", current_time)
        humidity = self._value_at(parsed, "relative_humidity_2m:p", current_time)
        pressure = self._value_at(parsed, "msl_pressure:hPa", current_time)
        wind_speed = self._value_at(parsed, "wind_speed_10m:ms", current_time)
        wind_bearing = self._value_at(parsed, "wind_dir_10m:d", current_time)
        condition = WEATHER_SYMBOL_MAP.get(
            int(self._value_at(parsed, "weather_symbol_1h:idx", current_time) or 0),
        )
        wind_gust = self._value_at(parsed, "wind_gusts_10m_1h:ms", current_time)
        uv_index = self._value_at(parsed, "uv:idx", current_time)

        return {
            "temperature": temperature,
            "humidity": humidity,
            "pressure": pressure,
            "wind_speed": wind_speed,
            "wind_bearing": wind_bearing,
            "condition": condition,
            "wind_gust": wind_gust,
            "uv_index": uv_index,
        }

    def _build_hourly_forecast(self, parsed: dict[str, dict[str, list[dict[str, Any]]]]) -> list[dict[str, Any]]:
        hourly: list[dict[str, Any]] = []
        for entry in parsed.get("t_2m:C", {}).get("dates", []):
            dt = self._parse_time(entry.get("date"))
            if dt is None:
                continue
            condition = WEATHER_SYMBOL_MAP.get(
                int(self._value_at(parsed, "weather_symbol_1h:idx", dt) or 0),
            )
            hourly.append(
                {
                    "datetime": dt,
                    "temperature": entry.get("value"),
                    "condition": condition,
                    "precipitation": self._value_at(parsed, "precip_1h:mm", dt),
                    "pressure": self._value_at(parsed, "msl_pressure:hPa", dt),
                    "wind_speed": self._value_at(parsed, "wind_speed_10m:ms", dt),
                    "wind_bearing": self._value_at(parsed, "wind_dir_10m:d", dt),
                    "humidity": self._value_at(parsed, "relative_humidity_2m:p", dt),
                    "wind_gust": self._value_at(parsed, "wind_gusts_10m_1h:ms", dt),
                    "uv_index": self._value_at(parsed, "uv:idx", dt),
                    "precipitation_24h": self._value_at(parsed, "precip_24h:mm", dt),
                    "wind_gust_24h": self._value_at(
                        parsed, "wind_gusts_10m_24h:ms", dt
                    ),
                }
            )
        return hourly

    def _build_daily_forecast(self, parsed: dict[str, dict[str, list[dict[str, Any]]]]) -> list[dict[str, Any]]:
        daily: list[dict[str, Any]] = []
        for entry in parsed.get("t_max_2m_24h:C", {}).get("dates", []):
            dt = self._parse_time(entry.get("date"))
            if dt is None:
                continue
            condition = self._infer_daily_condition(dt)
            daily.append(
                {
                    "datetime": dt,
                    "temperature": entry.get("value"),
                    "templow": self._value_at(parsed, "t_min_2m_24h:C", dt),
                    "condition": condition,
                    "precipitation": self._value_at(parsed, "precip_24h:mm", dt),
                    "wind_speed": self._value_at(parsed, "wind_speed_10m:ms", dt),
                    "wind_bearing": self._value_at(parsed, "wind_dir_10m:d", dt),
                    "wind_gust": self._value_at(parsed, "wind_gusts_10m_24h:ms", dt),
                    "pressure": self._value_at(parsed, "msl_pressure:hPa", dt),
                    "uv_index": self._value_at(parsed, "uv:idx", dt),
                    "sunrise": self._value_at(parsed, "sunrise:sql", dt),
                    "sunset": self._value_at(parsed, "sunset:sql", dt),
                }
            )
        return daily

    def _extract_hourly_symbol_entries(
        self, parsed: dict[str, dict[str, list[dict[str, Any]]]]
    ) -> list[tuple[datetime, str | None]]:
        entries: list[tuple[datetime, str | None]] = []
        for item in parsed.get("weather_symbol_1h:idx", {}).get("dates", []):
            dt = self._parse_time(item.get("date"))
            if dt is None:
                continue
            value = item.get("value")
            symbol: str | None = None
            if value is not None:
                try:
                    symbol = WEATHER_SYMBOL_MAP.get(int(value))
                except (TypeError, ValueError):
                    symbol = None
            entries.append((dt, symbol))
        return entries

    def _infer_daily_condition(self, day_start: datetime) -> str | None:
        if not self._hourly_symbol_entries:
            return None

        day_end = day_start + timedelta(days=1)
        midday = day_start + timedelta(hours=12)
        best_symbol: str | None = None
        best_distance: float | None = None

        for dt, symbol in self._hourly_symbol_entries:
            if symbol is None:
                continue
            if day_start <= dt < day_end:
                distance = abs((dt - midday).total_seconds())
                if best_distance is None or distance < best_distance:
                    best_symbol = symbol
                    best_distance = distance

        return best_symbol

    def _update_cached_daily_conditions(self) -> None:
        if not self._daily_data:
            return

        for entry in self._daily_data:
            dt = entry.get("datetime")
            if isinstance(dt, datetime):
                entry["condition"] = self._infer_daily_condition(dt)

    @property
    def _hourly_parameters(self) -> list[str]:
        if self._plan_type == PLAN_TYPE_BASIC:
            return HOURLY_PARAMETERS_BASIC
        return HOURLY_PARAMETERS_PAID_TRIAL

    @property
    def _daily_parameters(self) -> list[str]:
        if self._plan_type == PLAN_TYPE_BASIC:
            return DAILY_PARAMETERS_BASIC
        return DAILY_PARAMETERS_PAID_TRIAL

    @property
    def plan_type(self) -> str:
        """Return the current plan type."""

        return self._plan_type

    def _value_at(self, parsed: dict[str, dict[str, list[dict[str, Any]]]], parameter: str, target: datetime) -> Any:
        dates = parsed.get(parameter, {}).get("dates", [])
        for item in dates:
            dt = self._parse_time(item.get("date"))
            if dt == target:
                return item.get("value")
        return None

    @staticmethod
    def _parse_time(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
