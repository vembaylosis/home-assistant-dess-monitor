import asyncio
import logging
from datetime import timedelta, datetime

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from .api import get_device_last_data, get_devices, auth_user, get_device_energy_flow, get_device_pars
from .api.helpers import get_inverter_output_priority

_LOGGER = logging.getLogger(__name__)


class MyCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""
    devices = []
    auth = None
    auth_issued_at = None

    def __init__(self, hass: HomeAssistant, config_entry):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="My sensor",
            config_entry=config_entry,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=60),
            # Set always_update to `False` if the data returned from the
            # api can be compared via `__eq__` to avoid duplicate updates
            # being dispatched to listeners
            always_update=False

        )
        # self.my_api = my_api
        # self._device: MyDevice | None = None

    async def _async_setup(self):
        """Set up the coordinator

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        await self.create_auth()

        self.devices = await self.get_active_devices()
        print('coordinator setup devices count: ', len(self.devices))
        # await self.async_refresh()
        # await self._async_update_data()

    async def create_auth(self):
        username = self.config_entry.data["username"]
        password_hash = self.config_entry.data["password_hash"]
        auth = await auth_user(username, password_hash)
        auth_issued_at = int(datetime.now().timestamp())

        self.auth = auth
        self.auth_issued_at = auth_issued_at

    async def check_auth(self):
        now = int(datetime.now().timestamp())
        print(self.auth)
        if self.auth_issued_at is None or (now - (self.auth_issued_at + (self.auth['expire'])) <= 3600):
            await self.create_auth()

    async def get_active_devices(self):
        devices = await get_devices(self.auth['token'], self.auth['secret'])
        active_devices = [device for device in devices if device['status'] != 1]
        return active_devices

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(60):
                # Grab active context variables to limit data required to be fetched from API
                # Note: using context is not required if there is no need or ability to limit
                # data retrieved from API.
                # listening_idx = set(self.async_contexts())
                print('coordinator update data devices')

                await self.check_auth()
                self.devices = await self.get_active_devices()

                token = self.auth['token']
                secret = self.auth['secret']

                last_data_tasks = [get_device_last_data(token, secret, device) for device in self.devices]
                last_results = await asyncio.gather(*last_data_tasks)

                web_query_device_energy_flow_es = [get_device_energy_flow(token, secret, device) for device in
                                                   self.devices]
                web_query_device_energy_flow_es_results = await asyncio.gather(*web_query_device_energy_flow_es)

                query_device_pars_es = [get_device_pars(token, secret, device) for device in self.devices]
                query_device_pars_es_results = await asyncio.gather(*query_device_pars_es)

                query_device_output_priority = [get_inverter_output_priority(token, secret, device) for device in
                                                self.devices]
                query_device_output_priority_results = await asyncio.gather(*query_device_output_priority)

                data_map = {}
                for i, device in enumerate(self.devices):
                    data_map[device['pn']] = {
                        'last_data': last_results[i],
                        'energy_flow': web_query_device_energy_flow_es_results[i],
                        'pars': query_device_pars_es_results[i],
                        'device': self.devices[i],
                        'device_extra': {
                            'output_priority': query_device_output_priority_results[i]
                        }
                    }
                return data_map
                # return
        except TimeoutError as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise err
        except Exception as e:
            await self.create_auth()
            # raise ConfigEntryAuthFailed from err
        # except ApiError as err:
