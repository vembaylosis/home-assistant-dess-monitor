from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from custom_components.dess_monitor.api.helpers import get_direct_data
from custom_components.dess_monitor.const import (
    CONF_DIRECT_UPDATE_INTERVAL,
    DEFAULT_DIRECT_UPDATE_INTERVAL,
    MIN_DIRECT_UPDATE_INTERVAL,
    MAX_DIRECT_UPDATE_INTERVAL,
)
from custom_components.dess_monitor.coordinators.coordinator import _clamp
from custom_components.dess_monitor.device_cache import DeviceCache
from custom_components.dess_monitor.sdk import AuthError, DessmonitorClient, TransportError

_LOGGER = logging.getLogger(__name__)


class DirectCoordinator(DataUpdateCoordinator):
    """Polls inverter direct-protocol commands (QPIGS, QPIGS2, QPIRI)."""
    devices: list[dict[str, Any]] = []

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: Any,
        client: DessmonitorClient,
        device_cache: DeviceCache,
    ) -> None:
        interval_seconds = _clamp(
            config_entry.options.get(CONF_DIRECT_UPDATE_INTERVAL, DEFAULT_DIRECT_UPDATE_INTERVAL),
            MIN_DIRECT_UPDATE_INTERVAL,
            MAX_DIRECT_UPDATE_INTERVAL,
        )
        super().__init__(
            hass,
            _LOGGER,
            name="Direct request sensor",
            config_entry=config_entry,
            update_interval=timedelta(seconds=interval_seconds),
            always_update=False,
        )
        self._update_timeout = max(interval_seconds, 30)
        self._client = client
        self._device_cache = device_cache

    @property
    def client(self) -> DessmonitorClient:
        return self._client

    async def _async_setup(self) -> None:
        if self.config_entry.options.get('direct_request_protocol', False) is not True:
            return
        async with async_timeout.timeout(30):
            await self._client.session.get_auth()
            self.devices = await self.get_active_devices()
            _LOGGER.debug("direct coordinator setup devices count: %s", len(self.devices))

    async def get_active_devices(self) -> list[dict[str, Any]]:
        devices = await self._device_cache.async_get_devices(
            lambda: self._client.devices.list()
        )
        active_devices = [device for device in devices if device['status'] != 1]
        devices_filter = self.config_entry.options.get("devices", [])
        if devices_filter:
            return [
                device for device in active_devices
                if str(device.get("pn")) in devices_filter
            ]
        return active_devices

    async def _async_update_data(self) -> dict[str, dict[str, Any]] | None:
        try:
            async with async_timeout.timeout(self._update_timeout):
                if self.config_entry.options.get('direct_request_protocol', False) is not True:
                    return None
                _LOGGER.debug("direct coordinator update data devices")

                self.devices = await self.get_active_devices()

                async def fetch_device_data(device: dict[str, Any]) -> tuple[str, dict[str, Any]]:
                    qpigs = await get_direct_data(self._client, device, 'QPIGS')
                    qpigs2 = await get_direct_data(self._client, device, 'QPIGS2')
                    qpiri = await get_direct_data(self._client, device, 'QPIRI')
                    return device['pn'], {
                        'qpigs': qpigs,
                        'qpigs2': qpigs2,
                        'qpiri': qpiri,
                    }

                results = await asyncio.gather(*map(fetch_device_data, self.devices))
                return dict(results)
        except TimeoutError:
            raise
        except AuthError as err:
            await self._client.session.invalidate()
            raise UpdateFailed("auth token invalidated, will re-issue next tick") from err
        except TransportError as err:
            # Wrap as UpdateFailed so HA logs a single WARNING line instead
            # of the full aiohttp + SDK traceback every time the cloud blips.
            raise UpdateFailed(f"DESS cloud transient: {err}") from err
