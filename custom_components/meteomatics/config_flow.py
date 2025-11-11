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
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import (
    API_BASE_URL,
    BASIC_OPTIONAL_PARAMETER_LABELS,
    BASIC_OPTIONAL_PARAMETER_LIMIT,
    BASIC_OPTIONAL_PARAMETER_SCOPES,
    CONF_BASIC_OPTIONAL_PARAMETERS,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_PLAN_TYPE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_MODEL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    PLAN_TYPE_BASIC,
    PLAN_TYPE_OPTIONS,
    PLAN_TYPE_PAID_TRIAL,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_PLAN_TYPE, default=PLAN_TYPE_PAID_TRIAL): vol.In(
            PLAN_TYPE_OPTIONS
        ),
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

    def __init__(self) -> None:
        self._pending_user_input: dict[str, Any] | None = None

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
                if user_input[CONF_PLAN_TYPE] == PLAN_TYPE_BASIC:
                    self._pending_user_input = dict(user_input)
                    return await self.async_step_basic_parameters()

                await self.async_set_unique_id(
                    f"{user_input[CONF_LATITUDE]:.4f}_{user_input[CONF_LONGITUDE]:.4f}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Meteomatics",
                    data={
                        **user_input,
                        CONF_BASIC_OPTIONAL_PARAMETERS: [],
                    },
                )

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)

    async def async_step_basic_parameters(
        self, user_input: Mapping[str, Any] | None = None
    ) -> FlowResult:
        """Handle selection of optional parameters for the basic plan."""

        if self._pending_user_input is None:
            return self.async_abort(reason="unknown")

        errors: dict[str, str] = {}
        default_selection = list(
            self._pending_user_input.get(CONF_BASIC_OPTIONAL_PARAMETERS, [])
        )

        if user_input is not None:
            selected = user_input.get(CONF_BASIC_OPTIONAL_PARAMETERS, [])
            valid_selection = [
                param
                for param in selected
                if param in BASIC_OPTIONAL_PARAMETER_SCOPES
            ]

            if len(valid_selection) > BASIC_OPTIONAL_PARAMETER_LIMIT:
                errors["base"] = "basic_too_many_parameters"
                default_selection = valid_selection
            else:
                self._pending_user_input[CONF_BASIC_OPTIONAL_PARAMETERS] = valid_selection

                await self.async_set_unique_id(
                    f"{self._pending_user_input[CONF_LATITUDE]:.4f}_"
                    f"{self._pending_user_input[CONF_LONGITUDE]:.4f}"
                )
                self._abort_if_unique_id_configured()

                data = dict(self._pending_user_input)
                self._pending_user_input = None

                return self.async_create_entry(title="Meteomatics", data=data)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_BASIC_OPTIONAL_PARAMETERS,
                    default=default_selection,
                ): cv.multi_select(self._basic_parameter_labels()),
            }
        )

        return self.async_show_form(
            step_id="basic_parameters",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return MeteomaticsOptionsFlow(config_entry)

    def _basic_parameter_labels(self) -> dict[str, str]:
        language = (self.hass.config.language or "").lower()

        def _label_for(param: str) -> str:
            labels = BASIC_OPTIONAL_PARAMETER_LABELS.get(param, {})
            if language in labels:
                return labels[language]
            if language.startswith("pt") and "pt-BR" in labels:
                return labels["pt-BR"]
            return labels.get("default", param)

        return {
            param: _label_for(param)
            for param in BASIC_OPTIONAL_PARAMETER_SCOPES
        }


class MeteomaticsOptionsFlow(config_entries.OptionsFlowWithConfigEntry):
    """Handle options flow for Meteomatics."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        super().__init__(config_entry)
        self._pending_new_data: dict[str, Any] | None = None
        self._pending_options: dict[str, Any] | None = None

    async def async_step_init(self, user_input: Mapping[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            new_username = user_input[CONF_USERNAME]
            new_password = user_input[CONF_PASSWORD]
            update_interval = user_input[CONF_UPDATE_INTERVAL]
            new_plan_type = user_input[CONF_PLAN_TYPE]

            validation_data = {
                CONF_USERNAME: new_username,
                CONF_PASSWORD: new_password,
                CONF_LATITUDE: self.config_entry.data[CONF_LATITUDE],
                CONF_LONGITUDE: self.config_entry.data[CONF_LONGITUDE],
            }

            try:
                await validate_input(self.hass, validation_data)
            except aiohttp.ClientResponseError as err:
                if err.status == 401:
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "cannot_connect"
            except (aiohttp.ClientError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                new_data = {
                    **self.config_entry.data,
                    CONF_USERNAME: new_username,
                    CONF_PASSWORD: new_password,
                    CONF_PLAN_TYPE: new_plan_type,
                }

                options_data = {CONF_UPDATE_INTERVAL: update_interval}

                if new_plan_type == PLAN_TYPE_BASIC:
                    new_data.setdefault(CONF_BASIC_OPTIONAL_PARAMETERS, [])
                    self._pending_new_data = new_data
                    self._pending_options = options_data
                    return await self.async_step_basic_parameters()

                new_data.pop(CONF_BASIC_OPTIONAL_PARAMETERS, None)

                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=new_data,
                )

                return self.async_create_entry(title="", data=options_data)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_USERNAME,
                    default=self.config_entry.data[CONF_USERNAME],
                ): str,
                vol.Required(
                    CONF_PASSWORD,
                    default=self.config_entry.data[CONF_PASSWORD],
                ): str,
                vol.Required(
                    CONF_PLAN_TYPE,
                    default=self.config_entry.data.get(
                        CONF_PLAN_TYPE, PLAN_TYPE_PAID_TRIAL
                    ),
                ): vol.In(PLAN_TYPE_OPTIONS),
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

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)

    async def async_step_basic_parameters(
        self, user_input: Mapping[str, Any] | None = None
    ) -> FlowResult:
        """Handle optional parameter selection for the basic plan in options."""

        if self._pending_new_data is None or self._pending_options is None:
            return self.async_abort(reason="unknown")

        errors: dict[str, str] = {}
        default_selection = list(
            self.config_entry.data.get(
                CONF_BASIC_OPTIONAL_PARAMETERS,
                [],
            )
        )

        if user_input is not None:
            selected = user_input.get(CONF_BASIC_OPTIONAL_PARAMETERS, [])
            valid_selection = [
                param
                for param in selected
                if param in BASIC_OPTIONAL_PARAMETER_SCOPES
            ]

            if len(valid_selection) > BASIC_OPTIONAL_PARAMETER_LIMIT:
                errors["base"] = "basic_too_many_parameters"
                default_selection = valid_selection
            else:
                self._pending_new_data[CONF_BASIC_OPTIONAL_PARAMETERS] = valid_selection

                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=self._pending_new_data,
                )

                options = self._pending_options
                self._pending_new_data = None
                self._pending_options = None
                return self.async_create_entry(title="", data=options)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_BASIC_OPTIONAL_PARAMETERS,
                    default=default_selection,
                ): cv.multi_select(self._basic_parameter_labels()),
            }
        )

        return self.async_show_form(
            step_id="basic_parameters",
            data_schema=schema,
            errors=errors,
        )

    def _basic_parameter_labels(self) -> dict[str, str]:
        language = (self.hass.config.language or "").lower()

        def _label_for(param: str) -> str:
            labels = BASIC_OPTIONAL_PARAMETER_LABELS.get(param, {})
            if language in labels:
                return labels[language]
            if language.startswith("pt") and "pt-BR" in labels:
                return labels["pt-BR"]
            return labels.get("default", param)

        return {
            param: _label_for(param)
            for param in BASIC_OPTIONAL_PARAMETER_SCOPES
        }
