"""Platform for sensor integration."""
from datetime import datetime

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
        # grid sensors
        new_devices.append(GridInputVoltageSensor(item, hub.coordinator))
        new_devices.append(GridInputFrequencySensor(item, hub.coordinator))
        new_devices.append(GridInputPowerSensor(item, hub.coordinator))
        # pv sensors
        new_devices.append(PVPowerSensor(item, hub.coordinator))
        new_devices.append(PVPowerTotalSensor(item, hub.coordinator))  # deprecated
        new_devices.append(PVEnergySensor(item, hub.coordinator))
        new_devices.append(PVVoltageSensor(item, hub.coordinator))
        # battery sensors
        new_devices.append(BatteryVoltageSensor(item, hub.coordinator))
        new_devices.append(BatteryChargeSensor(item, hub.coordinator))
        new_devices.append(BatteryChargePowerSensor(item, hub.coordinator))
        new_devices.append(BatteryDischargeSensor(item, hub.coordinator))
        new_devices.append(BatteryDischargePowerSensor(item, hub.coordinator))
        new_devices.append(BatteryInEnergySensor(item, hub.coordinator))
        new_devices.append(BatteryOutEnergySensor(item, hub.coordinator))
        new_devices.append(BatteryCapacitySensor(item, hub.coordinator))
        # inverter sensors
        new_devices.append(InverterStatusSensor(item, hub.coordinator))
        new_devices.append(InverterOutputPrioritySensor(item, hub.coordinator))
        new_devices.append(InverterOutputVoltageSensor(item, hub.coordinator))
        new_devices.append(InverterOutputPowerSensor(item, hub.coordinator))
        new_devices.append(InverterOutEnergySensor(item, hub.coordinator))
        new_devices.append(InverterInEnergySensor(item, hub.coordinator))
        new_devices.append(InverterDCTemperatureSensor(item, hub.coordinator))
        new_devices.append(InverterInvTemperatureSensor(item, hub.coordinator))
        new_devices.append(InverterLoadSensor(item, hub.coordinator))
        # inverter config sensors
        new_devices.append(InverterChargePrioritySensor(item, hub.coordinator))
        new_devices.append(InverterConfigBTUtilityChargeSensor(item, hub.coordinator))
        new_devices.append(InverterConfigBTTotalChargeSensor(item, hub.coordinator))
        new_devices.append(InverterConfigBTCutoffSensor(item, hub.coordinator))
        new_devices.append(InverterNominalOutPowerSensor(item, hub.coordinator))
        new_devices.append(InverterRatedBatteryVoltageSensor(item, hub.coordinator))
        new_devices.append(InverterComebackUtilityVoltageSensor(item, hub.coordinator))
        new_devices.append(InverterComebackBatteryVoltageSensor(item, hub.coordinator))
        if 'raw_sensors' not in config_entry.options:
            continue
        if not config_entry.options.get('raw_sensors', False):
            continue
        if hub.coordinator.data is None or item.inverter_id not in hub.coordinator.data:
            continue
        data = hub.coordinator.data[item.inverter_id]
        allowed_units = [
            'kW',
            'W',
            'A',
            'V'
        ]
        for parameter in data['pars']['parameter']:
            if parameter['unit'] not in allowed_units:
                continue
            new_devices.append(InverterDynamicSensor(item, hub.coordinator, parameter))
    if new_devices:
        async_add_entities(new_devices)


# This base class shows the common properties and methods for a sensor as used in this
# example. See each sensor for further details about properties and methods that
# have been overridden.
class SensorBase(CoordinatorEntity, SensorEntity):
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


class InverterDynamicSensor(SensorBase):
    """Representation of a Sensor."""
    # device_class = SensorDeviceClass.TEMPERATURE
    # _attr_unit_of_measurement = UnitOfTemperature.CELSIUS
    # _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    # _attr_suggested_display_precision = 0
    # _sensor_option_display_precision = 0

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator, sensor_data):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        # "par": "bt_battery_charging_current",
        # "name": "Battery Charging Current",
        # "val": "0.0000",
        # "unit": "A"
        self._sensor_par_id = sensor_data['par']
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_{sensor_data['par']}"
        self._attr_name = f"{self._inverter_device.name} Raw {sensor_data['name']}"

        device_class_map = {
            'kW': SensorDeviceClass.POWER,
            'W': SensorDeviceClass.POWER,
            'A': SensorDeviceClass.CURRENT,
            'V': SensorDeviceClass.VOLTAGE,
        }
        # unit_map = {
        #     'kW': UnitOfPower.KILO_WATT,
        #     'W': UnitOfPower.WATT,
        #     'A': UnitOfElectricCurrent.AMPERE,
        #     'V': UnitOfElectricPotential.VOLT,
        # }
        self._attr_device_class = device_class_map[sensor_data['unit']]
        # self._unit_of_measurement = sensor_data['unit']
        self._attr_unit_of_measurement = sensor_data['unit']
        self._attr_native_unit_of_measurement = sensor_data['unit']
        self._attr_native_value = float(sensor_data['val'])
        # self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data
        # device_data = self._inverter_device.device_data
        self._attr_native_value = float(
            next((x for x in data['pars']['parameter'] if
                  x['par'] == self._sensor_par_id), {'val': '0'})['val'])
        self.async_write_ha_state()
