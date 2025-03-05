
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from . import hub
from .coordinator import MyCoordinator

# List of platforms to support. There should be a matching .py file for each,
# eg <cover.py> and <sensor.py>
PLATFORMS = [Platform.SENSOR]

type HubConfigEntry = ConfigEntry[hub.Hub]


async def async_setup_entry(hass: HomeAssistant, entry: HubConfigEntry) -> bool:
    # Store an instance of the "connecting" class that does the work of speaking
    # with your actual devices.
    my_coordinator = MyCoordinator(hass, entry)
    await my_coordinator.async_config_entry_first_refresh()

    entry.runtime_data = hub.Hub(hass, entry.data["username"], my_coordinator)
    await entry.runtime_data.init()
    # This creates each HA object for each platform your device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await my_coordinator.async_refresh()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    return unload_ok
