import logging
from datetime import datetime

from homeassistant.util import dt as dt_util

from custom_components.dess_monitor.api.helpers import get_sensor_value_simple, safe_float, \
    get_sensor_value_simple_entry

_LOGGER = logging.getLogger(__name__)


_LAST_SAMPLE_TIME_DIAG_LOGGED: set[str] = set()


def resolve_last_sample_time(data, device_data):
    """Return ``last_data.gts`` as an aware datetime (assumed in HA local TZ)."""
    pn = (device_data or {}).get('pn') if isinstance(device_data, dict) else None
    diag_key = str(pn) if pn else "?"
    last_data = data.get('last_data') if isinstance(data, dict) else None
    if not isinstance(last_data, dict):
        if diag_key not in _LAST_SAMPLE_TIME_DIAG_LOGGED:
            _LAST_SAMPLE_TIME_DIAG_LOGGED.add(diag_key)
            _LOGGER.warning("last_sample_time[%s]: last_data missing or not dict (type=%s)",
                            diag_key, type(last_data).__name__)
        return None
    raw = last_data.get('gts') or last_data.get('ts') or last_data.get('time')
    if raw in (None, ""):
        if diag_key not in _LAST_SAMPLE_TIME_DIAG_LOGGED:
            _LAST_SAMPLE_TIME_DIAG_LOGGED.add(diag_key)
            _LOGGER.warning("last_sample_time[%s]: no gts/ts/time in last_data; keys=%s",
                            diag_key, list(last_data.keys()))
        return None

    parsed: datetime | None = None

    # Numeric epoch (seconds or milliseconds), as int/float or numeric string.
    epoch_candidate = raw
    if isinstance(epoch_candidate, str):
        epoch_candidate = epoch_candidate.strip()
    try:
        epoch = float(epoch_candidate)
    except (TypeError, ValueError):
        epoch = None
    if epoch is not None:
        if epoch > 1e12:  # milliseconds
            epoch /= 1000.0
        try:
            parsed = datetime.fromtimestamp(epoch, tz=dt_util.UTC)
        except (OverflowError, OSError, ValueError):
            parsed = None

    if parsed is None and isinstance(raw, str):
        text = raw.strip()
        parsed = dt_util.parse_datetime(text)
        if parsed is None:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d %H:%M:%S"):
                try:
                    parsed = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue

    if parsed is None:
        if diag_key not in _LAST_SAMPLE_TIME_DIAG_LOGGED:
            _LAST_SAMPLE_TIME_DIAG_LOGGED.add(diag_key)
            _LOGGER.warning("last_sample_time[%s]: unparseable gts=%r", diag_key, raw)
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    return parsed


def resolve_battery_charging_current(data, device_data):
    raw = get_sensor_value_simple("battery_charging_current", data, device_data)
    return max(safe_float(raw), 0.0)


def resolve_battery_charging_voltage(data, device_data):
    return safe_float(get_sensor_value_simple("battery_charging_voltage", data, device_data))


def resolve_battery_discharge_current(
        data,
        device_data,
) -> float:
    """
    Для поля bt_eybond_read_29 — возвращает ABS только для отрицательных значений,
    иначе 0.0.
    Для всех остальных полей — возвращает значение как есть (может быть +
    или −).
    Если ничего не найдено — 0.0.
    """
    found = get_sensor_value_simple_entry("battery_discharge_current", data, device_data)
    if not found:
        return 0.0

    key, raw_val, unit = found
    value = safe_float(raw_val)

    if key == "bt_eybond_read_29" or key == "Battery Current":
        # Только отрицательный ток разряда, положительный — в 0
        return abs(value) if value < 0 else 0.0
    else:
        # Для прочих сенсоров возвращаем значение напрямую
        return value


def resolve_battery_voltage(data, device_data):
    return safe_float(get_sensor_value_simple("battery_voltage", data, device_data))


def resolve_battery_charging_power(data, device_data):
    found = get_sensor_value_simple_entry("battery_active_power", data, device_data)
    if found:
        key, raw_val, unit = found
        value = safe_float(raw_val)
        if unit == 'kW':
            value *= 1000
        if value > 0:
            return value
        else:
            return 0.0
    current = resolve_battery_charging_current(data, device_data)
    voltage = resolve_battery_charging_voltage(data, device_data) or resolve_battery_voltage(data, device_data)
    return current * voltage


