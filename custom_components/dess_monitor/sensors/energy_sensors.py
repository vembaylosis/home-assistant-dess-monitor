from datetime import datetime

from homeassistant.components.sensor import RestoreSensor, SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfEnergy
from homeassistant.core import callback

from custom_components.dess_monitor.api.resolvers.data_resolvers import *
from custom_components.dess_monitor.coordinators.coordinator import MainCoordinator
from custom_components.dess_monitor.hub import InverterDevice
from custom_components.dess_monitor.sensors.init_sensors import SensorBase


class MyEnergySensor(RestoreSensor, SensorBase):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0
    _attr_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR

    def __init__(self, inverter_device: InverterDevice, coordinator: MainCoordinator):
        super().__init__(inverter_device, coordinator)
        self._prev_value = None
        self._prev_value_timestamp = datetime.now()
        self._is_restored_value = False

    async def async_added_to_hass(self) -> None:
        if (last_sensor_data := await self.async_get_last_extra_data()) is not None:
            self._attr_native_value = last_sensor_data.as_dict().get('native_value', 0)
        else:
            self._attr_native_value = 0
        self._is_restored_value = True
        await super().async_added_to_hass()

    @property
    def available(self) -> bool:
        return self._inverter_device.online and self._inverter_device.hub.online and self._is_restored_value

    def update_energy_value(self, current_value: float):
        now = datetime.now()
        elapsed_seconds = int(now.timestamp() - self._prev_value_timestamp.timestamp())
        if self._prev_value is not None:
            self._attr_native_value += (elapsed_seconds / 3600) * (self._prev_value + current_value) / 2
        self._prev_value = current_value
        self._prev_value_timestamp = now
        self.async_write_ha_state()


class FunctionBasedEnergySensor(MyEnergySensor):
    def __init__(self, inverter_device: InverterDevice, coordinator: MainCoordinator, unique_suffix: str,
                 name_suffix: str, resolve_function):
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_{unique_suffix}"
        self._attr_name = f"{self._inverter_device.name} {name_suffix}"
        self._resolve_function = resolve_function

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.data
        device_data = self._inverter_device.device_data
        current_value = self._resolve_function(data, device_data)
        self.update_energy_value(current_value)


class PVEnergySensor(FunctionBasedEnergySensor):
    def __init__(self, inverter_device: InverterDevice, coordinator: MainCoordinator):
        super().__init__(inverter_device, coordinator, "pv_in_energy", "PV In Energy", resolve_pv_power)


class PV2EnergySensor(FunctionBasedEnergySensor):
    def __init__(self, inverter_device: InverterDevice, coordinator: MainCoordinator):
        super().__init__(inverter_device, coordinator, "pv2_in_energy", "PV2 In Energy", resolve_pv2_power)


class BatteryInEnergySensor(FunctionBasedEnergySensor):
    def __init__(self, inverter_device: InverterDevice, coordinator: MainCoordinator):
        super().__init__(inverter_device, coordinator, "battery_in_energy", "Battery In Energy",
                         resolve_battery_charging_power)


class BatteryOutEnergySensor(FunctionBasedEnergySensor):
    def __init__(self, inverter_device: InverterDevice, coordinator: MainCoordinator):
        super().__init__(inverter_device, coordinator, "battery_out_energy", "Battery Out Energy",
                         resolve_battery_discharge_power)


class InverterOutEnergySensor(FunctionBasedEnergySensor):
    def __init__(self, inverter_device: InverterDevice, coordinator: MainCoordinator):
        super().__init__(inverter_device, coordinator, "inverter_out_energy", "Inverter Out Energy",
                         resolve_active_load_power)


class InverterInEnergySensor(FunctionBasedEnergySensor):
    def __init__(self, inverter_device: InverterDevice, coordinator: MainCoordinator):
        super().__init__(inverter_device, coordinator, "inverter_in_energy", "Inverter In Energy",
                         resolve_grid_in_power)
