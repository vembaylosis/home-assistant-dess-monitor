"""Canonical metric resolvers — thin wrappers over the self-discovery layer.

Each ``resolve_*`` function takes the per-device tick data plus the owning
``InverterDevice`` and returns the normalised value. The legacy
``data_keys_map.py`` / :func:`get_sensor_value_simple` path is no longer used —
all lookups now go through :class:`MappingDiscovery`, which auto-detects the
matching provider key the first time a device responds, pins it, and persists
the choice across HA restarts.

The one exception is :func:`resolve_last_sample_time`, which parses a free-form
timestamp from the ``last_data`` envelope and isn't a per-key mapping.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Optional

from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from custom_components.dess_monitor.hub import InverterDevice

_LOGGER = logging.getLogger(__name__)


# --- last_sample_time (not a mapping resolver) -------------------------------

_LAST_SAMPLE_TIME_DIAG_LOGGED: set[str] = set()
_LAST_SAMPLE_TIME_TZ_OFFSET_HOURS: dict[str, int] = {}


def resolve_last_sample_time(data: dict[str, Any], inverter_device: "InverterDevice") -> Optional[datetime]:
    """Return ``last_data.gts`` as an aware datetime (assumed in HA local TZ)."""
    device_data = inverter_device.device_data if inverter_device is not None else None
    pn = device_data.get('pn') if isinstance(device_data, dict) else None
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

    # The cloud encodes gts in its own server timezone as if it were UTC ms.
    # Calibrate once per device: round (now - parsed) to whole hours and keep that
    # as the server's TZ offset, then apply it to every subsequent sample so
    # relative freshness is preserved.
    if pn:
        offset = _LAST_SAMPLE_TIME_TZ_OFFSET_HOURS.get(str(pn))
        if offset is None:
            diff_hours = (dt_util.utcnow() - parsed).total_seconds() / 3600.0
            offset = int(round(diff_hours))
            _LAST_SAMPLE_TIME_TZ_OFFSET_HOURS[str(pn)] = offset
            if offset:
                _LOGGER.info("last_sample_time[%s]: server TZ offset detected = %+d h",
                             pn, offset)
        if offset:
            parsed = parsed + timedelta(hours=offset)
    return parsed


# --- mapping-backed resolvers ------------------------------------------------

def _resolve(inverter_device: "InverterDevice", canonical: str, data: dict[str, Any]):
    return inverter_device.resolve(canonical, data)


def resolve_battery_voltage(data, inverter_device):
    return _resolve(inverter_device, "battery_voltage", data)


def resolve_battery_charging_voltage(data, inverter_device):
    return _resolve(inverter_device, "battery_charging_voltage", data)


def resolve_battery_charging_current(data, inverter_device):
    val = _resolve(inverter_device, "battery_charging_current", data)
    if val is None:
        return None
    return max(val, 0.0)


def resolve_battery_discharge_current(data, inverter_device):
    return _resolve(inverter_device, "battery_discharge_current", data)


def resolve_battery_charging_power(data, inverter_device):
    """Prefer signed ``battery_active_power`` (positive half); fall back to V·A."""
    val = _resolve(inverter_device, "battery_charging_power", data)
    if val is not None:
        return val
    # Fallback: charge_current * (charge_voltage or battery_voltage).
    current = _resolve(inverter_device, "battery_charging_current", data)
    voltage = (
            _resolve(inverter_device, "battery_charging_voltage", data)
            or _resolve(inverter_device, "battery_voltage", data)
    )
    if current is None or voltage is None:
        return None
    return current * voltage


def resolve_battery_discharge_power(data, inverter_device):
    """Prefer signed ``battery_active_power`` (negative half, abs'd); else V·A."""
    val = _resolve(inverter_device, "battery_discharge_power", data)
    if val is not None:
        return val
    current = _resolve(inverter_device, "battery_discharge_current", data)
    voltage = _resolve(inverter_device, "battery_voltage", data)
    if current is None or voltage is None:
        return None
    return current * voltage


def resolve_active_load_power(data, inverter_device):
    return _resolve(inverter_device, "active_load_power", data)


def resolve_active_load_percentage(data, inverter_device):
    return _resolve(inverter_device, "active_load_percentage", data)


def resolve_output_priority(data, inverter_device):
    return _resolve(inverter_device, "output_priority", data)


def resolve_charge_priority(data, inverter_device):
    return _resolve(inverter_device, "charge_priority", data)


def resolve_mains_status(data, inverter_device):
    return _resolve(inverter_device, "mains_status", data)


def resolve_grid_in_power(data, inverter_device):
    return _resolve(inverter_device, "grid_in_power", data)


def resolve_battery_capacity(data, inverter_device):
    return _resolve(inverter_device, "battery_capacity", data)


def resolve_grid_frequency(data, inverter_device):
    return _resolve(inverter_device, "grid_frequency", data)


def resolve_pv_power(data, inverter_device):
    return _resolve(inverter_device, "pv_power", data)


def resolve_pv2_power(data, inverter_device):
    return _resolve(inverter_device, "pv2_power", data)


def resolve_pv_voltage(data, inverter_device):
    return _resolve(inverter_device, "pv_voltage", data)


def resolve_pv2_voltage(data, inverter_device):
    return _resolve(inverter_device, "pv2_voltage", data)


def resolve_grid_input_voltage(data, inverter_device):
    return _resolve(inverter_device, "grid_input_voltage", data)


def resolve_grid_output_voltage(data, inverter_device):
    return _resolve(inverter_device, "grid_output_voltage", data)


def resolve_dc_module_temperature(data, inverter_device):
    return _resolve(inverter_device, "dc_module_temperature", data)


def resolve_inv_temperature(data, inverter_device):
    return _resolve(inverter_device, "inv_temperature", data)


def resolve_bt_utility_charge(data, inverter_device):
    return _resolve(inverter_device, "bt_utility_charge", data)


def resolve_bt_total_charge_current(data, inverter_device):
    return _resolve(inverter_device, "bt_total_charge_current", data)


def resolve_bt_cutoff_voltage(data, inverter_device):
    return _resolve(inverter_device, "bt_cutoff_voltage", data)


def resolve_sy_nominal_out_power(data, inverter_device):
    return _resolve(inverter_device, "sy_nominal_out_power", data)


def resolve_sy_rated_battery_voltage(data, inverter_device):
    return _resolve(inverter_device, "sy_rated_battery_voltage", data)


def resolve_bt_comeback_utility_voltage(data, inverter_device):
    return _resolve(inverter_device, "bt_comeback_utility_voltage", data)


def resolve_bt_comeback_battery_voltage(data, inverter_device):
    return _resolve(inverter_device, "bt_comeback_battery_voltage", data)
