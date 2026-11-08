"""Tohmo charging integration."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TohmoClient
from .coordinator import TohmoCoordinator

PLATFORMS = [Platform.BUTTON, Platform.NUMBER, Platform.SELECT, Platform.SENSOR,
             Platform.SWITCH, Platform.TEXT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    def save_tokens(tokens: dict) -> None:
        hass.config_entries.async_update_entry(entry, data={**entry.data, "tokens": tokens})

    client = TohmoClient(async_get_clientsession(hass), entry.data["tokens"], save_tokens)
    coordinator = TohmoCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

