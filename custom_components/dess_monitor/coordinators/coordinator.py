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
    CONF_MAIN_UPDATE_INTERVAL,
    DEFAULT_MAIN_UPDATE_INTERVAL,
    MIN_MAIN_UPDATE_INTERVAL,
    MAX_MAIN_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


async def safe_call(coro, default=None):
    try:
        return await coro
    except Exception:
        _LOGGER.exception("Error while awaiting %s", coro)
        return default


def _clamp(value, low, high):
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return low


class MainCoordinator(DataUpdateCoordinator):
    devices = []

    def __init__(self, hass: HomeAssistant, config_entry, auth_store: AuthStore):
        interval_seconds = _clamp(
            config_entry.options.get(CONF_MAIN_UPDATE_INTERVAL, DEFAULT_MAIN_UPDATE_INTERVAL),
            MIN_MAIN_UPDATE_INTERVAL,
            MAX_MAIN_UPDATE_INTERVAL,
        )
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Main coordinator",
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

    @property
    def auth(self):
        return self._auth_store._auth

    async def _async_setup(self):
        """Set up the coordinator

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        async with async_timeout.timeout(30):
            await self._auth_store.async_get()
            self.devices = await self.get_active_devices()
            _LOGGER.debug("coordinator setup devices count: %s", len(self.devices))

    async def get_active_devices(self):
        auth = await self._auth_store.async_get()
        devices = await get_devices(auth['token'], auth['secret'])
        active_devices = [device for device in devices if device['status'] != 1]
        selected_devices = [device for device in active_devices if
                            str(device['pn']) in self.config_entry.options["devices"] or str(device['uid']) in
                            self.config_entry.options["devices"]] if (
                "devices" in self.config_entry.options and len(
            self.config_entry.options["devices"]) > 0) else active_devices
        return selected_devices

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            async with async_timeout.timeout(self._update_timeout):
                _LOGGER.debug("coordinator update data devices")

                auth = await self._auth_store.async_get()
                self.devices = await self.get_active_devices()

                token = auth['token']
                secret = auth['secret']

                async def build_device_data(device):
                    pn = device['pn']
                    last_data = await safe_call(get_device_last_data(token, secret, device), default={})
                    energy_flow = await safe_call(get_device_energy_flow(token, secret, device), default={})
                    pars = await safe_call(get_device_pars(token, secret, device), default={})
                    ctrl_fields = await safe_call(get_device_ctrl_fields(token, secret, device), default={'field': []})
                    output_priority = await safe_call(get_inverter_output_priority(token, secret, device), default={})

                    return pn, {
                        'last_data': last_data,
                        'energy_flow': energy_flow,
                        'pars': pars,
                        'device': device,
                        'ctrl_fields': ctrl_fields.get('field', []),
                        'device_extra': {
                            'output_priority': output_priority,
                        }
                    }

                tasks = [build_device_data(device) for device in self.devices]

                device_data = await asyncio.gather(*tasks)

                data_map = {pn: data for pn, data in device_data}

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
