from custom_components.dess_monitor.api.helpers import (
    get_sensor_value_simple,
    safe_float,
    get_sensor_value_simple_entry, resolve_param
)


def resolve_battery_charging_current(data, device_data) -> float:
    """
    Extracts battery charging current:
    - For devcode 2376, reads 'bt_eybond_read_29'. Always non-negative.
    - For others, reads 'battery_charging_current'. Always non-negative.
    """
    if device_data.get('devcode') == 2376:
        entry = get_sensor_value_simple_entry("bt_eybond_read_29", data, device_data)
        raw = entry[1] if entry else None
    else:
        raw = get_sensor_value_simple("battery_charging_current", data, device_data)
    return max(safe_float(raw), 0.0)


def resolve_battery_charging_voltage(data, device_data) -> float:
    """
    Extracts battery charging voltage:
    - Primary: 'battery_charging_voltage'.
    - Fallback: battery_voltage if charging voltage missing or zero.
    """
    raw = get_sensor_value_simple("battery_charging_voltage", data, device_data)
    voltage = safe_float(raw)
    if voltage:
        return voltage
    # fallback to general battery voltage
    return safe_float(get_sensor_value_simple("battery_voltage", data, device_data))


def resolve_battery_discharge_current(data, device_data) -> float:
    """
    Extracts battery discharge current:
    - For devcode 2376, reads 'bt_eybond_read_29'. Returns ABS if negative, else 0.
    - For others, reads 'battery_discharge_current'. Returns raw (can be + or -).
    """
    if device_data.get('devcode') == 2376:
        entry = get_sensor_value_simple_entry("bt_eybond_read_29", data, device_data)
        raw = entry[1] if entry else None
        val = safe_float(raw)
        return abs(val) if val < 0 else 0.0
    # generic
    entry = get_sensor_value_simple_entry("battery_discharge_current", data, device_data)
    raw = entry[1] if entry else None
    return safe_float(raw)


def resolve_battery_voltage(data, device_data) -> float:
    """Extracts battery voltage."""
    return safe_float(get_sensor_value_simple("battery_voltage", data, device_data))


def resolve_battery_charging_power(data, device_data) -> float:
    """
    Рассчитывает мощность заряда батареи.

    1) Если в данных есть сенсор 'battery_charging_power', берём его:
       entry = (key, raw_val, unit) = get_sensor_value_simple_entry(...)
       — конвертируем raw_val через safe_float;
       — если unit == 'kW', умножаем на 1000.
    2) Иначе:
       — для devcode 2376 читаем par=='battery_active_power' из energy_flow,
         умножаем safe_float(val)×1000, возвращаем >=0.
       — для остальных: current = resolve_battery_charging_current(...);
         voltage = resolve_battery_charging_voltage(...) или fallback на resolve_battery_voltage;
         возвращаем current * voltage.
    """
    # 1) Прямой сенсор
    entry = get_sensor_value_simple_entry("battery_charging_power", data, device_data)
    if entry:
        _, raw_val, unit = entry
        val = safe_float(raw_val)
        return val * 1000 if unit and unit.lower() == "kw" else val

    # 2) Фallback на старую логику
    match device_data.get("devcode"):
        case 2376:
            result = resolve_param(
                data,
                {"par": "battery_active_power"},
                case_insensitive=True,
                root_keys=["energy_flow"]
            )
            if not result:
                return 0.0
            try:
                value = float(result.get("val", "0")) * 1000
            except (ValueError, TypeError):
                value = 0.0
            return value if value >= 0 else 0.0
        case _:
            current = resolve_battery_charging_current(data, device_data)
            voltage = resolve_battery_charging_voltage(data, device_data)
            if not voltage:
                voltage = resolve_battery_voltage(data, device_data)
            return current * voltage


def resolve_battery_discharge_power(data, device_data) -> float:
    """
    Рассчитывает мощность разряда батареи.

    1) Если в данных есть сенсор 'battery_discharge_power', берём его:
       entry = (key, raw_val, unit);
       — safe_float(raw_val) и kW→W.
    2) Иначе:
       — для devcode 2376 читаем par=='battery_active_power', умножаем safe_float×1000,
         возвращаем abs(value) если <=0, иначе 0.
       — для остальных: discharge_current * resolve_battery_voltage.
    """
    # 1) Прямой сенсор
    entry = get_sensor_value_simple_entry("battery_discharge_power", data, device_data)
    if entry:
        _, raw_val, unit = entry
        val = safe_float(raw_val)
        return val * 1000 if unit and unit.lower() == "kw" else val

    # 2) Фallback на старую логику
    match device_data.get("devcode"):
        case 2376:
            result = resolve_param(
                data,
                {"par": "battery_active_power"},
                case_insensitive=True,
                root_keys=["energy_flow"]
            )
            if not result:
                return 0.0
            try:
                value = float(result.get("val", "0")) * 1000
            except (ValueError, TypeError):
                value = 0.0
            return abs(value) if value <= 0 else 0.0
        case _:
            return resolve_battery_discharge_current(data, device_data) * resolve_battery_voltage(data, device_data)


