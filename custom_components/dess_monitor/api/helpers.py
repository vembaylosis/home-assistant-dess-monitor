from custom_components.dess_monitor.api import set_ctrl_device_param, get_device_ctrl_value


def resolve_battery_charging_current(data, device_data):
    match device_data['devcode']:
        case 2376:
            result = next((x for x in data['last_data']['pars']['bt_'] if
                           x['id'].lower() == 'bt_eybond_read_29'.lower()), None)
            if result is None:
                return None
            value = float(result['val'])
            if value >= 0:
                return value
            else:
                return 0
        case _:
            return \
                float(next(
                    (x for x in data['last_data']['pars']['bt_']
                     if
                     x['id'] == 'bt_battery_charging_current' or x[
                         'par'].lower() == 'Battery charging current'.lower()),
                    {'val': '0'}
                )['val'])


def resolve_battery_charging_voltage(data, device_data):
    match device_data['devcode']:
        case _:
            return \
                float(next((x for x in
                            data['last_data']['pars']['bt_']
                            if
                            x['id'] == 'bt_vulk_charging_voltage'), {'val': '0'})['val'])


def resolve_battery_discharge_current(data, device_data):
    match device_data['devcode']:
        case 2376:
            result = next((x for x in data['last_data']['pars']['bt_'] if
                           x['id'].lower() == 'bt_eybond_read_29'.lower()), None)
            if result is None:
                return None
            value = float(result['val'])
            if value <= 0:
                return abs(value)
            else:
                return 0
        case _:
            return \
                float(next(
                    (x for x in data['last_data']['pars']['bt_']
                     if
                     x['id'] == 'bt_battery_discharge_current' or x['id'] == 'bt_discharge_current' or x[
                         'par'].lower() == 'Battery discharge current'.lower()),
                    {'val': '0'}
                )['val'])


def resolve_battery_voltage(data, device_data):
    match device_data['devcode']:
        case _:
            return \
                float(next((x for x in
                            data['last_data']['pars']['bt_']
                            if
                            x['id'] == 'bt_battery_voltage' or x['par'].lower() == 'Battery Voltage'.lower()),
                           {'val': '0'})['val'])


def resolve_battery_charging_power(data, device_data):
    match device_data['devcode']:
        case 2376:
            result = next((x for x in data['energy_flow']['bt_status'] if x['par'].lower() == 'battery_active_power'),
                          None)
            if result is None:
                return None
            value = float(result['val']) * 1000
            if value >= 0:
                return value
            else:
                return 0
        case _:
            return resolve_battery_charging_current(data, device_data) * (
                        resolve_battery_charging_voltage(data, device_data) or resolve_battery_voltage(data,
                                                                                                       device_data))


def resolve_battery_discharge_power(data, device_data):
    match device_data['devcode']:
        case 2376:
            result = next((x for x in data['energy_flow']['bt_status'] if x['par'].lower() == 'battery_active_power'),
                          None)
            if result is None:
                return None
            value = float(result['val']) * 1000
            if value <= 0:
                return abs(value)
            else:
                return 0
        case _:
            return resolve_battery_discharge_current(data, device_data) * \
                resolve_battery_voltage(data, device_data)


def resolve_active_load_power(data, device_data):
    match device_data['devcode']:
        case _:
            return (float(
                next((x for x in data['energy_flow']['bc_status'] if
                      x['par'] == 'load_active_power'), {'val': '0'})['val']) * 1000)


def resolve_active_load_percentage(data, device_data):
    match device_data['devcode']:
        case 2376:
            return float(
                next((x for x in data['last_data']['pars']['bc_'] if
                      x['id'].lower() == 'bc_eybond_read_37'), {'val': '0'})['val'])
        case 2341:
            return float(
                next((x for x in data['last_data']['pars']['bc_'] if
                      x['id'].lower() == 'bc_battery_capacity'), {'val': '0'})['val'])
        case 2428:
            return float(
                next((x for x in data['last_data']['pars']['bc_'] if
                      x['id'].lower() == 'bc_load_percent'), {'val': '0'})['val'])
        case _:
            return None


def resolve_output_priority(data, device_data):
    mapper = {
        'uti': 'Utility',
        'utility': 'Utility',
        'sbu': 'SBU',
        'sol': 'Solar',
        'solar': 'Solar',
        'solar first': 'Solar',
        'sbu first': 'SBU',
        'utility first': 'Utility',
        None: None
    }
    match device_data['devcode']:
        case 2341:
            val = next((x for x in data['last_data']['pars']['bc_'] if x['id'] == 'bc_output_source_priority'),
                       {'val': None})['val']

        case 2376:
            if 'sy_' not in data['last_data']['pars']:
                return None
            val = next((x for x in data['last_data']['pars']['sy_'] if
                        x['par'].lower() == 'Output priority'.lower()), {'val': None})['val']

        case _:
            if 'device_extra' in data:
                return data['device_extra']['output_priority']
            else:
                return None

    if val is not None and val.lower() in mapper:
        return mapper[val.lower()]
    else:
        return None