def resolve_battery_discharge_power(data, device_data):
    found = get_sensor_value_simple_entry("battery_active_power", data, device_data)
    if found:
        key, raw_val, unit = found
        value = safe_float(raw_val)
        if unit == 'kW':
            value *= 1000
        if value < 0:
            return abs(value)
        else:
            return 0.0
    return resolve_battery_discharge_current(data, device_data) * resolve_battery_voltage(data, device_data)


def resolve_active_load_power(data, device_data):
    return safe_float(get_sensor_value_simple("active_load_power", data, device_data)) * 1000


def resolve_active_load_percentage(data, device_data):
    return safe_float(get_sensor_value_simple("active_load_percentage", data, device_data))


def resolve_output_priority(data, device_data):
    mapper = {
        'uti': 'Utility', 'utility': 'Utility',
        'sbu': 'SBU', 'sol': 'Solar', 'solar': 'Solar',
        'solar first': 'Solar', 'sbu first': 'SBU', 'utility first': 'Utility',
    }
    raw = get_sensor_value_simple("output_priority", data, device_data)
    if raw is None:
        return None
    return mapper.get(raw.lower(), None)


def resolve_charge_priority(data, device_data):
    mapper = {
        'solar priority': 'SOLAR_PRIORITY',
        'solar and mains': 'SOLAR_AND_UTILITY',
        'solar only': 'SOLAR_ONLY',
        'n/a': 'NONE',
    }
    raw = get_sensor_value_simple("charge_priority", data, device_data)
    if raw is None:
        return None
    return mapper.get(raw.lower(), None)


def resolve_grid_in_power(data, device_data):
    return safe_float(get_sensor_value_simple("grid_in_power", data, device_data))


def resolve_battery_capacity(data, device_data):
    return safe_float(get_sensor_value_simple("battery_capacity", data, device_data))


def resolve_grid_frequency(data, device_data):
    return safe_float(get_sensor_value_simple("grid_frequency", data, device_data), default=None)


def resolve_pv_power(data, device_data):
    found = (get_sensor_value_simple_entry("pv_power", data, device_data))

    if not found:
        return None

    key, raw_val, unit = found
    val = safe_float(raw_val)
    if unit == 'kW':
        val *= 1000

    return val


def resolve_pv2_power(data, device_data):
    found = (get_sensor_value_simple_entry("pv2_power", data, device_data))

    if not found:
        return None

    key, raw_val, unit = found
    val = safe_float(raw_val)
    if unit == 'kW':
        val *= 1000

    return val


def resolve_pv_voltage(data, device_data):
    return safe_float(get_sensor_value_simple("pv_voltage", data, device_data), default=None)


def resolve_pv2_voltage(data, device_data):
    return safe_float(get_sensor_value_simple("pv2_voltage", data, device_data), default=None)


def resolve_grid_input_voltage(data, device_data):
    return safe_float(get_sensor_value_simple("grid_input_voltage", data, device_data), default=None)


def resolve_grid_output_voltage(data, device_data):
    return safe_float(get_sensor_value_simple("grid_output_voltage", data, device_data), default=None)


def resolve_dc_module_temperature(data, device_data):
    return safe_float(get_sensor_value_simple("dc_module_temperature", data, device_data), default=None)


def resolve_inv_temperature(data, device_data):
    return safe_float(get_sensor_value_simple("inv_temperature", data, device_data), default=None)


def resolve_bt_utility_charge(data, device_data):
    return safe_float(get_sensor_value_simple("bt_utility_charge", data, device_data), default=None)


def resolve_bt_total_charge_current(data, device_data):
    return safe_float(get_sensor_value_simple("bt_total_charge_current", data, device_data), default=None)


def resolve_bt_cutoff_voltage(data, device_data):
    return safe_float(get_sensor_value_simple("bt_cutoff_voltage", data, device_data), default=None)


def resolve_sy_nominal_out_power(data, device_data):
    return safe_float(get_sensor_value_simple("sy_nominal_out_power", data, device_data), default=None)


def resolve_sy_rated_battery_voltage(data, device_data):
    return safe_float(get_sensor_value_simple("sy_rated_battery_voltage", data, device_data), default=None)


def resolve_bt_comeback_utility_voltage(data, device_data):
    return safe_float(get_sensor_value_simple("bt_comeback_utility_voltage", data, device_data), default=None)


def resolve_bt_comeback_battery_voltage(data, device_data):
    return safe_float(get_sensor_value_simple("bt_comeback_battery_voltage", data, device_data), default=None)
