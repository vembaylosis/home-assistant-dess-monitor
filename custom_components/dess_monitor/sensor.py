"""Platform for sensor integration."""
# This file shows the setup for the sensors associated with the cover.
# They are setup in the same way with the call to the async_setup_entry function
# via HA from the module __init__. Each sensor has a device_class, this tells HA how
# to display it in the UI (for know types). The unit_of_measurement property tells HA
# what the unit is, so it can display the correct range. For predefined types (such as
# battery), the unit_of_measurement should match what's expected.

from homeassistant.components.sensor import (
    SensorDeviceClass, SensorEntity, SensorStateClass,
)
from homeassistant.const import (
    UnitOfPower, UnitOfElectricPotential, UnitOfElectricCurrent, UnitOfEnergy, EntityCategory
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HubConfigEntry, MyCoordinator
from .const import DOMAIN
from .hub import InverterDevice


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
        new_devices.append(BatterySensor(item, hub.coordinator))
        new_devices.append(PVSensor(item, hub.coordinator))
        new_devices.append(PVVoltageSensor(item, hub.coordinator))
        new_devices.append(GridInputVoltageSensor(item, hub.coordinator))
        new_devices.append(InverterOutputVoltageSensor(item, hub.coordinator))
        new_devices.append(BatteryChargeSensor(item, hub.coordinator))
        new_devices.append(BatteryChargePowerSensor(item, hub.coordinator))
        new_devices.append(BatteryDischargeSensor(item, hub.coordinator))
        new_devices.append(BatteryDischargePowerSensor(item, hub.coordinator))
        new_devices.append(PVPowerTotalSensor(item, hub.coordinator))
        new_devices.append(InverterStatusSensor(item, hub.coordinator))
        new_devices.append(InverterConfigBTUtilityChargeSensor(item, hub.coordinator))
        new_devices.append(InverterConfigBTTotalChargeSensor(item, hub.coordinator))
        new_devices.append(InverterConfigBTCutoffSensor(item, hub.coordinator))
        new_devices.append(InverterOutputPrioritySensor(item, hub.coordinator))
        new_devices.append(InverterChargePrioritySensor(item, hub.coordinator))
        new_devices.append(InverterOutputPowerSensor(item, hub.coordinator))
    if new_devices:
        async_add_entities(new_devices)


# This base class shows the common properties and methods for a sensor as used in this
# example. See each sensor for further details about properties and methods that
# have been overridden.
class SensorBase(CoordinatorEntity, SensorEntity):
    # should_poll = True

    def __init__(self, inverter_device, coordinator: MyCoordinator):
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

    # async def async_added_to_hass(self):
    #     """Run when this Entity has been added to HA."""
    #     # Sensors should also register callbacks to HA when their state changes
    #     self._inverter_device.register_callback(self.async_write_ha_state)
    #
    # async def async_will_remove_from_hass(self):
    #     """Entity being removed from hass."""
    #     # The opposite of async_added_to_hass. Remove any registered call backs here.
    #     self._inverter_device.remove_callback(self.async_write_ha_state)


class BatterySensor(SensorBase):
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
        self._attr_name = f"{self._inverter_device.name} Battery"

        # self._state = 0

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = \
            next((x for x in self.coordinator.data[self._inverter_device.inverter_id]['last_data']['pars']['bt_'] if
                  x['id'] == 'bt_battery_voltage'), {'val': None})['val']
        self.async_write_ha_state()


class PVSensor(SensorBase):
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
        # print('_handle_coordinator_update', self._inverter_device.roller_id, self.coordinator.data[self._inverter_device.roller_id])
        self._attr_native_value = \
            next((x for x in self.coordinator.data[self._inverter_device.inverter_id]['last_data']['pars']['pv_'] if
                  x['id'] == 'pv_output_power'), {'val': 0})['val']
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
        self._attr_native_value = \
            next((x for x in self.coordinator.data[self._inverter_device.inverter_id]['last_data']['pars']['pv_'] if
                  x['id'] == 'pv_input_voltage' or x['id'] == 'pv_voltage'), {'val': None})['val']
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
        self._attr_native_value = \
            next((x for x in self.coordinator.data[self._inverter_device.inverter_id]['last_data']['pars']['gd_'] if
                  x['id'] == 'gd_ac_input_voltage' or x['id'] == 'gd_grid_voltage'), {'val': None})['val']
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
        self._attr_native_value = \
            next((x for x in self.coordinator.data[self._inverter_device.inverter_id]['last_data']['pars']['bc_'] if
                  x['id'] == 'bc_output_voltage'), {'val': None})['val']
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
        self._attr_native_value = \
            float(next((x for x in self.coordinator.data[self._inverter_device.inverter_id]['energy_flow']['bc_status'] if
                        x['par'] == 'load_active_power'), {'val': '0'})['val']) * 1000
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
        self._attr_native_value = \
            next((x for x in self.coordinator.data[self._inverter_device.inverter_id]['last_data']['pars']['bt_'] if
                  x['id'] == 'bt_battery_charging_current'), {'val': 0})['val']
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
        self._attr_native_value = \
            next((x for x in self.coordinator.data[self._inverter_device.inverter_id]['last_data']['pars']['bt_'] if
                  x['id'] == 'bt_battery_discharge_current'), {'val': 0})['val']
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
        self._attr_native_value = \
            float(next((x for x in self.coordinator.data[self._inverter_device.inverter_id]['last_data']['pars']['bt_'] if
                        x['id'] == 'bt_battery_discharge_current'), {'val': 0})['val']) * \
            float(next((x for x in self.coordinator.data[self._inverter_device.inverter_id]['last_data']['pars']['bt_'] if
                        x['id'] == 'bt_battery_voltage'), {'val': 0})['val'])
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
        self._attr_native_value = \
            float(next((x for x in self.coordinator.data[self._inverter_device.inverter_id]['last_data']['pars']['bt_'] if
                        x['id'] == 'bt_battery_charging_current'), {'val': 0})['val']) * \
            float(next((x for x in self.coordinator.data[self._inverter_device.inverter_id]['last_data']['pars']['bt_'] if
                        x['id'] == 'bt_vulk_charging_voltage'), {'val': 0})['val'])
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
        self._attr_native_value = self.coordinator.data[self._inverter_device.inverter_id]['device']['energyTotal']
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

        self._attr_native_value = self.options[self.coordinator.data[self._inverter_device.inverter_id]['device']['status']]
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
            next((x for x in self.coordinator.data[self._inverter_device.inverter_id]['last_data']['pars']['bt_'] if
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
            next((x for x in self.coordinator.data[self._inverter_device.inverter_id]['last_data']['pars']['bt_'] if
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
            next((x for x in self.coordinator.data[self._inverter_device.inverter_id]['last_data']['pars']['bt_'] if
                  x['id'] == 'bt_battery_cut_off_voltage'), {'val': None})['val']
        self.async_write_ha_state()


class InverterOutputPrioritySensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.ENUM
    options = ['SBU', 'SOL', 'UTILITY']
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_output_priority"
        self._attr_name = f"{self._inverter_device.name} Output Priority"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        self._attr_native_value = \
            next((x for x in self.coordinator.data[self._inverter_device.inverter_id]['last_data']['pars']['bc_'] if
                  x['id'] == 'bc_output_source_priority'), {'val': None})['val']
        self.async_write_ha_state()


class InverterChargePrioritySensor(SensorBase):
    """Representation of a Sensor."""
    device_class = SensorDeviceClass.ENUM
    options = ['SOLAR_PRIORITY', 'SOLAR_ONLY', 'SOLAR_AND_UTILITY']
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, inverter_device: InverterDevice, coordinator: MyCoordinator):
        """Initialize the sensor."""
        super().__init__(inverter_device, coordinator)
        self._attr_unique_id = f"{self._inverter_device.inverter_id}_charge_priority"
        self._attr_name = f"{self._inverter_device.name} Charge Priority"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        mapper = {
            'Solar priority': 'SOLAR_PRIORITY',
            'Solar and mains': 'SOLAR_AND_UTILITY',
            'Solar only': 'SOLAR_ONLY',
            None: None,
        }
        self._attr_native_value = \
            mapper[next((x for x in self.coordinator.data[self._inverter_device.inverter_id]['last_data']['pars']['bt_'] if
                         x['id'] == 'bt_charger_source_priority'), {'val': None})['val']]
        self.async_write_ha_state()

# class BTSensor(SensorBase):
#     """Representation of a Sensor."""
#
#     # # The class of this device. Note the value should come from the homeassistant.const
#     # # module. More information on the available devices classes can be seen here:
#     # # https://developers.home-assistant.io/docs/core/entity/sensor
#     # device_class = SensorDeviceClass.VOLTAGE
#
#     def __init__(self, inverter_device: Roller, coordinator: MyCoordinator, pars):
#         """Initialize the sensor."""
#         super().__init__(inverter_device, coordinator)
#
#         # As per the sensor, this must be a unique value within this domain. This is done
#         # by using the device ID, and appending "_battery"
#         # self._attr_native_value = None
#         self._attr_unique_id = f"{self._inverter_device.roller_id}_{pars['id']}"
#         # self.device_class = SensorDeviceClass.VOLTAGE
#         self._attr_device_class = SensorDeviceClass.VOLTAGE
#         if pars['unit'] == 'A':
#             self._attr_device_class = SensorDeviceClass.CURRENT
#         if pars['unit'] == '%':
#             self._attr_device_class = SensorDeviceClass.BATTERY
#         if pars['unit'] == 'min':
#             self._attr_device_class = SensorDeviceClass.DURATION
#         if pars['unit'] == 'day':
#             self._attr_device_class = SensorDeviceClass.DURATION
#
#         self._attr_native_unit_of_measurement = pars['unit']
#         self._attr_unit_of_measurement = pars['unit']
#         # The name of the entity
#         self._attr_name = f"{self._inverter_device.name} {pars['par']}"
#         self._state = pars['val']
#         self._attr_native_value = pars['val']
#
#     @callback
#     def _handle_coordinator_update(self) -> None:
#         """Handle updated data from the coordinator."""
#         # print('_handle_coordinator_update', self._inverter_device.roller_id, self.coordinator.data[self._inverter_device.roller_id])
#         self._attr_native_value = \
#             next((x for x in self.coordinator.data[self._inverter_device.roller_id]['last_data']['pars']['pv_'] if
#                   x['id'] == 'pv_output_power'))['val']
#         self.async_write_ha_state()

# class PVSensor(CoordinatorEntity, SensorEntity):
#     """Representation of a Sensor."""
#     device_class = SensorDeviceClass.VOLTAGE
#
#     # The unit of measurement for this entity. As it's a DEVICE_CLASS_BATTERY, this
#     # should be PERCENTAGE. A number of units are supported by HA, for some
#     # examples, see:
#     # https://developers.home-assistant.io/docs/core/entity/sensor#available-device-classes
#     _attr_unit_of_measurement = 'V'
#
#
#     def __init__(self, inverter_device: Roller, coordinator):
#         """Pass coordinator to CoordinatorEntity."""
#         super().__init__(coordinator)
#         self._inverter_device = inverter_device
#
#     @callback
#     def _handle_coordinator_update(self) -> None:
#         """Handle updated data from the coordinator."""
#         print('_handle_coordinator_update')
#         self._attr_native_value = '124'
#         self.async_write_ha_state()
#
#     @property
#     def device_info(self) -> DeviceInfo:
#         """Information about this entity/device."""
#         return {
#             "identifiers": {(DOMAIN, self._inverter_device.roller_id)},
#             # If desired, the name for the device could be different to the entity
#             "name": self._inverter_device.name,
#             "sw_version": self._inverter_device.firmware_version,
#             "model": self._inverter_device.device_data['sn'],
#             "serial_number": self._inverter_device.device_data['pn'],
#         }