def resolve_charge_priority(data, device_data):
    mapper = {
        'Solar priority': 'SOLAR_PRIORITY',
        'Solar and mains': 'SOLAR_AND_UTILITY',
        'Solar only': 'SOLAR_ONLY',
        None: None,
    }
    match device_data['devcode']:
        case _:
            return \
                mapper[
                    next(
                        (x for x in data['last_data']['pars']['bt_']
                         if
                         x['id'] == 'bt_charger_source_priority'), {'val': None})['val']]


def resolve_grid_in_power(data, device_data):
    match device_data['devcode']:
        case _:
            return float(next((x for x in data['last_data']['pars']['gd_'] if
                               x['id'] == 'gd_grid_active_power'), {'val': '0'})['val'])


def resolve_grid_frequency(data, device_data):
    match device_data['devcode']:
        case _:
            return next((x for x in data['last_data']['pars']['gd_'] if
                         x['id'] == 'gd_grid_frequency' or
                         x['id'] == 'gd_ac_input_frequency' or
                         x['par'].lower() == 'Grid frequency'.lower()
                         ), {'val': None})['val']


def resolve_pv_power(data, device_data):
    match device_data['devcode']:
        case _:
            return (float(next((x for x in data['last_data']['pars']['pv_'] if
                                x['id'] == 'pv_output_power'), {'val': '0'})['val'])
                    or (float(next((x for x in data['energy_flow']['pv_status'] if
                                    x['par'] == 'pv_output_power'), {'val': '0'})['val']) * 1000))


def resolve_pv_voltage(data, device_data):
    match device_data['devcode']:
        case _:
            return next((x for x in data['last_data']['pars']['pv_'] if
                         x['id'] == 'pv_input_voltage' or x['id'] == 'pv_voltage' or x[
                             'par'].lower() == 'PV Voltage'.lower() or x[
                             'par'].lower() == 'PV Input Voltage'.lower()), {'val': None})['val']


def resolve_grid_input_voltage(data, device_data):
    match device_data['devcode']:
        case _:
            return next((x for x in data['last_data']['pars']['gd_'] if
                         x['id'] == 'gd_ac_input_voltage' or x['id'] == 'gd_grid_voltage' or x[
                             'par'].lower() == 'Grid Voltage'.lower()),
                        {'val': None})['val']


def resolve_grid_output_voltage(data, device_data):
    match device_data['devcode']:
        case _:
            return next((x for x in data['last_data']['pars']['bc_'] if
                         x['id'] == 'bc_output_voltage' or x['par'].lower() == 'Output Voltage'.lower()),
                        {'val': None})['val']


def resolve_dc_module_temperature(data, device_data):
    match device_data['devcode']:
        case _:
            data = data['last_data']['pars']
            if 'sy_' not in data:
                return None
            else:
                return \
                    next((x for x in data['sy_'] if x['par'].lower() == 'DC Module Termperature'.lower()),
                         {'val': None})['val']


def resolve_inv_temperature(data, device_data):
    match device_data['devcode']:
        case _:
            data = data['last_data']['pars']
            if 'sy_' not in data:
                return None
            else:
                return \
                    next((x for x in data['sy_'] if x['par'].lower() == 'INV Module Termperature'.lower()),
                         {'val': None})['val']


async def set_inverter_output_priority(token: str, secret: str, device_data, value: str):
    match device_data['devcode']:
        case 2341:
            map_param_value = {
                'Utility': '0',
                'Solar': '1',
                'SBU': '2'
            }
            param_value = map_param_value[value]

            param_id = 'los_output_source_priority'
        case 2428:
            map_param_value = {
                'Utility': '12336',
                'Solar': '12337',
                'SBU': '12338'
            }
            param_value = map_param_value[value]

            param_id = 'bse_output_source_priority'
        case 2376:
            map_param_value = {
                'Utility': '0',
                'Solar': '1',
                'SBU': '2'
            }
            param_value = map_param_value[value]

            param_id = 'bse_eybond_ctrl_49'

        case _:
            return
    return await set_ctrl_device_param(token, secret, device_data, param_id, param_value)


async def get_inverter_output_priority(token: str, secret: str, device_data):
    match device_data['devcode']:
        case 2341:
            map_param_value = {
                'Utility first': 'Utility',
                'Solar first': 'Solar',
                'SBU': 'SBU',
                'SBU first': 'SBU',
                None: None
            }
            # param_value = map_param_value[value]

            param_id = 'los_output_source_priority'
        case 2428:
            map_param_value = {
                'Utility first': 'Utility',
                'Solar first': 'Solar',
                'SBU': 'SBU',
                'SBU first': 'SBU',
                None: None
            }
            # param_value = map_param_value[value]

            param_id = 'bse_output_source_priority'

        case _:
            return
    result = await get_device_ctrl_value(token, secret, device_data, param_id)

    return map_param_value[result['val']]
