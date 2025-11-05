"""Weather platform for Meteomatics."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_HUMIDITY,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_PRESSURE,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_WIND_SPEED,
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CONF_LATITUDE, CONF_LONGITUDE, DOMAIN
from .coordinator import MeteomaticsDataUpdateCoordinator

DEFAULT_NAME = "Meteomatics"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Meteomatics weather entity."""
    coordinator: MeteomaticsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    name = entry.title or entry.data.get(CONF_NAME) or DEFAULT_NAME

    async_add_entities([MeteomaticsWeather(coordinator, entry, name)])


class MeteomaticsWeather(
    CoordinatorEntity[MeteomaticsDataUpdateCoordinator], WeatherEntity
):
    """Representation of a Meteomatics weather entity."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: MeteomaticsDataUpdateCoordinator,
        entry: ConfigEntry,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_name = name
        self._entry = entry
        self._attr_unique_id = entry.entry_id
        self._attr_should_poll = False
        self._attr_attribution = ATTRIBUTION
        self._attr_supported_features = (
            WeatherEntityFeature.FORECAST_HOURLY | WeatherEntityFeature.FORECAST_DAILY
        )
        self._attr_native_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_native_pressure_unit = UnitOfPressure.HPA
        self._attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
        self._attr_native_precipitation_unit = UnitOfLength.MILLIMETERS

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            manufacturer="Meteomatics",
            name=self.name,
            configuration_url="https://www.meteomatics.com/",
        )

    @property
    def native_temperature(self) -> float | None:
        return self.coordinator.data.get("current", {}).get("temperature")

    @property
    def temperature(self) -> float | None:
        return self.native_temperature

    @property
    def humidity(self) -> float | None:
        return self.coordinator.data.get("current", {}).get("humidity")

    @property
    def native_pressure(self) -> float | None:
        return self.coordinator.data.get("current", {}).get("pressure")

    @property
    def pressure(self) -> float | None:
        return self.native_pressure

    @property
    def native_wind_speed(self) -> float | None:
        return self.coordinator.data.get("current", {}).get("wind_speed")

    @property
    def wind_speed(self) -> float | None:
        return self.native_wind_speed

    @property
    def wind_bearing(self) -> float | None:
        return self.coordinator.data.get("current", {}).get("wind_bearing")

    @property
    def condition(self) -> str | None:
        return self.coordinator.data.get("current", {}).get("condition")

    @property
    def latitude(self) -> float:
        return float(self._entry.data[CONF_LATITUDE])

    @property
    def longitude(self) -> float:
        return float(self._entry.data[CONF_LONGITUDE])

    @property
    def forecast_hourly(self) -> list[Forecast] | None:
        hourly = self.coordinator.data.get("hourly")
        if not hourly:
            return None
        return [self._format_forecast(entry) for entry in hourly]

    @property
    def forecast_daily(self) -> list[Forecast] | None:
        daily = self.coordinator.data.get("daily")
        if not daily:
            return None
        return [self._format_forecast(entry, daily=True) for entry in daily]

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Return hourly forecast data."""
        return self.forecast_hourly

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return daily forecast data."""
        return self.forecast_daily

    def _format_forecast(self, data: dict[str, object], daily: bool = False) -> Forecast:
        forecast: Forecast = {
            ATTR_FORECAST_TIME: self._ensure_iso(data.get("datetime")),
            ATTR_FORECAST_TEMP: data.get("temperature"),
            ATTR_FORECAST_CONDITION: data.get("condition"),
            ATTR_FORECAST_PRECIPITATION: data.get("precipitation"),
            ATTR_FORECAST_WIND_SPEED: data.get("wind_speed"),
        }

        if not daily:
            forecast[ATTR_FORECAST_PRESSURE] = data.get("pressure")
            forecast[ATTR_FORECAST_WIND_BEARING] = data.get("wind_bearing")
            forecast[ATTR_FORECAST_HUMIDITY] = data.get("humidity")
        else:
            forecast[ATTR_FORECAST_TEMP_LOW] = data.get("templow")
        return forecast

    @staticmethod
    def _ensure_iso(value: object) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, str):
            return value
        return None
