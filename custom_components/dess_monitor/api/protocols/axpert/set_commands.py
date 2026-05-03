"""Voltronic Axpert/PI30 *set* command builders.

These functions produce the bare command string (e.g. ``"POP02"``,
``"PBAV56.40"``). Wire framing — CRC + ``\\r`` — is added by
:meth:`AxpertProtocol.encode`. The reply is a short ACK/NAK frame, decoded
by :meth:`AxpertProtocol.decode` into ``{"status": "ACK"}`` / ``"NAK"``.

Usage::

    cmd = build_set_output_priority(OutputSourcePrioritySetting.SBU)
    result = await service.query(device, cmd)
    if result.get("status") == "ACK": ...
"""
from __future__ import annotations

from ..enums import (
    BatteryTypeSetting,
    ChargeSourcePrioritySetting,
    OutputSourcePrioritySetting,
)


def build_set_battery_type(battery: BatteryTypeSetting) -> str:
    return battery.value


def build_set_output_priority(mode: OutputSourcePrioritySetting) -> str:
    return mode.value


def build_set_charge_source_priority(mode: ChargeSourcePrioritySetting) -> str:
    return mode.value


def build_set_battery_bulk_voltage(voltage: float) -> str:
    """``PBAVxx.xx`` — bulk (constant) charging voltage."""
    return f"PBAV{voltage:.2f}"


def build_set_battery_float_voltage(voltage: float) -> str:
    """``PBFVxx.xx`` — float charging voltage."""
    return f"PBFV{voltage:.2f}"


def build_set_rated_battery_voltage(voltage: int) -> str:
    """``PBRVxx`` — rated battery voltage (12/24/48...)."""
    return f"PBRV{voltage}"


def build_set_max_combined_charge_current(amps: int) -> str:
    """``MCHGCxxx`` — max combined (utility + solar) charging current."""
    return f"MCHGC{amps:03d}"


def build_set_battery_charge_current(amps: int) -> str:
    """``PBATCxxx`` — max battery charging current."""
    return f"PBATC{amps:03d}"


def build_set_max_utility_charge_current(amps: int) -> str:
    """``MUCHGCxxx`` — max utility (AC) charging current."""
    return f"MUCHGC{amps:03d}"
