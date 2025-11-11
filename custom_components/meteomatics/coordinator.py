"""Meteomatics data coordinator."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Iterable

import asyncio

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
    DAILY_PARAMETERS,
    DEFAULT_MODEL,
    HOURLY_HOURS,
    HOURLY_PARAMETERS,
    MAX_PARAMETERS_PER_REQUEST,
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
        config_entry: ConfigEntry | None = None,
    ) -> None:
        self._username = username
        self._password = password
        self._latitude = latitude
        self._longitude = longitude
        self._daily_fetch_hours: tuple[int, ...] | None = BASIC_DAILY_FETCH_HOURS
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
        self._latest_hourly_parsed: dict[str, dict[str, list[dict[str, Any]]]] = {}
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

    async def _fetch_hourly(
        self, session: aiohttp.ClientSession
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        now = dt_util.utcnow().astimezone(self._time_zone)
        now = now.replace(minute=0, second=0, microsecond=0)
        end = (now + timedelta(hours=HOURLY_HOURS)).astimezone(self._time_zone)
        timerange = f"{self._format_datetime(now)}--{self._format_datetime(end)}:PT1H"

        parsed = await self._fetch_parameters(session, timerange, HOURLY_PARAMETERS)
        self._latest_hourly_parsed = parsed

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

        parsed = await self._fetch_parameters(session, timerange, DAILY_PARAMETERS)
        return self._build_daily_forecast(parsed)

    async def _fetch_parameters(
        self,
        session: aiohttp.ClientSession,
        timerange: str,
        parameters: Iterable[str],
    ) -> dict[str, dict[str, list[dict[str, Any]]]]:
        combined: dict[str, dict[str, list[dict[str, Any]]]] = {}

        for chunk in self._chunk_parameters(parameters):
            data = await self._perform_request(session, timerange, chunk)
            parsed = self._parse_response(data)
            for key, value in parsed.items():
                combined[key] = value

        return combined

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

    async def _perform_request(
        self,
        session: aiohttp.ClientSession,
        timerange: str,
        parameters: Iterable[str],
    ) -> dict[str, Any]:
        params = ",".join(parameters)
        url = (
            f"{API_BASE_URL}/{timerange}/{params}/{self._latitude},{self._longitude}/json"
        )
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

    def _parse_response(
        self, data: dict[str, Any]
    ) -> dict[str, dict[str, list[dict[str, Any]]]]:
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
    def _chunk_parameters(parameters: Iterable[str]) -> Iterable[list[str]]:
        chunk: list[str] = []
        for parameter in parameters:
            chunk.append(parameter)
            if len(chunk) == MAX_PARAMETERS_PER_REQUEST:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        return value.isoformat(timespec="seconds")

    def _build_current(
        self, parsed: dict[str, dict[str, list[dict[str, Any]]]], now: datetime
    ) -> dict[str, Any]:
        current_time = now.replace(minute=0, second=0, microsecond=0)
        temperature = self._value_at(parsed, "t_2m:C", current_time)
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
            "pressure": pressure,
            "wind_speed": wind_speed,
            "wind_bearing": wind_bearing,
            "condition": condition,
            "wind_gust": wind_gust,
            "uv_index": uv_index,
        }

    def _build_hourly_forecast(
        self, parsed: dict[str, dict[str, list[dict[str, Any]]]]
    ) -> list[dict[str, Any]]:
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
                    "wind_gust": self._value_at(parsed, "wind_gusts_10m_1h:ms", dt),
                    "uv_index": self._value_at(parsed, "uv:idx", dt),
                    "precipitation_24h": self._value_at(parsed, "precip_24h:mm", dt),
                }
            )
        return hourly

    def _build_daily_forecast(
        self, parsed: dict[str, dict[str, list[dict[str, Any]]]]
    ) -> list[dict[str, Any]]:
        derived_temperatures = self._derive_daily_temperatures()
        daily: list[dict[str, Any]] = []
        for entry in parsed.get("t_max_2m_24h:C", {}).get("dates", []):
            dt = self._parse_time(entry.get("date"))
            if dt is None:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=dt_util.UTC)
            local_day = dt.astimezone(self._time_zone).date()
            temperatures = derived_temperatures.get(local_day)
            condition = self._daily_condition(parsed, dt)
            midday = dt + timedelta(hours=12)
            precipitation = self._value_at(parsed, "precip_24h:mm", dt)
            if precipitation is None:
                precipitation = self._sum_hourly_values(
                    "precip_1h:mm", dt, dt + timedelta(days=1)
                )
            wind_speed = self._value_at(parsed, "wind_speed_10m:ms", dt)
            if wind_speed is None:
                wind_speed = self._hourly_value_near("wind_speed_10m:ms", midday)
            wind_bearing = self._value_at(parsed, "wind_dir_10m:d", dt)
            if wind_bearing is None:
                wind_bearing = self._hourly_value_near("wind_dir_10m:d", midday)
            pressure = self._value_at(parsed, "msl_pressure:hPa", dt)
            if pressure is None:
                pressure = self._hourly_value_near("msl_pressure:hPa", midday)
            uv_index = self._value_at(parsed, "uv:idx", dt)
            if uv_index is None:
                uv_index = self._hourly_value_near("uv:idx", midday)
            daily.append(
                {
                    "datetime": dt,
                    "temperature": (
                        temperatures[0]
                        if temperatures and temperatures[0] is not None
                        else entry.get("value")
                    ),
                    "templow": (
                        temperatures[1]
                        if temperatures and temperatures[1] is not None
                        else self._value_at(parsed, "t_min_2m_24h:C", dt)
                    ),
                    "condition": condition,
                    "precipitation": precipitation,
                    "wind_speed": wind_speed,
                    "wind_bearing": wind_bearing,
                    "wind_gust": self._value_at(parsed, "wind_gusts_10m_24h:ms", dt),
                    "pressure": pressure,
                    "uv_index": uv_index,
                    "sunrise": self._value_at(parsed, "sunrise:sql", dt),
                    "sunset": self._value_at(parsed, "sunset:sql", dt),
                }
            )
        return daily

    def _daily_condition(
        self, parsed: dict[str, dict[str, list[dict[str, Any]]]], day_start: datetime
    ) -> str | None:
        raw_symbol = self._value_at(parsed, "weather_symbol_24h:idx", day_start)
        if raw_symbol is not None:
            try:
                mapped = WEATHER_SYMBOL_MAP.get(int(raw_symbol))
                if mapped is not None:
                    return mapped
            except (TypeError, ValueError):
                LOGGER.debug(
                    "Invalid weather symbol for 24h data: %s", raw_symbol, exc_info=True
                )
        return self._infer_daily_condition(day_start)

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

        derived_temperatures = self._derive_daily_temperatures()
        for entry in self._daily_data:
            dt = entry.get("datetime")
            if isinstance(dt, datetime):
                localized = dt
                if localized.tzinfo is None:
                    localized = localized.replace(tzinfo=dt_util.UTC)
                local_day = localized.astimezone(self._time_zone).date()
                temperatures = derived_temperatures.get(local_day)
                entry["condition"] = self._infer_daily_condition(dt)
                if temperatures:
                    high, low = temperatures
                    if high is not None:
                        entry["temperature"] = high
                    if low is not None:
                        entry["templow"] = low

    def _derive_daily_temperatures(self) -> dict[date, tuple[float | None, float | None]]:
        derived: dict[date, tuple[float | None, float | None]] = {}
        hourly_entries = self._latest_hourly_parsed.get("t_2m:C", {}).get("dates", [])
        grouped: dict[date, list[float]] = {}

        for item in hourly_entries:
            dt = self._parse_time(item.get("date"))
            if dt is None:
                continue
            value = item.get("value")
            try:
                temperature = float(value)
            except (TypeError, ValueError):
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=dt_util.UTC)
            local_day = dt.astimezone(self._time_zone).date()
            grouped.setdefault(local_day, []).append(temperature)

        for local_day, temperatures in grouped.items():
            if not temperatures:
                continue
            derived[local_day] = (max(temperatures), min(temperatures))

        return derived

    def _hourly_value_near(
        self, parameter: str, target: datetime
    ) -> Any:
        dates = self._latest_hourly_parsed.get(parameter, {}).get("dates", [])
        best_value: Any = None
        best_distance: float | None = None
        for item in dates:
            dt = self._parse_time(item.get("date"))
            if dt is None:
                continue
            distance = abs((dt - target).total_seconds())
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_value = item.get("value")
        return best_value

    def _sum_hourly_values(
        self, parameter: str, start: datetime, end: datetime
    ) -> float | None:
        total = 0.0
        found = False
        dates = self._latest_hourly_parsed.get(parameter, {}).get("dates", [])
        for item in dates:
            dt = self._parse_time(item.get("date"))
            if dt is None or dt < start or dt >= end:
                continue
            value = item.get("value")
            try:
                total += float(value)
                found = True
            except (TypeError, ValueError):
                continue
        if not found:
            return None
        return total

    def _value_at(
        self,
        parsed: dict[str, dict[str, list[dict[str, Any]]]],
        parameter: str,
        target: datetime,
    ) -> Any:
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

