from custom_components.dess_monitor.api import set_ctrl_device_param, get_device_ctrl_value


def resolve_param(data, where, case_insensitive=False, find_all=False, default=None, root_keys=None):
    """
    Recursively searches for elements in a nested structure that satisfy 'where'.

    Args:
      data: The input data (dict, list, etc.).
      where: A dict of conditions (AND mode) or a list of dicts (OR mode).
      case_insensitive: Compare strings in lower-case if True.
      find_all: Return all matching elements if True; otherwise, first match.
      default: Value to return if no match is found.
      root_keys: List of keys at root to start the search; if None, search full structure.

    Returns:
      A matching element (or list of elements) or default if not found.
    """
    found = []

    def _matches_conditions(item):
        # OR mode if where is a list; AND mode if dict.
        if isinstance(where, list):
            for condition in where:
                if not isinstance(condition, dict):
                    continue
                match = True
                for key, value in condition.items():
                    if key not in item:
                        match = False
                        break
                    item_val = item[key]
                    if case_insensitive and isinstance(item_val, str) and isinstance(value, str):
                        if item_val.lower() != value.lower():
                            match = False
                            break
                    else:
                        if item_val != value:
                            match = False
                            break
                if match:
                    return True
            return False
        elif isinstance(where, dict):
            for key, value in where.items():
                if key not in item:
                    return False
                item_val = item[key]
                if case_insensitive and isinstance(item_val, str) and isinstance(value, str):
                    if item_val.lower() != value.lower():
                        return False
                else:
                    if item_val != value:
                        return False
            return True
        return False

    def _search(current):
        nonlocal found
        if isinstance(current, dict):
            if _matches_conditions(current):
                found.append(current)
                if not find_all:
                    return True
            for v in current.values():
                if isinstance(v, (dict, list)):
                    if _search(v) and not find_all:
                        return True
        elif isinstance(current, list):
            for item in current:
                if isinstance(item, (dict, list)):
                    if _search(item) and not find_all:
                        return True
        return False

    if root_keys is not None and isinstance(data, dict):
        for key in root_keys:
            if key in data:
                _search(data[key])
    else:
        _search(data)

    if find_all:
        return found if found else default
    else:
        return found[0] if found else default


def resolve_battery_charging_current(data, device_data):
    """
    Extracts battery charging current.

    For devcode 2376, searches for 'id' == 'bt_eybond_read_29'. Returns float(value) if >= 0, else 0.
    For others, searches using OR: 'id' == 'bt_battery_charging_current' or 'par' == 'Battery charging current'.
    Returns 0 if not found.
    """
    match device_data.get('devcode'):
        case 2376:
            result = resolve_param(data, {"id": "bt_eybond_read_29"}, case_insensitive=True)
            if result is None:
                return None
            try:
                value = float(result.get("val", "0"))
            except (ValueError, TypeError):
                value = 0
            return value if value >= 0 else 0
        case _:
            result = resolve_param(
                data,
                [{"id": "bt_battery_charging_current"}, {"par": "Battery charging current"}],
                case_insensitive=True,
            )
            if result is None:
                return 0
            try:
                value = float(result.get("val", "0"))
            except (ValueError, TypeError):
                value = 0
            return value


def resolve_battery_charging_voltage(data, device_data):
    """
    Extracts battery charging voltage by searching for 'id' == 'bt_vulk_charging_voltage'.
    Returns its float value or 0.
    """
    result = resolve_param(data, {"id": "bt_vulk_chaging_voltage"}, case_insensitive=True)
    try:
        return float(result.get("val", "0")) if result else 0
    except (ValueError, TypeError):
        return 0


def resolve_battery_discharge_current(data, device_data):
    """
    Extracts battery discharge current.

    For devcode 2376, searches for 'id' == 'bt_eybond_read_29' and returns abs(value) if value <= 0, else 0.
    For others, searches using OR among:
      'bt_battery_discharge_current', 'bt_discharge_current', and 'par' == 'Battery discharge current'.
    """
    match device_data.get('devcode'):
        case 2376:
            result = resolve_param(data, {"id": "bt_eybond_read_29"}, case_insensitive=True)
            if result is None:
                return None
            try:
                value = float(result.get("val", "0"))
            except (ValueError, TypeError):
                value = 0
            return abs(value) if value <= 0 else 0
        case _:
            result = resolve_param(
                data,
                [
                    {"id": "bt_battery_discharge_current"},
                    {"id": "bt_discharge_current"},
                    {"par": "Battery discharge current"}
                ],
                case_insensitive=True,
            )
            try:
                return float(result.get("val", "0")) if result else 0
            except (ValueError, TypeError):
                return 0


def resolve_battery_voltage(data, device_data):
    """
    Extracts battery voltage by searching for 'id' == 'bt_battery_voltage' or 'par' == 'Battery Voltage'.
    Returns float(value) or 0.
    """
    result = resolve_param(
        data,
        [{"id": "bt_battery_voltage"}, {"par": "Battery Voltage"}],
        case_insensitive=True,
    )
    try:
        return float(result.get("val", "0")) if result else 0
    except (ValueError, TypeError):
        return 0


