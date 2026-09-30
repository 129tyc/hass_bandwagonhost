"""KiwiVM traffic monitoring integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, PLATFORMS
from .coordinator import KiwiVMRuntimeData, KiwiVMTrafficCoordinator

type KiwiVMConfigEntry = ConfigEntry[KiwiVMRuntimeData]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration domain."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: KiwiVMConfigEntry) -> bool:
    """Set up one VPS entry and its shared coordinator."""
    coordinator = KiwiVMTrafficCoordinator(
        hass, entry, aiohttp_client.async_get_clientsession(hass)
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = KiwiVMRuntimeData(coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KiwiVMConfigEntry) -> bool:
    """Unload one VPS entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(
    hass: HomeAssistant, entry: KiwiVMConfigEntry
) -> None:
    """Reload this VPS after its polling options change."""
    await hass.config_entries.async_reload(entry.entry_id)
