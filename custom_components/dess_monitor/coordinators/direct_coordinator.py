import logging
from datetime import timedelta

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from custom_components.dess_monitor.api import *
from custom_components.dess_monitor.api.helpers import *
from custom_components.dess_monitor.auth_store import AuthStore
from custom_components.dess_monitor.const import (
    CONF_DIRECT_UPDATE_INTERVAL,
    DEFAULT_DIRECT_UPDATE_INTERVAL,
    MIN_DIRECT_UPDATE_INTERVAL,
    MAX_DIRECT_UPDATE_INTERVAL,
)
from custom_components.dess_monitor.coordinators.coordinator import _clamp

_LOGGER = logging.getLogger(__name__)


class DirectCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""
    devices = []

    def __init__(self, hass: HomeAssistant, config_entry, auth_store: AuthStore):
        """Initialize my coordinator."""
        interval_seconds = _clamp(
            config_entry.options.get(CONF_DIRECT_UPDATE_INTERVAL, DEFAULT_DIRECT_UPDATE_INTERVAL),
            MIN_DIRECT_UPDATE_INTERVAL,
            MAX_DIRECT_UPDATE_INTERVAL,
        )
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Direct request sensor",
            config_entry=config_entry,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=interval_seconds),
            # Set always_update to `False` if the data returned from the
            # api can be compared via `__eq__` to avoid duplicate updates
            # being dispatched to listeners
            always_update=False

        )
        self._update_timeout = max(interval_seconds, 30)
        self._auth_store = auth_store

    async def _async_setup(self):
        """Set up the coordinator

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        if self.config_entry.options.get('direct_request_protocol', False) is not True:
            return
        async with async_timeout.timeout(30):
            await self._auth_store.async_get()
            self.devices = await self.get_active_devices()
            _LOGGER.debug("direct coordinator setup devices count: %s", len(self.devices))

    async def get_active_devices(self):
        auth = await self._auth_store.async_get()
        devices = await get_devices(auth['token'], auth['secret'])
        active_devices = [device for device in devices if device['status'] != 1]
        devices_filter = self.config_entry.options.get("devices", [])

        if devices_filter:
            selected_devices = [
                device for device in active_devices
                if str(device.get("pn")) in devices_filter
            ]
        else:
            selected_devices = active_devices
        return selected_devices

    async def _async_update_data(self):
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(self._update_timeout):
                if self.config_entry.options.get('direct_request_protocol', False) is not True:
                    return None
                _LOGGER.debug("direct coordinator update data devices")

                auth = await self._auth_store.async_get()
                self.devices = await self.get_active_devices()

                token = auth['token']
                secret = auth['secret']

                async def fetch_device_data(device):
                    qpigs = await get_direct_data(token, secret, device, 'QPIGS')
                    qpigs2 = await get_direct_data(token, secret, device, 'QPIGS2')
                    qpiri = await get_direct_data(token, secret, device, 'QPIRI')
                    return device['pn'], {
                        'qpigs': qpigs,
                        'qpigs2': qpigs2,
                        'qpiri': qpiri
                    }

                data_map = dict(await asyncio.gather(*map(fetch_device_data, self.devices)))
                return data_map
                # return
        except TimeoutError as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise err
        except AuthInvalidateError as err:
            await self._auth_store.async_get(force_refresh=True)
            raise UpdateFailed("auth token invalidated, re-issued") from err
        # except ApiError as err:
