from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, Awaitable, Coroutine, TypeVar

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from custom_components.dess_monitor.api.helpers import get_inverter_output_priority
from custom_components.dess_monitor.const import (
    CONF_MAIN_UPDATE_INTERVAL,
    DEFAULT_MAIN_UPDATE_INTERVAL,
    MIN_MAIN_UPDATE_INTERVAL,
    MAX_MAIN_UPDATE_INTERVAL,
)
from custom_components.dess_monitor.device_cache import DeviceCache
from custom_components.dess_monitor.sdk import (
    AuthError,
    DessmonitorClient,
    DeviceIdentity,
    TransportError,
)

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


async def safe_call(coro: Coroutine[Any, Any, T] | Awaitable[T], default: T | None = None) -> T | None:
    try:
        return await coro
    except TransportError as err:
        # Cloud timeout / network blip — expected with this provider. Log a
        # one-line WARNING so HA logs stay readable; the upstream stack frames
        # don't add diagnostic value when we already know it's the wire.
        _LOGGER.warning("DESS cloud transient (%s): %s", _action_of(err), err)
        return default
    except asyncio.TimeoutError as err:
        _LOGGER.warning("DESS cloud timed out: %s", err)
        return default
    except Exception:
        _LOGGER.exception("Error while awaiting %s", coro)
        return default


def _action_of(err: BaseException) -> str:
    """Best-effort label for which API call timed out (helps grep the logs)."""
    return getattr(err, "action", None) or type(err).__name__


def _clamp(value: object, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return low


class MainCoordinator(DataUpdateCoordinator):
    devices: list[dict[str, Any]] = []

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: Any,
        client: DessmonitorClient,
        device_cache: DeviceCache,
    ) -> None:
        interval_seconds = _clamp(
            config_entry.options.get(CONF_MAIN_UPDATE_INTERVAL, DEFAULT_MAIN_UPDATE_INTERVAL),
            MIN_MAIN_UPDATE_INTERVAL,
            MAX_MAIN_UPDATE_INTERVAL,
        )
        super().__init__(
            hass,
            _LOGGER,
            name="Main coordinator",
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

    @property
    def device_cache(self) -> DeviceCache:
        return self._device_cache

    async def _async_setup(self) -> None:
        async with async_timeout.timeout(30):
            await self._client.session.get_auth()
            self.devices = await self.get_active_devices()
            _LOGGER.debug("coordinator setup devices count: %s", len(self.devices))

    async def get_active_devices(self) -> list[dict[str, Any]]:
        devices = await self._device_cache.async_get_devices(
            lambda: self._client.devices.list()
        )
        active_devices = [device for device in devices if device['status'] != 1]
        if "devices" in self.config_entry.options and len(self.config_entry.options["devices"]) > 0:
            return [
                device for device in active_devices
                if str(device['pn']) in self.config_entry.options["devices"]
                or str(device['uid']) in self.config_entry.options["devices"]
            ]
        return active_devices

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            async with async_timeout.timeout(self._update_timeout):
                _LOGGER.debug("coordinator update data devices")

                self.devices = await self.get_active_devices()

                async def build_device_data(device: dict[str, Any]) -> tuple[str, dict[str, Any]]:
                    pn = device['pn']
                    identity = DeviceIdentity.from_dict(device)
                    last_data = await safe_call(self._client.devices.last_data(identity), default={})
                    energy_flow = await safe_call(self._client.devices.energy_flow(identity), default={})
                    pars = await safe_call(self._client.devices.pars(identity), default={})
                    ctrl_fields = await safe_call(
                        self._device_cache.async_get_ctrl_fields(
                            pn, lambda: self._client.control.get_fields(identity)
                        ),
                        default={'field': []},
                    )
                    output_priority = await safe_call(
                        self._device_cache.async_get_output_priority(
                            pn, lambda: get_inverter_output_priority(self._client, device)
                        ),
                        default=None,
                    )

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
                return {pn: data for pn, data in device_data}
        except TimeoutError:
            raise
        except AuthError as err:
            await self._client.session.invalidate()
            raise UpdateFailed("auth token invalidated, will re-issue next tick") from err
        except TransportError as err:
            # Wrap as UpdateFailed so HA's DataUpdateCoordinator logs a single
            # WARNING line ("Error fetching ... data: ...") instead of the
            # full aiohttp + SDK traceback.
            raise UpdateFailed(f"DESS cloud transient: {err}") from err
