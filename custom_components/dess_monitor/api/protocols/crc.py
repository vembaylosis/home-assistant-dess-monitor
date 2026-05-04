"""CRC routines used by the inverter protocols.

Voltronic Axpert (PI30) and InfiniSolar PI18 frames are both protected by
CRC-16/XMODEM (poly 0x1021, init 0x0000, no reflection, no xor-out).
"""
from __future__ import annotations


def crc16_xmodem(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


def crc16_xmodem_bytes(data: bytes) -> bytes:
    crc = crc16_xmodem(data)
    return bytes([(crc >> 8) & 0xFF, crc & 0xFF])


def crc16_modbus(data: bytes) -> int:
    """Standard Modbus CRC-16 (poly 0xA001, init 0xFFFF, refin/refout, no xor-out)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def crc16_modbus_bytes(data: bytes) -> bytes:
    """Modbus CRC as wire bytes (low byte first, as transmitted on RTU)."""
    crc = crc16_modbus(data)
    return bytes([crc & 0xFF, (crc >> 8) & 0xFF])