def resolve_active_load_power(data, device_data) -> float:
    """
    Extracts active load power, converting kW to W if needed.
    """
    entry = get_sensor_value_simple_entry("active_load_power", data, device_data)
    if not entry:
        return 0.0
    _, raw, unit = entry
    val = safe_float(raw)
    # convert kW to W
    return val * 1000 if unit and unit.lower() == 'kw' else val


def resolve_active_load_percentage(data, device_data) -> float:
    """Extracts active load percentage."""
    entry = get_sensor_value_simple_entry("active_load_percentage", data, device_data)
    raw = entry[1] if entry else None
    return safe_float(raw)


def resolve_output_priority(data, device_data):
    """
    Determines output priority using mapping.
    """
    mapper = {
        'uti': 'Utility', 'utility': 'Utility',
        'sbu': 'SBU', 'sol': 'Solar', 'solar': 'Solar',
        'solar first': 'Solar', 'sbu first': 'SBU', 'utility first': 'Utility'
    }
    raw = get_sensor_value_simple("output_priority", data, device_data)
    if raw is None:
        return None
    return mapper.get(raw.lower())


def resolve_charge_priority(data, device_data):
    """Determines charge priority."""
    mapper = {
        'solar priority': 'SOLAR_PRIORITY',
        'solar and mains': 'SOLAR_AND_UTILITY',
        'solar only': 'SOLAR_ONLY',
        'n/a': 'NONE'
    }
    raw = get_sensor_value_simple("charge_priority", data, device_data)
    if raw is None:
        return None
    return mapper.get(raw.lower())


def resolve_grid_in_power(data, device_data) -> float:
    """Extracts incoming grid power."""
    return safe_float(get_sensor_value_simple("grid_in_power", data, device_data))


def resolve_battery_capacity(data, device_data) -> float:
    """Extracts battery capacity."""
    return safe_float(get_sensor_value_simple("battery_capacity", data, device_data))


def resolve_grid_frequency(data, device_data):
    """Extracts grid frequency (string)."""
    return get_sensor_value_simple("grid_frequency", data, device_data)


def resolve_pv_power(data, device_data) -> float:
    """Extracts PV power, converting kW to W if unit is kW."""
    entry = get_sensor_value_simple_entry("pv_power", data, device_data)
    if not entry:
        return 0.0
    _, raw, unit = entry
    val = safe_float(raw)
    return val * 1000 if unit and unit.lower() == 'kw' else val


def resolve_pv2_power(data, device_data) -> float:
    """Extracts PV2 power."""
    entry = get_sensor_value_simple_entry("pv2_power", data, device_data)
    if not entry:
        return 0.0
    _, raw, unit = entry
    val = safe_float(raw)
    return val * 1000 if unit and unit.lower() == 'kw' else val


def resolve_pv_voltage(data, device_data):
    """Extracts PV voltage."""
    return safe_float(get_sensor_value_simple("pv_voltage", data, device_data))


def resolve_pv2_voltage(data, device_data):
    """Extracts PV2 voltage."""
    return safe_float(get_sensor_value_simple("pv2_voltage", data, device_data))


def resolve_grid_input_voltage(data, device_data):
    """Extracts grid input voltage."""
    return safe_float(get_sensor_value_simple("grid_input_voltage", data, device_data))


def resolve_grid_output_voltage(data, device_data):
    """Extracts grid output voltage."""
    return safe_float(get_sensor_value_simple("grid_output_voltage", data, device_data))


def resolve_dc_module_temperature(data, device_data):
    """Extracts DC module temperature."""
    return safe_float(get_sensor_value_simple("dc_module_temperature", data, device_data))


def resolve_inv_temperature(data, device_data):
    """Extracts inverter temperature."""
    return safe_float(get_sensor_value_simple("inv_temperature", data, device_data))


def resolve_bt_utility_charge(data, device_data):
    """Extracts utility charge current."""
    return safe_float(get_sensor_value_simple("bt_utility_charge", data, device_data))


def resolve_bt_total_charge_current(data, device_data):
    """Extracts total charge current."""
    return safe_float(get_sensor_value_simple("bt_total_charge_current", data, device_data))


def resolve_bt_cutoff_voltage(data, device_data):
    """Extracts battery cutoff voltage."""
    return safe_float(get_sensor_value_simple("bt_cutoff_voltage", data, device_data))


def resolve_sy_nominal_out_power(data, device_data):
    """Extracts nominal output power."""
    return safe_float(get_sensor_value_simple("sy_nominal_out_power", data, device_data))


def resolve_sy_rated_battery_voltage(data, device_data):
    """Extracts rated battery voltage."""
    return safe_float(get_sensor_value_simple("sy_rated_battery_voltage", data, device_data))


def resolve_bt_comeback_utility_voltage(data, device_data):
    """Extracts comeback utility voltage."""
    return safe_float(get_sensor_value_simple("bt_comeback_utility_voltage", data, device_data))


def resolve_bt_comeback_battery_voltage(data, device_data):
    """Extracts comeback battery voltage."""
    return safe_float(get_sensor_value_simple("bt_comeback_battery_voltage", data, device_data))