def resolve_battery_charging_power(data, device_data):
    """
    Calculates battery charging power.

    For devcode 2376, searches for element with 'par' == 'battery_active_power' in energy_flow,
      multiplies float(value) by 1000 and returns it (if >= 0).
    For others, multiplies charging current by voltage (or battery voltage if charging voltage is missing).
    """
    match device_data.get('devcode'):
        case 2376:
            result = resolve_param(
                data,
                {"par": "battery_active_power"},
                case_insensitive=True
            )
            if result is None:
                return None
            try:
                value = float(result.get("val", "0")) * 1000
            except (ValueError, TypeError):
                value = 0
            return value if value >= 0 else 0
        case _:
            current = resolve_battery_charging_current(data, device_data)
            voltage = resolve_battery_charging_voltage(data, device_data)
            if not voltage:
                voltage = resolve_battery_voltage(data, device_data)
            return current * voltage


def resolve_battery_discharge_power(data, device_data):
    """
    Calculates battery discharge power.

    For devcode 2376, uses 'battery_active_power' (multiplied by 1000) and returns abs(value) if <= 0.
    For others, multiplies discharge current by battery voltage.
    """
    match device_data.get('devcode'):
        case 2376:
            result = resolve_param(
                data,
                {"par": "battery_active_power"},
                case_insensitive=True
            )
            if result is None:
                return None
            try:
                value = float(result.get("val", "0")) * 1000
            except (ValueError, TypeError):
                value = 0
            return abs(value) if value <= 0 else 0
        case _:
            return resolve_battery_discharge_current(data, device_data) * resolve_battery_voltage(data, device_data)


def resolve_active_load_power(data, device_data):
    """
    Calculates active load power.

    Searches for elements matching any of:
      {"unit": "kW", "par": "load_active_power"},
      {"unit": "kW", "par": "output_power"},
      {"unit": "kW", "par": "bc_load_active_power"}.
    Returns the found value multiplied by 1000 or 0.
    """
    conditions = [
        {"unit": "kW", "par": "load_active_power"},
        {"unit": "kW", "par": "output_power"},
        {"unit": "kW", "par": "bc_load_active_power"}
    ]
    result = resolve_param(data, conditions, case_insensitive=True)
    try:
        return float(result.get("val", "0")) * 1000 if result else 0
    except (ValueError, TypeError):
        return 0


def resolve_active_load_percentage(data, device_data):
    """
    Extracts active load percentage based on devcode:
      2376: searches for 'id' == 'bc_eybond_read_37'
      2341: searches for 'id' == 'bc_battery_capacity'
      2428: searches for 'id' == 'bc_load_percent'
    Returns float(value) or 0.
    """
    match device_data.get('devcode'):
        case _:
            result = resolve_param(data, [
                {"id": "bc_eybond_read_37"},
                {"id": "bc_battery_capacity"},
                {"id": "bc_load_percent"}
            ], case_insensitive=True)

    try:
        return float(result.get("val", "0")) if result else 0
    except (ValueError, TypeError):
        return 0


def resolve_output_priority(data, device_data):
    """
    Determines output priority.

    For devcode 2341, searches for 'id' == 'bc_output_source_priority';
    for 2376, searches in 'sy_' (via root_keys) for 'par' == 'Output priority';
    for others, uses device_extra['output_priority'].
    Standardizes using a mapper.
    """
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
    match device_data.get('devcode'):
        case 2341:
            result = resolve_param(data, {"id": "bc_output_source_priority"}, case_insensitive=True)
            val = result.get("val") if result else None
        case 2376:
            result = resolve_param(data, {"par": "Output priority"}, case_insensitive=True,
                                   root_keys=["last_data", "pars"])
            val = result.get("val") if result else None
        case _:
            val = data.get("device_extra", {}).get("output_priority")
    if val is not None and isinstance(val, str) and val.lower() in mapper:
        return mapper[val.lower()]
    return None


def resolve_charge_priority(data, device_data):
    """
    Determines charge priority.

    Searches for 'id' == 'bt_charger_source_priority' and maps its value.
    """
    mapper = {
        'Solar priority': 'SOLAR_PRIORITY',
        'Solar and mains': 'SOLAR_AND_UTILITY',
        'Solar only': 'SOLAR_ONLY',
        'N/A': 'NONE',
        None: None,
    }
    result = resolve_param(data, {"id": "bt_charger_source_priority"}, case_insensitive=True)
    key = result.get("val") if result else None
    return mapper.get(key) if key in mapper else None


def resolve_grid_in_power(data, device_data):
    """
    Extracts incoming grid power by searching for 'id' == 'gd_grid_active_power'.
    Returns float(value) or 0.
    """
    result = resolve_param(data, {"id": "gd_grid_active_power"}, case_insensitive=True)
    try:
        return float(result.get("val", "0")) if result else 0
    except (ValueError, TypeError):
        return 0


