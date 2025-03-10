import json

from custom_components.dess_monitor.api.helpers import *

devcode = 2376

with open(f'devcodes/{devcode}/querySPDeviceLastData.json') as querySPDeviceLastData:
    with open(f'devcodes/{devcode}/webQueryDeviceEnergyFlowEs.json') as webQueryDeviceEnergyFlowEs:
        last_data = json.load(querySPDeviceLastData)
        energy_flow = json.load(webQueryDeviceEnergyFlowEs)
        data = {
            'last_data': last_data['dat'],
            'energy_flow': energy_flow['dat'],
        }
        device_data = {
            'devcode': devcode
        }
        print('resolve_battery_voltage', resolve_battery_voltage(data, device_data))
        print('resolve_grid_in_power', resolve_grid_in_power(data, device_data))
        print('resolve_grid_frequency', resolve_grid_frequency(data, device_data))
        print('resolve_output_priority', resolve_output_priority(data, device_data))
        print('resolve_charge_priority', resolve_charge_priority(data, device_data))
        print('resolve_battery_charging_voltage', resolve_battery_charging_voltage(data, device_data))
        print('resolve_battery_charging_current', resolve_battery_charging_current(data, device_data))
        print('resolve_battery_discharge_current', resolve_battery_discharge_current(data, device_data))
        print('resolve_battery_charging_power', resolve_battery_charging_power(data, device_data))
        print('resolve_battery_discharge_power', resolve_battery_discharge_power(data, device_data))
