"""Meteomatics data coordinator."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_BASE_URL,
    DAILY_DAYS,
    HOURLY_HOURS,
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
    ) -> None:
        self._username = username
        self._password = password
        self._latitude = latitude
        self._longitude = longitude
        super().__init__(
            hass,
            LOGGER,
            name="Meteomatics",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Meteomatics."""
        session = async_get_clientsession(self.hass)
        try:
            current, hourly = await self._fetch_hourly(session)
            daily = await self._fetch_daily(session)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Error communicating with Meteomatics: {err}") from err

        return {
            "current": current,
            "hourly": hourly,
            "daily": daily,
        }

    async def _fetch_hourly(self, session: aiohttp.ClientSession) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        end = now + timedelta(hours=HOURLY_HOURS)
        timerange = f"{now:%Y-%m-%dT%H:%M:%SZ}--{end:%Y-%m-%dT%H:%M:%SZ}:PT1H"
        parameters = ",".join(
            [
                "t_2m:C",
                "weather_symbol_1h:idx",
                "wind_speed_10m:ms",
                "wind_dir_10m:d",
                "pressure_mean_sea_level:hPa",
                "relative_humidity_2m:p",
                "precip_1h:mm",
            ]
        )

        data = await self._request(session, timerange, parameters)
        parsed = self._parse_response(data)

        current = self._build_current(parsed, now)
        hourly_forecast = self._build_hourly_forecast(parsed)
        return current, hourly_forecast

    async def _fetch_daily(self, session: aiohttp.ClientSession) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now + timedelta(days=DAILY_DAYS)
        timerange = f"{now:%Y-%m-%dT%H:%M:%SZ}--{end:%Y-%m-%dT%H:%M:%SZ}:P1D"
        parameters = ",".join(
            [
                "t_max_2m_24h:C",
                "t_min_2m_24h:C",
                "weather_symbol_24h:idx",
                "precip_24h:mm",
                "wind_speed_10m:ms",
            ]
        )

        data = await self._request(session, timerange, parameters)
        parsed = self._parse_response(data)

        return self._build_daily_forecast(parsed)

    async def _request(self, session: aiohttp.ClientSession, timerange: str, parameters: str) -> dict[str, Any]:
        url = f"{API_BASE_URL}/{timerange}/{parameters}/{self._latitude},{self._longitude}/json"
        async with session.get(url, auth=aiohttp.BasicAuth(self._username, self._password), timeout=30) as response:
            response.raise_for_status()
            return await response.json()

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

    def _build_current(self, parsed: dict[str, dict[str, list[dict[str, Any]]]], now: datetime) -> dict[str, Any]:
        current_time = now.replace(minute=0, second=0, microsecond=0)
        temperature = self._value_at(parsed, "t_2m:C", current_time)
        humidity = self._value_at(parsed, "relative_humidity_2m:p", current_time)
        pressure = self._value_at(parsed, "pressure_mean_sea_level:hPa", current_time)
        wind_speed = self._value_at(parsed, "wind_speed_10m:ms", current_time)
        wind_bearing = self._value_at(parsed, "wind_dir_10m:d", current_time)
        condition = WEATHER_SYMBOL_MAP.get(
            int(self._value_at(parsed, "weather_symbol_1h:idx", current_time) or 0),
        )

        return {
            "temperature": temperature,
            "humidity": humidity,
            "pressure": pressure,
            "wind_speed": wind_speed,
            "wind_bearing": wind_bearing,
            "condition": condition,
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
                    "pressure": self._value_at(parsed, "pressure_mean_sea_level:hPa", dt),
                    "wind_speed": self._value_at(parsed, "wind_speed_10m:ms", dt),
                    "wind_bearing": self._value_at(parsed, "wind_dir_10m:d", dt),
                    "humidity": self._value_at(parsed, "relative_humidity_2m:p", dt),
                }
            )
        return hourly

    def _build_daily_forecast(self, parsed: dict[str, dict[str, list[dict[str, Any]]]]) -> list[dict[str, Any]]:
        daily: list[dict[str, Any]] = []
        for entry in parsed.get("t_max_2m_24h:C", {}).get("dates", []):
            dt = self._parse_time(entry.get("date"))
            if dt is None:
                continue
            condition = WEATHER_SYMBOL_MAP.get(
                int(self._value_at(parsed, "weather_symbol_24h:idx", dt) or 0),
            )
            daily.append(
                {
                    "datetime": dt,
                    "temperature": entry.get("value"),
                    "templow": self._value_at(parsed, "t_min_2m_24h:C", dt),
                    "condition": condition,
                    "precipitation": self._value_at(parsed, "precip_24h:mm", dt),
                    "wind_speed": self._value_at(parsed, "wind_speed_10m:ms", dt),
                }
            )
        return daily

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
