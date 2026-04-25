import asyncio
import logging
import random
from datetime import timedelta, datetime

import async_timeout
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.dess_monitor import MainCoordinator, HubConfigEntry
from custom_components.dess_monitor.const import (
    DOMAIN,
    CONF_DYNAMIC_SETTINGS_INTERVAL,
    DEFAULT_DYNAMIC_SETTINGS_INTERVAL,
    MIN_DYNAMIC_SETTINGS_INTERVAL,
    MAX_DYNAMIC_SETTINGS_INTERVAL,
    DYNAMIC_SETTINGS_API_TIMEOUT,
)
from custom_components.dess_monitor.coordinators.coordinator import _clamp
from custom_components.dess_monitor.hub import InverterDevice
from custom_components.dess_monitor.sdk import DeviceIdentity
from custom_components.dess_monitor.util import resolve_number_with_unit

_LOGGER = logging.getLogger(__name__)

# See ``select.py`` — platform interval is the throttle-check cadence; actual
# API hit rate is bounded by ``CONF_DYNAMIC_SETTINGS_INTERVAL``.
SCAN_INTERVAL = timedelta(seconds=60)
PARALLEL_UPDATES = 1


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: HubConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    hub = config_entry.runtime_data
    coordinator = hub.coordinator
    coordinator_data = hub.coordinator.data

    new_devices = []
    for item in hub.items:
        # grid sensors
        if coordinator_data is None or item.inverter_id not in coordinator_data:
            continue
        fields = coordinator_data[item.inverter_id]['ctrl_fields']
        if fields is None:
            continue
        if config_entry.options.get('dynamic_settings', False) is True:
            async_add_entities(list(
                map(
                    lambda field_data: InverterDynamicSettingNumber(item, coordinator, field_data),
                    filter(lambda field: 'item' not in field, fields)
                )
            )
            )
    if new_devices:
        async_add_entities(new_devices)


class NumberBase(CoordinatorEntity, NumberEntity):
    # should_poll = True

    def __init__(self, inverter_device: InverterDevice, coordinator: MainCoordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._inverter_device = inverter_device

    # To link this entity to the cover device, this property must return an
    # identifiers value matching that used in the cover, but no other information such
    # as name. If name is returned, this entity will then also become a device in the
    # HA UI.
    @property
    def device_info(self) -> DeviceInfo:
        """Information about this entity/device."""
        return {
            "identifiers": {(DOMAIN, self._inverter_device.inverter_id)},
            # If desired, the name for the device could be different to the entity
            "name": self._inverter_device.name,
            "sw_version": self._inverter_device.firmware_version,
            "model": self._inverter_device.device_data['pn'],
            "serial_number": self._inverter_device.device_data['sn'],
            "hw_version": self._inverter_device.device_data['devcode'],
            "model_id": self._inverter_device.device_data['devaddr'],
            "manufacturer": 'ESS'
        }

    # This property is important to let HA know if this entity is online or not.
    # If an entity is offline (return False), the UI will refelect this.
    @property
    def available(self) -> bool:
        """Return True if inverter_device and hub is available."""
        return self._inverter_device.online and self._inverter_device.hub.online

    @property
    def data(self):
        return self.coordinator.data[self._inverter_device.inverter_id]

    # async def async_added_to_hass(self):
    #     """Run when this Entity has been added to HA."""
    #     # Sensors should also register callbacks to HA when their state changes
    #     self._inverter_device.register_callback(self.async_write_ha_state)
    #
    # async def async_will_remove_from_hass(self):
    #     """Entity being removed from hass."""
    #     # The opposite of async_added_to_hass. Remove any registered call backs here.
    #     self._inverter_device.remove_callback(self.async_write_ha_state)


class InverterDynamicSettingNumber(NumberBase):
    _attr_native_value = None
    should_poll = True
    _attr_entity_category = EntityCategory.CONFIG

    # _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, inverter_device: InverterDevice, coordinator: MainCoordinator, field_data):
        super().__init__(inverter_device, coordinator)
        self._service_param_id = field_data['id']
        # "hint": "25.0~31.5V 48.0~61.0V"
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_settings_{field_data['id']}"
        self._attr_name = f"{self._inverter_device.name} SET {field_data['name']}"
        self._attr_native_unit_of_measurement = 'V'  # field_data['unit']
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 0.1
        self._attr_mode = NumberMode.BOX
        self._poll_interval = _clamp(
            coordinator.config_entry.options.get(
                CONF_DYNAMIC_SETTINGS_INTERVAL, DEFAULT_DYNAMIC_SETTINGS_INTERVAL,
            ),
            MIN_DYNAMIC_SETTINGS_INTERVAL,
            MAX_DYNAMIC_SETTINGS_INTERVAL,
        )
        # Stagger initial polls across one interval to avoid hammering the API.
        now = int(datetime.now().timestamp())
        self._last_updated: int | None = now - random.randint(0, max(self._poll_interval - 1, 1))

    async def async_update(self) -> None:
        now = int(datetime.now().timestamp())
        if self._last_updated is not None and (now - self._last_updated) < self._poll_interval:
            return

        try:
            async with async_timeout.timeout(DYNAMIC_SETTINGS_API_TIMEOUT):
                response = await self.coordinator.client.control.get_value(
                    DeviceIdentity.from_dict(self._inverter_device.device_data),
                    self._service_param_id,
                )
        except (asyncio.TimeoutError, Exception) as err:
            _LOGGER.debug(
                "Skipping update of %s: %s", self._attr_unique_id, err,
            )
            return

        if not isinstance(response, dict) or 'err' in response:
            self._last_updated = now
            return
        raw_val = response.get('val')
        if raw_val is None:
            self._last_updated = now
            return
        self._attr_native_value = resolve_number_with_unit(raw_val)
        self._last_updated = now
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        param_id = self._service_param_id
        param_value = str(value)
        await self.coordinator.client.control.set_param(
            DeviceIdentity.from_dict(self._inverter_device.device_data),
            param_id,
            param_value,
        )

        self._attr_native_value = param_value
        self.async_write_ha_state()
