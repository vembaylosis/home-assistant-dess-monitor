from __future__ import annotations

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.dess_monitor.auth_store import HomeAssistantTokenStorage
from custom_components.dess_monitor.coordinators.coordinator import MainCoordinator
from custom_components.dess_monitor.coordinators.direct_coordinator import DirectCoordinator
from custom_components.dess_monitor.device_cache import DeviceCache
from custom_components.dess_monitor.sdk import Credentials, DessmonitorClient
from . import hub

# List of platforms to support. There should be a matching .py file for each,
# eg <cover.py> and <sensor.py>
PLATFORMS = [Platform.SENSOR, Platform.SELECT, Platform.NUMBER]

type HubConfigEntry = ConfigEntry[hub.Hub]


async def async_setup_entry(hass: HomeAssistant, entry: HubConfigEntry) -> bool:
    await _migrate_data_to_options(hass, entry)
    username = entry.data["username"]
    client = DessmonitorClient(
        credentials=Credentials(
            username=username,
            password_hash=entry.data["password_hash"],
        ),
        http_session=async_get_clientsession(hass),
        storage=HomeAssistantTokenStorage(hass, entry.entry_id, username),
    )
    device_cache = DeviceCache(hass, entry.entry_id)
    my_coordinator = MainCoordinator(hass, entry, client, device_cache)
    direct_coordinator_ctx = DirectCoordinator(hass, entry, client, device_cache)
    await asyncio.gather(
        my_coordinator.async_config_entry_first_refresh(),
        direct_coordinator_ctx.async_config_entry_first_refresh()
    )

    entry.runtime_data = hub.Hub(hass, username, client, my_coordinator, direct_coordinator_ctx)
    await entry.runtime_data.init()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Drop the cached auth file when the entry is removed entirely."""
    storage = HomeAssistantTokenStorage(
        hass,
        entry.entry_id,
        entry.data.get("username", ""),
    )
    await storage.clear()
    await DeviceCache(hass, entry.entry_id).async_clear()


async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def _migrate_data_to_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    new_data = dict(entry.data)
    new_options = dict(entry.options)
    fields = [
        'dynamic_settings',
        'direct_request_protocol',
        'devices',
        'raw_sensors',
    ]
    k = 0
    for field in fields:
        if field in new_data:
            k += 1
            new_options[field] = new_data.pop(field)
    if k > 0:
        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            options=new_options
        )
