def resolve_battery_charging_current(data, device_data):
    match device_data['devcode']:
        case 2376:
            # PV charging current
            pv = float(next((x for x in data['last_data']['pars']['gd_'] if
                             x['par'] == 'PV charging current'),
                            {'val': '0'}))
            # AC charging current
            ac = float(next((x for x in data['last_data']['pars']['gd_'] if
                             x['par'] == 'AC charging current'),
                            {'val': '0'}))
            return pv + ac
        case _:
            return \
                float(next(
                    (x for x in data['last_data']['pars']['bt_']
                     if
                     x['id'] == 'bt_battery_charging_current' or x['par'] == 'Battery charging current'),
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
        case _:
            return \
                float(next(
                    (x for x in data['last_data']['pars']['bt_']
                     if
                     x['id'] == 'bt_battery_discharge_current'),
                    {'val': '0'}
                )['val'])


def resolve_battery_voltage(data, device_data):
    match device_data['devcode']:
        case _:
            return \
                float(next((x for x in
                            data['last_data']['pars']['bt_']
                            if
                            x['id'] == 'bt_battery_voltage' or x['par'] == 'Battery voltage'), {'val': '0'})['val'])


def resolve_active_load_power(data, device_data):
    match device_data['devcode']:
        case _:
            return (float(
                next((x for x in data['energy_flow']['bc_status'] if
                      x['par'] == 'load_active_power'), {'val': '0'})['val']) * 1000)


def resolve_output_priority(data, device_data):
    match device_data['devcode']:
        case _:
            return next((x for x in data['last_data']['pars']['bc_'] if
                         x['id'] == 'bc_output_source_priority'), {'val': None})['val']


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
            return next((x for x in data['last_data']['pars']['gd_'] if
                         x['id'] == 'gd_grid_active_power'), {'val': None})['val']


def resolve_grid_frequency(data, device_data):
    match device_data['devcode']:
        case _:
            return next((x for x in data['last_data']['pars']['gd_'] if
                         x['id'] == 'gd_grid_frequency' or
                         x['id'] == 'gd_ac_input_frequency' or
                         x['par'] == 'Grid frequency'
                         ), {'val': None})['val']
