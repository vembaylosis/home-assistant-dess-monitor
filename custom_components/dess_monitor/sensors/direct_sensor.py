from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import UnitOfElectricPotential, UnitOfPower, UnitOfTemperature, EntityCategory, \
    UnitOfElectricCurrent
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.dess_monitor import DirectCoordinator
from custom_components.dess_monitor.const import DOMAIN
from custom_components.dess_monitor.hub import InverterDevice


class DirectSensorBase(CoordinatorEntity, SensorEntity):

    def __init__(self, inverter_device: InverterDevice, coordinator: DirectCoordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._inverter_device = inverter_device

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

    @property
    def available(self) -> bool:
        """Return True if inverter_device and hub is available."""
        return self._inverter_device.online and self._inverter_device.hub.online

    @property
    def data(self):
        return self.coordinator.data[self._inverter_device.inverter_id]


class DirectPVPowerSensor(DirectSensorBase):
    device_class = SensorDeviceClass.POWER
    _attr_unit_of_measurement = UnitOfPower.WATT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: DirectCoordinator):
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_direct_pv_power"
        self._attr_name = f"{self._inverter_device.name} Direct PV Power"

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.data
        # device_data = self._inverter_device.device_data
        # self._attr_native_value = float(data['direct_data']['pv_input_current']) * float(
        #     data['direct_data']['pv_input_voltage'])
        self._attr_native_value = float(data['direct_data']['pv_charging_power'])
        self.async_write_ha_state()


class DirectPV2PowerSensor(DirectSensorBase):
    device_class = SensorDeviceClass.POWER
    _attr_unit_of_measurement = UnitOfPower.WATT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: DirectCoordinator):
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_direct_pv2_power"
        self._attr_name = f"{self._inverter_device.name} Direct PV2 Power"

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.data
        # device_data = self._inverter_device.device_data
        # self._attr_native_value = float(data['direct_data']['pv_input_current']) * float(
        #     data['direct_data']['pv_input_voltage'])
        self._attr_native_value = float(data['direct_data_2']['pv_current']) * float(
            data['direct_data_2']['pv_voltage'])
        self.async_write_ha_state()


class DirectPVVoltageSensor(DirectSensorBase):
    device_class = SensorDeviceClass.VOLTAGE
    _attr_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: DirectCoordinator):
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_direct_pv_voltage"
        self._attr_name = f"{self._inverter_device.name} Direct PV Voltage"

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = float(self.data['direct_data']['pv_input_voltage'])
        self.async_write_ha_state()


class DirectPV2VoltageSensor(DirectSensorBase):
    device_class = SensorDeviceClass.VOLTAGE
    _attr_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: DirectCoordinator):
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_direct_pv2_voltage"
        self._attr_name = f"{self._inverter_device.name} Direct PV2 Voltage"

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = float(self.data['direct_data_2']['pv_voltage'])
        self.async_write_ha_state()


class DirectPV2CurrentSensor(DirectSensorBase):
    device_class = SensorDeviceClass.CURRENT
    _attr_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: DirectCoordinator):
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_direct_pv2_current"
        self._attr_name = f"{self._inverter_device.name} Direct PV2 Current"

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = float(self.data['direct_data_2']['pv_current'])
        self.async_write_ha_state()


class DirectBatteryVoltageSensor(DirectSensorBase):
    device_class = SensorDeviceClass.VOLTAGE
    _attr_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 1
    _sensor_option_display_precision = 1

    def __init__(self, inverter_device: InverterDevice, coordinator: DirectCoordinator):
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_direct_battery"
        self._attr_name = f"{self._inverter_device.name} Direct Battery Voltage"

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = float(self.data['direct_data']['battery_voltage'])
        self.async_write_ha_state()


class DirectInverterOutputPowerSensor(DirectSensorBase):
    device_class = SensorDeviceClass.POWER
    _attr_unit_of_measurement = UnitOfPower.WATT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: DirectCoordinator):
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_direct_inverter_out_power"
        self._attr_name = f"{self._inverter_device.name} Direct Inverter Out Power"

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = float(self.data['direct_data']['output_active_power'])
        self.async_write_ha_state()


class DirectInverterTemperatureSensor(DirectSensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.TEMPERATURE
    _attr_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: DirectCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_direct_inverter_temperature"
        self._attr_name = f"{self._inverter_device.name} Direct Inverter Temperature"

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = float(self.data['direct_data']['inverter_heat_sink_temperature'])
        self.async_write_ha_state()
