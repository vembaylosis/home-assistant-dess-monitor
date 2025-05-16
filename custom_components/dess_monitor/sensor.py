"""Platform for sensor integration."""
from datetime import datetime
from enum import Enum

from homeassistant.components.sensor import (
    SensorDeviceClass, SensorEntity, SensorStateClass, RestoreSensor,
)
from homeassistant.const import (
    UnitOfPower, UnitOfElectricPotential, UnitOfElectricCurrent, UnitOfEnergy, EntityCategory, UnitOfTemperature,
    UnitOfFrequency, PERCENTAGE
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HubConfigEntry, MyCoordinator
from .api.helpers import *
from .const import DOMAIN
from custom_components.dess_monitor.sensors.direct_sensor import DirectPVPowerSensor, DirectBatteryVoltageSensor, \
    DirectPVVoltageSensor, DirectInverterOutputPowerSensor, DirectInverterTemperatureSensor
from .hub import InverterDevice


# This file shows the setup for the sensors associated with the cover.
# They are setup in the same way with the call to the async_setup_entry function
# via HA from the module __init__. Each sensor has a device_class, this tells HA how
# to display it in the UI (for know types). The unit_of_measurement property tells HA
# what the unit is, so it can display the correct range. For predefined types (such as
# battery), the unit_of_measurement should match what's expected.


# See cover.py for more details.
# Note how both entities for each sensor (battery and illuminance) are added at
# the same time to the same list. This way only a single async_add_devices call is
# required.
async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: HubConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    hub = config_entry.runtime_data

    new_devices = []
    for item in hub.items:
        sensor_classes = [
            # Grid sensors
            GridInputVoltageSensor,
            GridInputFrequencySensor,
            GridInputPowerSensor,
            # PV sensors
            PVPowerSensor,
            PVPowerTotalSensor,  # deprecated
            PVEnergySensor,
            PVVoltageSensor,
            # Battery sensors
            BatteryVoltageSensor,
            BatteryChargeSensor,
            BatteryChargePowerSensor,
            BatteryDischargeSensor,
            BatteryDischargePowerSensor,
            BatteryInEnergySensor,
            BatteryOutEnergySensor,
            BatteryCapacitySensor,
            # Inverter sensors
            InverterStatusSensor,
            InverterOutputPrioritySensor,
            InverterOutputVoltageSensor,
            InverterOutputPowerSensor,
            InverterOutEnergySensor,
            InverterInEnergySensor,
            InverterDCTemperatureSensor,
            InverterInvTemperatureSensor,
            InverterLoadSensor,
            # Inverter config sensors
            InverterChargePrioritySensor,
            InverterConfigBTUtilityChargeSensor,
            InverterConfigBTTotalChargeSensor,
            InverterConfigBTCutoffSensor,
            InverterNominalOutPowerSensor,
            InverterRatedBatteryVoltageSensor,
            InverterComebackUtilityVoltageSensor,
            InverterComebackBatteryVoltageSensor,
        ]

        for sensor_cls in sensor_classes:
            new_devices.append(sensor_cls(item, hub.coordinator))
        if (
                config_entry.options.get('raw_sensors', False)
                and hub.coordinator.data is not None
                and item.inverter_id in hub.coordinator.data
        ):
            data = hub.coordinator.data[item.inverter_id]
            allowed_units = {'kW', 'W', 'A', 'V', 'HZ', '%'}

            def is_valid_parameter(param):
                return 'unit' in param and param['unit'] in allowed_units

            for parameter in filter(is_valid_parameter, data.get('pars', {}).get('parameter', [])):
                new_devices.append(InverterDynamicSensor(
                    item, hub.coordinator, parameter, DessSensorSource.PARS_ES
                ))

            for key, params in data.get('last_data', {}).get('pars', {}).items():
                for parameter in filter(is_valid_parameter, params):
                    new_devices.append(InverterDynamicSensor(
                        item,
                        hub.coordinator,
                        {
                            'par': parameter['id'],
                            'name': parameter['par'],
                            'val': parameter['val'],
                            'unit': parameter['unit'],
                        },
                        DessSensorSource.SP_LAST_DATA,
                    ))
        if (
                config_entry.options.get('direct_request_protocol', False) is True
                and hub.direct_coordinator.data is not None
                and item.inverter_id in hub.direct_coordinator.data
        ):
            direct_sensors = [
                DirectPVPowerSensor,
                DirectBatteryVoltageSensor,
                DirectPVVoltageSensor,
                DirectInverterOutputPowerSensor,
                DirectInverterTemperatureSensor,
            ]

            for sensor_cls in direct_sensors:
                new_devices.append(sensor_cls(item, hub.direct_coordinator))
    if new_devices:
        async_add_entities(new_devices)


class SensorBase(CoordinatorEntity, SensorEntity):

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
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


class MyEnergySensor(RestoreSensor, SensorBase):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0
    _prev_value = None
    _prev_value_timestamp = datetime.now()
    _attr_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _is_restored_value = False

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""

        if (last_sensor_data := await self.async_get_last_extra_data()) is not None:
            # print('last_sensor_data', last_sensor_data.as_dict())
            self._attr_native_value = (last_sensor_data.as_dict())['native_value']
        else:
            self._attr_native_value = 0
        self._is_restored_value = True
        await super().async_added_to_hass()

    @property
    def available(self) -> bool:
        """Return True if inverter_device and hub is available."""
        return self._inverter_device.online and self._inverter_device.hub.online and self._is_restored_value


class BatteryVoltageSensor(SensorBase):
    """Representation of a Sensor."""

    # The class of this device. Note the value should come from the homeassistant.const
    # module. More information on the available devices classes can be seen here:
    # https://developers.home-assistant.io/docs/core/entity/sensor
    device_class = SensorDeviceClass.VOLTAGE

    # The unit of measurement for this entity. As it's a DEVICE_CLASS_BATTERY, this
    # should be PERCENTAGE. A number of units are supported by HA, for some
    # examples, see:
    # https://developers.home-assistant.io/docs/core/entity/sensor#available-device-classes
    _attr_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 1
    _sensor_option_display_precision = 1

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)

        # As per the sensor, this must be a unique value within this domain. This is done
        # by using the device ID, and appending "_battery"
        # self._attr_native_value = None
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_battery"

        # The name of the entity
        self._attr_name = f"{self._inverter_device.name} Battery Voltage"

        # self._state = 0

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = resolve_battery_voltage(self.data, self._inverter_device.device_data)
        self.async_write_ha_state()


