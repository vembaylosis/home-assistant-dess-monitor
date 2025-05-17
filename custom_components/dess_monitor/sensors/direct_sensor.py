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


class DirectTypedSensorBase(DirectSensorBase):
    """Абстрактный базовый класс для сенсоров, получающих значение по ключу."""

    def __init__(
            self,
            inverter_device: InverterDevice,
            coordinator: DirectCoordinator,
            data_section: str,
            data_key: str,
            sensor_suffix: str = "",
            name_suffix: str = ""
    ):
        super().__init__(inverter_device, coordinator)
        self.data_section = data_section
        self.data_key = data_key

        suffix = sensor_suffix or data_key
        name_part = name_suffix or data_key.replace('_', ' ').title()

        self._attr_unique_id = f"{self._inverter_device.inverter_id}_direct_{suffix}"
        self._attr_name = f"{self._inverter_device.name} Direct {name_part}"

    @callback
    def _handle_coordinator_update(self) -> None:
        section = self.data.get(self.data_section, {})
        raw_value = section.get(self.data_key)

        if raw_value is not None:
            try:
                self._attr_native_value = float(raw_value)
            except (ValueError, TypeError):
                self._attr_native_value = None
        else:
            self._attr_native_value = None

        self.async_write_ha_state()


class DirectWattSensorBase(DirectTypedSensorBase):
    device_class = SensorDeviceClass.POWER
    _attr_unit_of_measurement = UnitOfPower.WATT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0


class DirectTemperatureSensorBase(DirectTypedSensorBase):
    device_class = SensorDeviceClass.TEMPERATURE
    _attr_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0


class DirectVoltageSensorBase(DirectTypedSensorBase):
    device_class = SensorDeviceClass.VOLTAGE
    _attr_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 1
    _sensor_option_display_precision = 1


class DirectCurrentSensorBase(DirectTypedSensorBase):
    """Базовый сенсор силы тока (A) для direct-протокола."""

    device_class = SensorDeviceClass.CURRENT
    _attr_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0


class DirectPVPowerSensor(DirectWattSensorBase):
    def __init__(self, inverter_device: InverterDevice, coordinator: DirectCoordinator):
        super().__init__(
            inverter_device,
            coordinator,
            data_section="qpigs",
            data_key="pv_charging_power",
            sensor_suffix="pv_power",
            name_suffix="PV Power"
        )


class DirectPV2PowerSensor(DirectWattSensorBase):  # можно и от DirectSensorBase, если не нужен unit/class
    def __init__(self, inverter_device: InverterDevice, coordinator: DirectCoordinator):
        super().__init__(
            inverter_device,
            coordinator,
            data_section="unused",  # не используется, можно передать любой
            data_key="unused",
            sensor_suffix="pv2_power",
            name_suffix="PV2 Power"
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        try:
            qpigs2 = self.data["qpigs2"]
            self._attr_native_value = float(qpigs2["pv_current"]) * float(qpigs2["pv_voltage"])
        except (KeyError, ValueError, TypeError):
            self._attr_native_value = None

        self.async_write_ha_state()


class DirectPVVoltageSensor(DirectVoltageSensorBase):
    def __init__(self, inverter_device: InverterDevice, coordinator: DirectCoordinator):
        super().__init__(
            inverter_device,
            coordinator,
            data_section="qpigs",
            data_key="pv_input_voltage",
            sensor_suffix="pv_voltage",
            name_suffix="PV Voltage"
        )


class DirectPV2VoltageSensor(DirectVoltageSensorBase):
    def __init__(self, inverter_device: InverterDevice, coordinator: DirectCoordinator):
        super().__init__(
            inverter_device,
            coordinator,
            data_section="qpigs2",
            data_key="pv_voltage",
            sensor_suffix="pv2_voltage",
            name_suffix="PV2 Voltage"
        )


class DirectPV2CurrentSensor(DirectCurrentSensorBase):
    def __init__(self, inverter_device: InverterDevice, coordinator: DirectCoordinator):
        super().__init__(
            inverter_device,
            coordinator,
            data_section="qpigs2",
            data_key="pv_current",
            sensor_suffix="pv2_current",
            name_suffix="PV2 Current"
        )


class DirectBatteryVoltageSensor(DirectVoltageSensorBase):
    def __init__(self, inverter_device: InverterDevice, coordinator: DirectCoordinator):
        super().__init__(
            inverter_device,
            coordinator,
            data_section="qpigs",
            data_key="battery_voltage",
            sensor_suffix="battery",
            name_suffix="Battery Voltage"
        )


class DirectInverterOutputPowerSensor(DirectWattSensorBase):
    def __init__(self, inverter_device: InverterDevice, coordinator: DirectCoordinator):
        super().__init__(
            inverter_device,
            coordinator,
            data_section="qpigs",
            data_key="output_active_power",
            sensor_suffix="inverter_out_power",
            name_suffix="Inverter Out Power"
        )


class DirectInverterTemperatureSensor(DirectTemperatureSensorBase):
    def __init__(self, inverter_device: InverterDevice, coordinator: DirectCoordinator):
        super().__init__(
            inverter_device,
            coordinator,
            data_section="qpigs",
            data_key="inverter_heat_sink_temperature",
            sensor_suffix="inverter_temperature",
            name_suffix="Inverter Temperature"
        )


class DirectGridVoltageSensor(DirectVoltageSensorBase):
    def __init__(self, inverter_device, coordinator):
        super().__init__(inverter_device, coordinator, "qpigs", "grid_voltage", "grid_voltage", "Grid Voltage")


class DirectGridFrequencySensor(DirectTypedSensorBase):
    device_class = SensorDeviceClass.FREQUENCY
    _attr_unit_of_measurement = "Hz"
    _attr_native_unit_of_measurement = "Hz"
    _attr_suggested_display_precision = 1
    _sensor_option_display_precision = 1

    def __init__(self, inverter_device, coordinator):
        super().__init__(inverter_device, coordinator, "qpigs", "grid_frequency", "grid_freq", "Grid Frequency")


class DirectACOutputVoltageSensor(DirectVoltageSensorBase):
    def __init__(self, inverter_device, coordinator):
        super().__init__(inverter_device, coordinator, "qpigs", "ac_output_voltage", "ac_output_voltage",
                         "AC Output Voltage")


class DirectACOutputFrequencySensor(DirectTypedSensorBase):
    device_class = SensorDeviceClass.FREQUENCY
    _attr_unit_of_measurement = "Hz"
    _attr_native_unit_of_measurement = "Hz"
    _attr_suggested_display_precision = 1
    _sensor_option_display_precision = 1

    def __init__(self, inverter_device, coordinator):
        super().__init__(inverter_device, coordinator, "qpigs", "ac_output_frequency", "ac_output_freq",
                         "AC Output Frequency")


class DirectOutputApparentPowerSensor(DirectWattSensorBase):
    def __init__(self, inverter_device, coordinator):
        super().__init__(inverter_device, coordinator, "qpigs", "output_apparent_power", "output_apparent_power",
                         "Apparent Power")


class DirectLoadPercentSensor(DirectTypedSensorBase):
    device_class = SensorDeviceClass.POWER_FACTOR
    _attr_unit_of_measurement = "%"
    _attr_native_unit_of_measurement = "%"
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device, coordinator):
        super().__init__(inverter_device, coordinator, "qpigs", "load_percent", "load_percent", "Load Percent")


