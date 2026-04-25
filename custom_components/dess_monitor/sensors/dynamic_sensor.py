from enum import Enum

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import EntityCategory, UnitOfPower, UnitOfElectricPotential, UnitOfFrequency, \
    UnitOfElectricCurrent, PERCENTAGE
from homeassistant.core import callback

from custom_components.dess_monitor.api.helpers import safe_float
from custom_components.dess_monitor.coordinators.coordinator import MainCoordinator
from custom_components.dess_monitor.hub import InverterDevice
from custom_components.dess_monitor.sensors.init_sensors import SensorBase


class DessSensorSource(Enum):
    PARS_ES = 'pars'
    SP_LAST_DATA = 'last_data'
    ENERGY_FLOW = 'energy_flow'


class InverterDynamicSensor(SensorBase):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, inverter_device: InverterDevice, coordinator: MainCoordinator, sensor_data,
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
        unit = sensor_data.get('unit')
        display_unit = unit_map.get(unit)
        self._attr_device_class = device_class_map.get(unit)
        self._attr_unit_of_measurement = display_unit
        self._attr_native_unit_of_measurement = display_unit
        self._attr_native_value = safe_float(sensor_data.get('val'), default=None)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.data
        if data is None:
            self._attr_native_value = None
            self.async_write_ha_state()
            return

        def get_prefix(s):
            return s.split("_", 1)[0] + "_"

        try:
            match self._sensor_source:
                case DessSensorSource.PARS_ES:
                    parameter = (data.get('pars') or {}).get('parameter') or []
                    found = next((x for x in parameter if x.get('par') == self._sensor_par_id), None)
                    self._attr_native_value = safe_float(found.get('val'), default=None) if found else None
                case DessSensorSource.SP_LAST_DATA:
                    key = get_prefix(self._sensor_par_id)
                    pars = ((data.get('last_data') or {}).get('pars') or {}).get(key) or []
                    found = next((x for x in pars if x.get('id') == self._sensor_par_id), None)
                    self._attr_native_value = safe_float(found.get('val'), default=None) if found else None
                case _:
                    self._attr_native_value = None
        except Exception:
            self._attr_native_value = None
        self.async_write_ha_state()