class PVPowerSensor(SensorBase):
    """Representation of a Sensor."""

    # The class of this device. Note the value should come from the homeassistant.const
    # module. More information on the available devices classes can be seen here:
    # https://developers.home-assistant.io/docs/core/entity/sensor
    device_class = SensorDeviceClass.POWER

    # The unit of measurement for this entity. As it's a DEVICE_CLASS_BATTERY, this
    # should be PERCENTAGE. A number of units are supported by HA, for some
    # examples, see:
    # https://developers.home-assistant.io/docs/core/entity/sensor#available-device-classes
    _attr_unit_of_measurement = UnitOfPower.WATT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)

        # As per the sensor, this must be a unique value within this domain. This is done
        # by using the device ID, and appending "_battery"
        # self._attr_native_value = None
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_pv_power"

        # The name of the entity
        self._attr_name = f"{self._inverter_device.name} PV Power"

        # self._state = 0

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data
        device_data = self._inverter_device.device_data
        self._attr_native_value = resolve_pv_power(data, device_data)
        self.async_write_ha_state()


class PVVoltageSensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.VOLTAGE
    _attr_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_pv_voltage"
        self._attr_name = f"{self._inverter_device.name} PV Voltage"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data
        device_data = self._inverter_device.device_data
        self._attr_native_value = resolve_pv_voltage(data, device_data)
        self.async_write_ha_state()


class GridInputVoltageSensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.VOLTAGE
    _attr_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_grid_in_voltage"
        self._attr_name = f"{self._inverter_device.name} Grid In Voltage"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data
        device_data = self._inverter_device.device_data
        self._attr_native_value = resolve_grid_input_voltage(data, device_data)
        self.async_write_ha_state()


class InverterOutputVoltageSensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.VOLTAGE
    _attr_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_inverter_out_voltage"
        self._attr_name = f"{self._inverter_device.name} Inverter Out Voltage"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data
        device_data = self._inverter_device.device_data
        self._attr_native_value = resolve_grid_output_voltage(data, device_data)
        self.async_write_ha_state()


class InverterOutputPowerSensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.POWER
    _attr_unit_of_measurement = UnitOfPower.WATT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_inverter_out_power"
        self._attr_name = f"{self._inverter_device.name} Inverter Out Power"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data
        device_data = self._inverter_device.device_data
        self._attr_native_value = resolve_active_load_power(data, device_data)
        self.async_write_ha_state()


class InverterLoadSensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.POWER_FACTOR
    _attr_unit_of_measurement = PERCENTAGE
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_inverter_load"
        self._attr_name = f"{self._inverter_device.name} Inverter Load"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data
        device_data = self._inverter_device.device_data
        self._attr_native_value = resolve_active_load_percentage(data, device_data)
        self.async_write_ha_state()


class BatteryCapacitySensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.BATTERY
    _attr_unit_of_measurement = PERCENTAGE
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_battery_capacity"
        self._attr_name = f"{self._inverter_device.name} Battery Capacity"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data
        device_data = self._inverter_device.device_data
        self._attr_native_value = resolve_battery_capacity(data, device_data)
        self.async_write_ha_state()


class GridInputPowerSensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.POWER
    _attr_unit_of_measurement = UnitOfPower.WATT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_grid_in_power"
        self._attr_name = f"{self._inverter_device.name} Grid In Power"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data
        device_data = self._inverter_device.device_data
        self._attr_native_value = resolve_grid_in_power(data, device_data)
        self.async_write_ha_state()


class GridInputFrequencySensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.FREQUENCY
    _attr_unit_of_measurement = UnitOfFrequency.HERTZ
    _attr_native_unit_of_measurement = UnitOfFrequency.HERTZ
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 2
    _sensor_option_display_precision = 2

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_grid_in_frequency"
        self._attr_name = f"{self._inverter_device.name} Grid In Frequency"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data
        device_data = self._inverter_device.device_data
        self._attr_native_value = resolve_grid_frequency(data, device_data)
        self.async_write_ha_state()


class BatteryChargeSensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.CURRENT
    _attr_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_suggested_display_precision = 1
    _sensor_option_display_precision = 1

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_battery_charge_current"
        self._attr_name = f"{self._inverter_device.name} Battery Charge Current"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        data = self.data
        self._attr_native_value = resolve_battery_charging_current(data, self._inverter_device.device_data)
        self.async_write_ha_state()


class BatteryDischargeSensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.CURRENT
    _attr_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_suggested_display_precision = 1
    _sensor_option_display_precision = 1

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_battery_discharge_current"
        self._attr_name = f"{self._inverter_device.name} Battery Discharge Current"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = resolve_battery_discharge_current(self.data, self._inverter_device.device_data)
        self.async_write_ha_state()


class BatteryDischargePowerSensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.POWER
    _attr_unit_of_measurement = UnitOfPower.WATT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_battery_discharge_power"
        self._attr_name = f"{self._inverter_device.name} Battery Discharge Power"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data
        device_data = self._inverter_device.device_data

        self._attr_native_value = resolve_battery_discharge_power(data, device_data)
        self.async_write_ha_state()


class BatteryChargePowerSensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.POWER
    _attr_unit_of_measurement = UnitOfPower.WATT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_battery_charge_power"
        self._attr_name = f"{self._inverter_device.name} Battery Charge Power"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data
        device_data = self._inverter_device.device_data
        self._attr_native_value = resolve_battery_charging_power(data, device_data)
        self.async_write_ha_state()


class PVPowerTotalSensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.ENERGY
    state_class = SensorStateClass.TOTAL
    _attr_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 3

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_pv_total_energy"
        self._attr_name = f"{self._inverter_device.name} PV Total Energy"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.data['device']['energyTotal']
        self.async_write_ha_state()


class PVEnergySensor(MyEnergySensor):
    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_pv_in_energy"
        self._attr_name = f"{self._inverter_device.name} PV In Energy"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data
        device_data = self._inverter_device.device_data

        now = datetime.now()
        elapsed_seconds = int(now.timestamp() - self._prev_value_timestamp.timestamp())
        current_value = resolve_pv_power(data, device_data)

        if self._prev_value is not None:
            self._attr_native_value += (elapsed_seconds / 3600) * (self._prev_value + current_value) / 2
        self._prev_value = current_value
        self._prev_value_timestamp = now
        self.async_write_ha_state()


class InverterStatusSensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.ENUM
    options = ['NORMAL', 'OFFLINE', 'FAULT', 'STANDBY', 'WARNING']
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_status"
        self._attr_name = f"{self._inverter_device.name} Status"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        self._attr_native_value = self.options[
            self.data['device']['status']]
        self.async_write_ha_state()


class InverterConfigBTUtilityChargeSensor(SensorBase):
    """Representation of a Sensor."""
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    device_class = SensorDeviceClass.CURRENT
    _attr_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_config_bt_utility_charge_current"
        self._attr_name = f"{self._inverter_device.name} Battery Utility Charge Current"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        self._attr_native_value = \
            next((x for x in self.data['last_data']['pars']['bt_'] if
                  x['id'] == 'bt_utility_charge'), {'val': None})['val']
        self.async_write_ha_state()


class InverterConfigBTTotalChargeSensor(SensorBase):
    """Representation of a Sensor."""
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    device_class = SensorDeviceClass.CURRENT
    _attr_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_config_bt_total_charge_current"
        self._attr_name = f"{self._inverter_device.name} Battery Total Charge Current"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        self._attr_native_value = \
            next((x for x in self.data['last_data']['pars']['bt_'] if
                  x['id'] == 'bt_total_charge_current'), {'val': None})['val']
        self.async_write_ha_state()


class InverterConfigBTCutoffSensor(SensorBase):
    """Representation of a Sensor."""
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    device_class = SensorDeviceClass.VOLTAGE
    _attr_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_config_bt_cutoff_voltage"
        self._attr_name = f"{self._inverter_device.name} Battery Cutoff Voltage"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        self._attr_native_value = \
            next((x for x in self.data['last_data']['pars']['bt_'] if
                  x['id'] == 'bt_battery_cut_off_voltage'), {'val': None})['val']
        self.async_write_ha_state()


class InverterNominalOutPowerSensor(SensorBase):
    """Representation of a Sensor."""
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    device_class = SensorDeviceClass.POWER
    _attr_unit_of_measurement = UnitOfPower.WATT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_suggested_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_nominal_out_power"
        self._attr_name = f"{self._inverter_device.name} Nominal Out Power"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data['last_data']['pars']
        if 'sy_' not in data:
            self._attr_native_value = None
        else:
            self._attr_native_value = \
                next((x for x in data['sy_'] if
                      x['id'] == 'sy_nonimal_output_active_power'), {'val': None})['val']
        self.async_write_ha_state()


class InverterRatedBatteryVoltageSensor(SensorBase):
    """Representation of a Sensor."""
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    device_class = SensorDeviceClass.VOLTAGE
    _attr_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_rated_battery_voltage"
        self._attr_name = f"{self._inverter_device.name} Rated Battery Voltage"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data['last_data']['pars']
        if 'sy_' not in data:
            self._attr_native_value = None
        else:
            self._attr_native_value = \
                next((x for x in data['sy_'] if
                      x['id'] == 'sy_rated_battery_voltage'), {'val': None})['val']
        self.async_write_ha_state()


