from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.dess_monitor import MyCoordinator, HubConfigEntry
from custom_components.dess_monitor.api.helpers import resolve_output_priority, set_inverter_output_priority
from custom_components.dess_monitor.const import DOMAIN
from custom_components.dess_monitor.hub import InverterDevice


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: HubConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    hub = config_entry.runtime_data

    new_devices = []
    for item in hub.items:
        # grid sensors
        new_devices.append(InverterOutputPrioritySelect(item, hub.coordinator))
    if new_devices:
        async_add_entities(new_devices)


class SelectBase(CoordinatorEntity, SelectEntity):
    # should_poll = True

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
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


class InverterOutputPrioritySelect(SelectBase):
    _attr_current_option = None

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_output_priority"
        self._attr_name = f"{self._inverter_device.name} Output Priority"
        self._attr_options = ['Utility', 'Solar', 'SBU']

        if coordinator.data is not None:
            data = coordinator.data[self._inverter_device.inverter_id]
            device_data = self._inverter_device.device_data
            self._attr_current_option = resolve_output_priority(data, device_data)

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data[self._inverter_device.inverter_id]
        device_data = self._inverter_device.device_data
        self._attr_current_option = resolve_output_priority(data, device_data)
        self.async_write_ha_state()

    async def async_select_option(self, option: str):
        if option in self._attr_options:
            # los_output_source_priority Utility, Solar, SBU
            await set_inverter_output_priority(
                self.coordinator.auth['token'],
                self.coordinator.auth['secret'],
                self._inverter_device.device_data,
                option
            )
            self._attr_current_option = option
            await self.coordinator.async_request_refresh()
