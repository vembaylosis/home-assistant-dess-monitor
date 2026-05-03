"""Voltronic device status bit parsers.

QPIGS returns two compact bitfields as ASCII '0'/'1' strings:
``device_status_bits_b7_b0`` (8 bits) and ``device_status_bits_b10_b8``
(3 bits). This module turns either into a flat dict of named booleans
without losing the raw bit pattern.
"""
from __future__ import annotations

from enum import IntEnum, unique


@unique
class DeviceStatusBitsB7B0(IntEnum):
    FAULT = 1 << 7
    RESERVED_B6 = 1 << 6
    BUS_OVER = 1 << 5
    LINE_FAIL = 1 << 4
    BATTERY_LOW = 1 << 3
    BATTERY_HIGH = 1 << 2
    INVERTER_OVERLOAD = 1 << 1
    INVERTER_ON = 1 << 0


@unique
class DeviceStatusBitsB10B8(IntEnum):
    CHARGING_TO_BATTERY = 1 << 2
    CHARGING_AC_ACTIVE = 1 << 1
    CHARGING_SCC_ACTIVE = 1 << 0


def _extract_bits(raw: str, count: int) -> str:
    """Pick out exactly ``count`` bits from ``raw``, ignoring junk chars."""
    bits = [c for c in (raw or "") if c in "01"][:count]
    return "".join(bits).rjust(count, "0")


def parse_device_status_bits_b7_b0(raw: str) -> dict:
    bits = _extract_bits(raw, 8)
    value = int(bits, 2)
    return {
        "fault": bool(value & DeviceStatusBitsB7B0.FAULT),
        "line_fail": bool(value & DeviceStatusBitsB7B0.LINE_FAIL),
        "bus_over": bool(value & DeviceStatusBitsB7B0.BUS_OVER),
        "battery_low": bool(value & DeviceStatusBitsB7B0.BATTERY_LOW),
        "battery_high": bool(value & DeviceStatusBitsB7B0.BATTERY_HIGH),
        "inverter_overload": bool(value & DeviceStatusBitsB7B0.INVERTER_OVERLOAD),
        "inverter_on": bool(value & DeviceStatusBitsB7B0.INVERTER_ON),
        "_raw_b7_b0": bits,
    }


def parse_device_status_bits_b10_b8(raw: str) -> dict:
    bits = _extract_bits(raw, 3)
    value = int(bits, 2)
    return {
        "charging_to_battery": bool(value & DeviceStatusBitsB10B8.CHARGING_TO_BATTERY),
        "charging_scc_active": bool(value & DeviceStatusBitsB10B8.CHARGING_SCC_ACTIVE),
        "charging_ac_active": bool(value & DeviceStatusBitsB10B8.CHARGING_AC_ACTIVE),
        "_raw_b10_b8": bits,
    }