class InverterComebackUtilityVoltageSensor(SensorBase):
    """Representation of a Sensor."""
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    device_class = SensorDeviceClass.VOLTAGE
    _attr_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 1

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_comeback_utility_voltage"
        self._attr_name = f"{self._inverter_device.name} Comeback Utility"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data['last_data']['pars']
        if 'bt_' not in data:
            self._attr_native_value = None
        else:
            self._attr_native_value = \
                next((x for x in data['bt_'] if
                      x['id'] == 'bt_comeback_utility_iode'), {'val': None})['val']
        self.async_write_ha_state()


class InverterComebackBatteryVoltageSensor(SensorBase):
    """Representation of a Sensor."""
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    device_class = SensorDeviceClass.VOLTAGE
    _attr_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 1

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_comeback_battery_voltage"
        self._attr_name = f"{self._inverter_device.name} Comeback Battery"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data['last_data']['pars']
        if 'bt_' not in data:
            self._attr_native_value = None
        else:
            self._attr_native_value = \
                next((x for x in data['bt_'] if
                      x['id'] == 'bt_battery_mode_voltage'), {'val': None})['val']
        self.async_write_ha_state()


class InverterOutputPrioritySensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.ENUM
    options = ['Utility', 'Solar', 'SBU']
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_output_priority"
        self._attr_name = f"{self._inverter_device.name} Output Priority"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data
        device_data = self._inverter_device.device_data
        value = resolve_output_priority(data, device_data)
        if value in self.options:
            self._attr_native_value = value
        self.async_write_ha_state()


class InverterChargePrioritySensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.ENUM
    options = ['SOLAR_PRIORITY', 'SOLAR_ONLY', 'SOLAR_AND_UTILITY', 'NONE']
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_charge_priority"
        self._attr_name = f"{self._inverter_device.name} Charge Priority"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        data = self.data
        device_data = self._inverter_device.device_data

        self._attr_native_value = resolve_charge_priority(data, device_data)
        self.async_write_ha_state()


class BatteryInEnergySensor(MyEnergySensor):

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_battery_in_energy"
        self._attr_name = f"{self._inverter_device.name} Battery In Energy"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        now = datetime.now()
        elapsed_seconds = int(now.timestamp() - self._prev_value_timestamp.timestamp())
        data = self.data
        device_data = self._inverter_device.device_data

        current_value = resolve_battery_charging_power(data, device_data)
        if self._prev_value is not None:
            self._attr_native_value += (elapsed_seconds / 3600) * (self._prev_value + current_value) / 2
        self._prev_value = current_value
        self._prev_value_timestamp = now
        self.async_write_ha_state()


class BatteryOutEnergySensor(MyEnergySensor):

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_battery_out_energy"
        self._attr_name = f"{self._inverter_device.name} Battery Out Energy"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        now = datetime.now()
        elapsed_seconds = int(now.timestamp() - self._prev_value_timestamp.timestamp())
        data = self.data
        current_value = resolve_battery_discharge_power(data, self._inverter_device.device_data)
        if self._prev_value is not None:
            self._attr_native_value += (elapsed_seconds / 3600) * (self._prev_value + current_value) / 2
        self._prev_value = current_value
        self._prev_value_timestamp = now
        self.async_write_ha_state()


class InverterOutEnergySensor(MyEnergySensor):

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_inverter_out_energy"
        self._attr_name = f"{self._inverter_device.name} Inverter Out Energy"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        now = datetime.now()
        elapsed_seconds = int(now.timestamp() - self._prev_value_timestamp.timestamp())
        data = self.data
        device_data = self._inverter_device.device_data
        current_val = resolve_active_load_power(data, device_data)
        if self._prev_value is not None:
            self._attr_native_value += (elapsed_seconds / 3600) * (self._prev_value + current_val) / 2
        self._prev_value = current_val
        self._prev_value_timestamp = now
        self.async_write_ha_state()


