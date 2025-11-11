"""The Meteomatics Home Assistant integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .coordinator import MeteomaticsDataUpdateCoordinator

LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.WEATHER]


def _get_update_interval(entry: ConfigEntry) -> timedelta:
    minutes = entry.options.get(
        CONF_UPDATE_INTERVAL,
        entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
    )
    return timedelta(minutes=minutes)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Meteomatics from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    LOGGER.debug("Setting up Meteomatics entry %s", entry.entry_id)

    coordinator = MeteomaticsDataUpdateCoordinator(
        hass,
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        latitude=entry.data[CONF_LATITUDE],
        longitude=entry.data[CONF_LONGITUDE],
        update_interval=_get_update_interval(entry),
        config_entry=entry,
    )

    hass.data[DOMAIN][entry.entry_id] = coordinator

    if entry.state == ConfigEntryState.SETUP_IN_PROGRESS:
        await coordinator.async_config_entry_first_refresh()
    else:
        success = await coordinator.async_refresh()
        if not success:
            raise ConfigEntryNotReady("Initial data refresh failed")

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Meteomatics config entry."""
    LOGGER.debug("Unloading Meteomatics entry %s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload Meteomatics config entry when options change."""
    coordinator: MeteomaticsDataUpdateCoordinator | None = hass.data[DOMAIN].get(
        entry.entry_id
    )

    if coordinator is None:
        LOGGER.debug(
            "Options updated for Meteomatics entry %s before setup completed; "
            "the new update interval will be applied on the next setup",
            entry.entry_id,
        )
        return

    new_interval = _get_update_interval(entry)

    interval_changed = False
    if coordinator.update_interval != new_interval:
        try:
            await coordinator.async_set_update_interval(new_interval)
        except AttributeError:  # Home Assistant < 2024.8
            coordinator.update_interval = new_interval
        interval_changed = True

    credentials_changed = coordinator.update_credentials(
        entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )

    if not interval_changed and not credentials_changed:
        LOGGER.debug(
            "Meteomatics entry %s already using provided configuration",
            entry.entry_id,
        )
        return

    await coordinator.async_request_refresh()