def resolve_battery_capacity(data, device_data):
    """
    Extracts battery capacity from energy_flow by searching for 'par' == 'bt_battery_capacity'.
    Returns float(value) or 0.
    """
    result = resolve_param(data, {"par": "bt_battery_capacity"}, case_insensitive=True)
    try:
        return float(result.get("val", "0")) if result else 0
    except (ValueError, TypeError):
        return 0


def resolve_grid_frequency(data, device_data):
    """
    Extracts grid frequency by searching for one of:
      'id' == 'gd_grid_frequency', 'id' == 'gd_ac_input_frequency', or 'par' == 'Grid frequency'.
    Returns its value.
    """
    result = resolve_param(
        data,
        [
            {"id": "gd_grid_frequency"},
            {"id": "gd_ac_input_frequency"},
            {"par": "Grid frequency"}
        ],
        case_insensitive=True
    )
    return result.get("val") if result else None


def resolve_pv_power(data, device_data):
    """
    Extracts PV power.

    First, searches in last_data for 'id' == 'pv_output_power'. If nonzero, returns float(value).
    Otherwise, searches in energy_flow for 'par' == 'pv_output_power' and returns float(value)*1000.
    """
    result1 = resolve_param(data, {"id": "pv_output_power"}, case_insensitive=True, root_keys=["last_data"])
    try:
        value1 = float(result1.get("val", "0")) if result1 else 0
    except (ValueError, TypeError):
        value1 = 0
    if value1:
        return value1
    result2 = resolve_param(data, {"par": "pv_output_power"}, case_insensitive=True, root_keys=["energy_flow"])
    try:
        value2 = float(result2.get("val", "0")) * 1000 if result2 else 0
    except (ValueError, TypeError):
        value2 = 0
    return value2


def resolve_pv_voltage(data, device_data):
    """
    Extracts PV voltage by searching for one of:
      'id' == 'pv_input_voltage', 'id' == 'pv_voltage', 'par' == 'PV Voltage', or 'par' == 'PV Input Voltage'.
    Returns its value.
    """
    result = resolve_param(
        data,
        [
            {"id": "pv_input_voltage"},
            {"id": "pv_voltage"},
            {"par": "PV Voltage"},
            {"par": "PV Input Voltage"}
        ],
        case_insensitive=True
    )
    return result.get("val") if result else None


def resolve_grid_input_voltage(data, device_data):
    """
    Extracts grid input voltage by searching for one of:
      'id' == 'gd_ac_input_voltage', 'id' == 'gd_grid_voltage', or 'par' == 'Grid Voltage'.
    Returns its value.
    """
    result = resolve_param(
        data,
        [
            {"id": "gd_ac_input_voltage"},
            {"id": "gd_grid_voltage"},
            {"par": "Grid Voltage"}
        ],
        case_insensitive=True
    )
    return result.get("val") if result else None


def resolve_grid_output_voltage(data, device_data):
    """
    Extracts grid output voltage by searching for:
      'id' == 'bc_output_voltage' or 'par' == 'Output Voltage'.
    Returns its value.
    """
    result = resolve_param(
        data,
        [
            {"id": "bc_output_voltage"},
            {"par": "Output Voltage"}
        ],
        case_insensitive=True
    )
    return result.get("val") if result else None


def resolve_dc_module_temperature(data, device_data):
    """
    Extracts DC module temperature by searching in 'sy_' (via root_keys) for 'par' == 'DC Module Termperature'.
    Returns its value or None.
    """
    result = resolve_param(
        data,
        {"par": "DC Module Termperature"},
        case_insensitive=True,
        root_keys=["last_data", "pars"]
    )
    return result.get("val") if result else None


def resolve_inv_temperature(data, device_data):
    """
    Extracts inverter temperature by searching in 'sy_' (via root_keys) for 'par' == 'INV Module Termperature'.
    Returns its value or None.
    """
    result = resolve_param(
        data,
        {"par": "INV Module Termperature"},
        case_insensitive=True,
        root_keys=["last_data", "pars"]
    )
    return result.get("val") if result else None


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
                'Utility': 'Utility',
                'Solar first': 'Solar',
                'Solar': 'Solar',
                'SBU': 'SBU',
                'SBU first': 'SBU',
                None: None
            }
            # param_value = map_param_value[value]

            param_id = 'los_output_source_priority'
        case 2428:
            map_param_value = {
                'Utility first': 'Utility',
                'Utility': 'Utility',
                'Solar first': 'Solar',
                'Solar': 'Solar',
                'SBU': 'SBU',
                'SBU first': 'SBU',
                None: None
            }
            # param_value = map_param_value[value]

            param_id = 'bse_output_source_priority'

        case _:
            return
    result = await get_device_ctrl_value(token, secret, device_data, param_id)
    if result['val'] not in map_param_value:
        return None
    return map_param_value[result['val']]