class DirectBusVoltageSensor(DirectVoltageSensorBase):
    def __init__(self, inverter_device, coordinator):
        super().__init__(inverter_device, coordinator, "qpigs", "bus_voltage", "bus_voltage", "Bus Voltage")


class DirectBatteryChargingCurrentSensor(DirectCurrentSensorBase):
    def __init__(self, inverter_device, coordinator):
        super().__init__(inverter_device, coordinator, "qpigs", "battery_charging_current", "battery_charging_current",
                         "Battery Charging Current")


class DirectBatteryDischargeCurrentSensor(DirectCurrentSensorBase):
    def __init__(self, inverter_device, coordinator):
        super().__init__(inverter_device, coordinator, "qpigs", "battery_discharge_current",
                         "battery_discharge_current", "Battery Discharge Current")


class DirectBatteryCapacitySensor(DirectTypedSensorBase):
    _attr_unit_of_measurement = "%"
    _attr_native_unit_of_measurement = "%"
    _attr_suggested_display_precision = 0
    _sensor_option_display_precision = 0

    def __init__(self, inverter_device, coordinator):
        super().__init__(inverter_device, coordinator, "qpigs", "battery_capacity", "battery_capacity",
                         "Battery Capacity")


class DirectPVInputCurrentSensor(DirectCurrentSensorBase):
    def __init__(self, inverter_device, coordinator):
        super().__init__(inverter_device, coordinator, "qpigs", "pv_input_current", "pv_input_current",
                         "PV Input Current")


class DirectSCCBatteryVoltageSensor(DirectVoltageSensorBase):
    def __init__(self, inverter_device, coordinator):
        super().__init__(inverter_device, coordinator, "qpigs", "scc_battery_voltage", "scc_batt_voltage",
                         "SCC Battery Voltage")

DIRECT_SENSORS = [
    DirectPVPowerSensor,
    DirectPV2PowerSensor,
    DirectPVVoltageSensor,
    DirectPV2VoltageSensor,
    DirectPVInputCurrentSensor,
    DirectPV2CurrentSensor,
    DirectBatteryVoltageSensor,
    DirectBatteryChargingCurrentSensor,
    DirectBatteryDischargeCurrentSensor,
    DirectBatteryCapacitySensor,
    DirectInverterOutputPowerSensor,
    DirectInverterTemperatureSensor,
    DirectGridVoltageSensor,
    DirectGridFrequencySensor,
    DirectACOutputVoltageSensor,
    DirectACOutputFrequencySensor,
    DirectOutputApparentPowerSensor,
    DirectLoadPercentSensor,
    DirectBusVoltageSensor,
    DirectSCCBatteryVoltageSensor,
]