class InverterInEnergySensor(MyEnergySensor):

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_inverter_in_energy"
        self._attr_name = f"{self._inverter_device.name} Inverter In Energy"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        now = datetime.now()
        elapsed_seconds = int(now.timestamp() - self._prev_value_timestamp.timestamp())
        data = self.data
        device_data = self._inverter_device.device_data
        current_val = resolve_grid_in_power(data, device_data)
        if self._prev_value is not None:
            self._attr_native_value += (elapsed_seconds / 3600) * (self._prev_value + current_val) / 2
        self._prev_value = current_val
        self._prev_value_timestamp = now
        self.async_write_ha_state()


class InverterDCTemperatureSensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.TEMPERATURE
    _attr_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_inverter_dc_temperature"
        self._attr_name = f"{self._inverter_device.name} Inverter DC Temperature"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data
        device_data = self._inverter_device.device_data
        self._attr_native_value = resolve_dc_module_temperature(data, device_data)
        self.async_write_ha_state()


class InverterInvTemperatureSensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.TEMPERATURE
    _attr_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_inverter_inv_temperature"
        self._attr_name = f"{self._inverter_device.name} Inverter INV Temperature"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data
        device_data = self._inverter_device.device_data
        self._attr_native_value = resolve_inv_temperature(data, device_data)
        self.async_write_ha_state()


class DessSensorSource(Enum):
    PARS_ES = 'pars'
    SP_LAST_DATA = 'last_data'
    ENERGY_FLOW = 'energy_flow'


class InverterDynamicSensor(SensorBase):
    """Representation of a Sensor."""
    # device_class = SensorDeviceClass.TEMPERATURE
    # _attr_unit_of_measurement = UnitOfTemperature.CELSIUS
    # _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    # _attr_suggested_display_precision = 0
    # _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator, sensor_data,
                 sensor_source: DessSensorSource):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        # "par": "bt_battery_charging_current",
        # "name": "Battery Charging Current",
        # "val": "0.0000",
        # "unit": "A"
        self._sensor_par_id = sensor_data['par']
        self._sensor_source = sensor_source
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_raw_{sensor_data['par']}"
        self._attr_name = f"{self._inverter_device.name} Raw {sensor_data['name']}"

        device_class_map = {
            'kW': SensorDeviceClass.POWER,
            'W': SensorDeviceClass.POWER,
            'A': SensorDeviceClass.CURRENT,
            'V': SensorDeviceClass.VOLTAGE,
            'HZ': SensorDeviceClass.FREQUENCY,
            '%': SensorDeviceClass.BATTERY,
        }
        unit_map = {
            'kW': UnitOfPower.KILO_WATT,
            'W': UnitOfPower.WATT,
            'A': UnitOfElectricCurrent.AMPERE,
            'V': UnitOfElectricPotential.VOLT,
            'HZ': UnitOfFrequency.HERTZ,
            '%': PERCENTAGE,
        }
        display_unit = unit_map[sensor_data['unit']]
        self._attr_device_class = device_class_map[sensor_data['unit']]
        # self._unit_of_measurement = sensor_data['unit']
        self._attr_unit_of_measurement = display_unit
        self._attr_native_unit_of_measurement = display_unit
        self._attr_native_value = float(sensor_data['val'])
        # self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data

        def get_prefix(s):
            return s.split("_", 1)[0] + "_"

        match self._sensor_source:
            case DessSensorSource.PARS_ES:
                self._attr_native_value = float(
                    next((x for x in data['pars']['parameter'] if x['par'] == self._sensor_par_id), {'val': '0'})['val']
                )
            case DessSensorSource.SP_LAST_DATA:
                key = get_prefix(self._sensor_par_id)
                self._attr_native_value = float(
                    next((x for x in data['last_data']['pars'][key] if x['id'] == self._sensor_par_id), {'val': '0'})[
                        'val']
                )
        self.async_write_ha_state()
