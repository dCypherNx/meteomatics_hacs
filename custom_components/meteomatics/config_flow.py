"""Config flow for Meteomatics."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import (
    API_BASE_URL,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_MODEL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_LATITUDE): vol.Coerce(float),
        vol.Required(CONF_LONGITUDE): vol.Coerce(float),
        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: Mapping[str, Any]) -> None:
    """Validate user input by performing a simple API request."""
    session = async_get_clientsession(hass)
    time_zone_name = hass.config.time_zone
    time_zone = (
        dt_util.get_time_zone(time_zone_name)
        if time_zone_name
        else dt_util.UTC
    )
    now = dt_util.utcnow().astimezone(time_zone)
    now = now.replace(minute=0, second=0, microsecond=0)
    timerange = f"{now.isoformat(timespec='seconds')}--{now.isoformat(timespec='seconds')}:PT1H"
    parameters = "t_2m:C"
    url = f"{API_BASE_URL}/{timerange}/{parameters}/{data[CONF_LATITUDE]},{data[CONF_LONGITUDE]}/json"

    async with session.get(
        url,
        auth=aiohttp.BasicAuth(data[CONF_USERNAME], data[CONF_PASSWORD]),
        params={"model": DEFAULT_MODEL},
        timeout=30,
    ) as response:
        response.raise_for_status()


class MeteomaticsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Meteomatics."""

    VERSION = 1

    async def async_step_user(self, user_input: Mapping[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
            except aiohttp.ClientResponseError as err:
                if err.status == 401:
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "cannot_connect"
            except (aiohttp.ClientError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(
                    f"{user_input[CONF_LATITUDE]:.4f}_{user_input[CONF_LONGITUDE]:.4f}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Meteomatics", data=user_input)

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return MeteomaticsOptionsFlow(config_entry)


class MeteomaticsOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Meteomatics."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Mapping[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_UPDATE_INTERVAL,
                        self.config_entry.data.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ),
                ): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL)
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
