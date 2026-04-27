"""Standalone smoke tests for the protocol/transport adapter layer.

Run from the repo root::

    python tests/test_protocols_smoke.py

Exits non-zero on any failure. Intentionally avoids ``pytest`` and
``homeassistant`` so it can run in any Python 3.11+ environment.
``custom_components.dess_monitor`` is loaded via stubbed package shells
so we never trigger the HA imports in ``__init__.py``.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import traceback
import types
from pathlib import Path


# ---------------------------------------------------------------------------
# Bootstrap: load custom_components.dess_monitor.api.* without hitting HA.
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
API_DIR = ROOT / "custom_components" / "dess_monitor" / "api"


def _install_namespace(name: str, path: Path) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__path__ = [str(path)]  # type: ignore[attr-defined]
    sys.modules[name] = mod
    return mod


def _load_pkg(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        name,
        str(path / "__init__.py"),
        submodule_search_locations=[str(path)],
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Stub the HA-touching parts so api.transports.cloud_hex doesn't fail to
# import. We won't actually exercise CloudHexTransport here.
_install_namespace("custom_components", ROOT / "custom_components")
_install_namespace(
    "custom_components.dess_monitor",
    ROOT / "custom_components" / "dess_monitor",
)

_sdk_stub = types.ModuleType("custom_components.dess_monitor.sdk")
_sdk_stub.DessmonitorClient = object  # type: ignore[attr-defined]
sys.modules["custom_components.dess_monitor.sdk"] = _sdk_stub

_sdk_models_stub = types.ModuleType("custom_components.dess_monitor.sdk.models")


class _StubDeviceIdentity:
    @classmethod
    def from_dict(cls, d):  # noqa: ANN001
        return d


_sdk_models_stub.DeviceIdentity = _StubDeviceIdentity  # type: ignore[attr-defined]
sys.modules["custom_components.dess_monitor.sdk.models"] = _sdk_models_stub

_load_pkg("custom_components.dess_monitor.api", API_DIR)
_load_pkg("custom_components.dess_monitor.api.protocols", API_DIR / "protocols")
_load_pkg("custom_components.dess_monitor.api.transports", API_DIR / "transports")


# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------

from custom_components.dess_monitor.api.protocols import (  # noqa: E402
    AxpertProtocol,
    Pi18Protocol,
    Smg2ModbusProtocol,
    default_registry,
)
from custom_components.dess_monitor.api.protocols.axpert import set_commands as axpert_set  # noqa: E402
from custom_components.dess_monitor.api.protocols.crc import (  # noqa: E402
    crc16_modbus,
    crc16_modbus_bytes,
    crc16_xmodem,
    crc16_xmodem_bytes,
)
from custom_components.dess_monitor.api.protocols.enums import (  # noqa: E402
    BatteryTypeSetting,
    ChargeSourcePrioritySetting,
    OutputSourcePrioritySetting,
)
from custom_components.dess_monitor.api.protocols.status_bits import (  # noqa: E402
    parse_device_status_bits_b10_b8,
    parse_device_status_bits_b7_b0,
)


# ---------------------------------------------------------------------------
# Tiny test runner
# ---------------------------------------------------------------------------

_PASSED: list[str] = []
_FAILED: list[tuple[str, str]] = []


def check(name: str):
    def deco(fn):
        try:
            fn()
            _PASSED.append(name)
            print(f"  ok    {name}")
        except AssertionError as err:
            _FAILED.append((name, str(err) or repr(err)))
            print(f"  FAIL  {name}: {err}")
        except Exception:  # noqa: BLE001
            tb = traceback.format_exc(limit=3)
            _FAILED.append((name, tb))
            print(f"  ERROR {name}\n{tb}")
        return fn

    return deco


def section(title: str) -> None:
    print(f"\n[{title}]")


def to_hex(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)


# ---------------------------------------------------------------------------
# CRC
# ---------------------------------------------------------------------------

section("CRC")


@check("crc16_xmodem matches the legacy hardcoded table for 11/13 commands")
def _():
    cases = {
        "QPIGS": 0xB7A9,
        "QPIRI": 0xF854,
        "QMOD": 0x49C1,
        "QPIWS": 0xB4DA,
        "QVFW": 0x6299,
        "QMCHGCR": 0xD855,
        "QMUCHGCR": 0x2634,
        "QFLAG": 0x9874,
        "QSID": 0xBB05,
        "QID": 0xD6EA,
        "QMN": 0xBB64,
    }
    for cmd, expected in cases.items():
        got = crc16_xmodem(cmd.encode("ascii"))
        assert got == expected, f"{cmd}: got {got:04X}, want {expected:04X}"


@check("crc16_xmodem deliberately differs from the broken legacy QPIGS2/QBEQI hardcodes")
def _():
    # The pre-refactor table held wrong CRCs for these two; the new
    # computed values are the proper XMODEM result. Pin the expected
    # values so an accidental regression of the polynomial breaks loud.
    assert crc16_xmodem(b"QPIGS2") == 0x682D
    assert crc16_xmodem(b"QBEQI") == 0x2EA9


@check("crc16_modbus matches a published reference vector")
def _():
    # Modbus RTU reference: read holding regs, addr=201, count=31, unit=1
    # Body: 01 03 00 C9 00 1F  -> CRC 3C D4 (low first on the wire => D4 3C)
    body = bytes([0x01, 0x03, 0x00, 0xC9, 0x00, 0x1F])
    assert crc16_modbus(body) == 0x3CD4
    assert crc16_modbus_bytes(body) == bytes([0xD4, 0x3C])


# ---------------------------------------------------------------------------
# AxpertProtocol — encode
# ---------------------------------------------------------------------------

section("AxpertProtocol.encode")

_axpert = AxpertProtocol()


@check("encode produces command + CRC + CR for QPIGS")
def _():
    assert _axpert.encode("QPIGS") == bytes.fromhex("51504947 53B7A9 0D".replace(" ", ""))


@check("encode is case-insensitive on the command name")
def _():
    assert _axpert.encode("qpigs") == _axpert.encode("QPIGS")


@check("encode generates correct frames for set commands (POP01)")
def _():
    cmd = axpert_set.build_set_output_priority(OutputSourcePrioritySetting.SBU)
    assert cmd == "POP01"
    frame = _axpert.encode(cmd)
    # POP01 + CRC + 0x0D
    assert frame.endswith(b"\r")
    assert frame[:-3].decode("ascii") == "POP01"
    assert len(frame) == len("POP01") + 2 + 1


# ---------------------------------------------------------------------------
# AxpertProtocol — decode (parity with the legacy decoders)
# ---------------------------------------------------------------------------

section("AxpertProtocol.decode")


@check("QPIGS decode yields all 21 expected fields with raw string values")
def _():
    raw = (
        b"(231.8 50.0 231.8 50.0 0115 0016 002 408 27.00 012 095 0030 "
        b"0000 000.0 00.00 00000 00010101 00 00 00001 010\xff\xff\r"
    )
    out = _axpert.decode("QPIGS", raw)
    assert out["grid_voltage"] == "231.8"
    assert out["grid_frequency"] == "50.0"
    assert out["battery_voltage"] == "27.00"
    assert out["battery_capacity"] == "095"
    assert out["device_status_bits_b7_b0"] == "00010101"
    assert "error" not in out and "status" not in out


@check("QPIRI decode applies enum mapping at the right positions")
def _():
    raw = (
        b"(230.0 21.7 230.0 50.0 21.7 5000 5000 48.0 46.0 42.0 56.4 54.0 "
        b"2 30 060 0 1 2 9 01 0 0 54.0 0 1 480 0 000\xff\xff\r"
    )
    out = _axpert.decode("QPIRI", raw)
    assert out["battery_type"] == "UserDefined"
    assert out["ac_input_voltage_range"] == "Appliance"
    assert out["output_source_priority"] == "SolarFirst"
    assert out["charger_source_priority"] == "SolarAndUtility"


@check("QPIGS2 decode returns the 3-field PV section")
def _():
    raw = b"(02.5 245.6 1234\xff\xff\r"
    out = _axpert.decode("QPIGS2", raw)
    assert out == {"pv_current": "02.5", "pv_voltage": "245.6", "pv_daily_energy": "1234"}


@check("QMOD decode resolves the operating-mode letter to its enum name")
def _():
    out = _axpert.decode("QMOD", b"(L\xff\xff\r")
    assert out == {"operating_mode": "Line"}


@check("decode reports a structured error for null and empty replies")
def _():
    err1 = _axpert.decode("QPIGS", b"")
    err2 = _axpert.decode("QPIGS", b"null")
    assert err1.get("error") and err2.get("error")


@check("ACK/NAK control replies surface as {'status': ...}")
def _():
    ack = _axpert.decode("POP01", b"(ACK\x39\x20\r")
    nak = _axpert.decode("POP01", b"(NAK\xff\xff\r")
    assert ack == {"status": "ACK"}
    assert nak == {"status": "NAK"}


# ---------------------------------------------------------------------------
# Set-command builders
# ---------------------------------------------------------------------------

section("axpert_set builders")


@check("priority/charger/battery-type builders return the documented codes")
def _():
    assert axpert_set.build_set_output_priority(OutputSourcePrioritySetting.UtilityFirst) == "POP00"
    assert axpert_set.build_set_output_priority(OutputSourcePrioritySetting.SBU) == "POP01"
    assert axpert_set.build_set_output_priority(OutputSourcePrioritySetting.SolarFirst) == "POP02"
    assert axpert_set.build_set_charge_source_priority(ChargeSourcePrioritySetting.SolarFirst) == "PCP01"
    assert axpert_set.build_set_battery_type(BatteryTypeSetting.AGM) == "PBT00"


@check("voltage/current builders apply the documented formatting")
def _():
    assert axpert_set.build_set_battery_bulk_voltage(56.4) == "PBAV56.40"
    assert axpert_set.build_set_battery_float_voltage(54.0) == "PBFV54.00"
    assert axpert_set.build_set_rated_battery_voltage(48) == "PBRV48"
    assert axpert_set.build_set_max_combined_charge_current(60) == "MCHGC060"
    assert axpert_set.build_set_battery_charge_current(30) == "PBATC030"
    assert axpert_set.build_set_max_utility_charge_current(2) == "MUCHGC002"


# ---------------------------------------------------------------------------
# Status bits
# ---------------------------------------------------------------------------

section("status bits")


@check("parse_device_status_bits_b7_b0 unpacks named flags + keeps the raw")
def _():
    out = parse_device_status_bits_b7_b0("00010001")
    assert out["inverter_on"] is True
    assert out["line_fail"] is True
    assert out["fault"] is False
    assert out["_raw_b7_b0"] == "00010001"


@check("parse_device_status_bits_b10_b8 unpacks the 3-bit charge state")
def _():
    out = parse_device_status_bits_b10_b8("010")
    assert out["charging_ac_active"] is True
    assert out["charging_to_battery"] is False
    assert out["charging_scc_active"] is False


@check("status bit parsers tolerate junk input by clamping to N bits")
def _():
    assert parse_device_status_bits_b7_b0("xx10")["_raw_b7_b0"] == "00000010"
    assert parse_device_status_bits_b10_b8("")["_raw_b10_b8"] == "000"


# ---------------------------------------------------------------------------
# Smg2ModbusProtocol — round-trip
# ---------------------------------------------------------------------------

section("Smg2ModbusProtocol")

_smg2 = Smg2ModbusProtocol(unit_id=1)


def _build_modbus_response(unit_id: int, registers: list[int]) -> bytes:
    body = bytes([unit_id, 0x03, len(registers) * 2])
    for r in registers:
        body += bytes([(r >> 8) & 0xFF, r & 0xFF])
    return body + crc16_modbus_bytes(body)


@check("encode builds a function-0x03 read frame at the QPIGS register block")
def _():
    frame = _smg2.encode("QPIGS")
    # unit=1, func=3, addr=0x00C9 (201), count=0x001F (31), CRC
    assert frame[:6] == bytes([0x01, 0x03, 0x00, 0xC9, 0x00, 0x1F])
    assert len(frame) == 8
    assert crc16_modbus(frame[:6]) == frame[6] | (frame[7] << 8)


@check("encode raises for an unsupported command")
def _():
    raised = False
    try:
        _smg2.encode("QFLAG")
    except ValueError:
        raised = True
    assert raised, "expected ValueError for unsupported command"


@check("decode QPIGS maps registers into the same dict shape as Axpert")
def _():
    regs = [0] * 31

    def setreg(addr: int, val: int) -> None:
        regs[addr - 201] = val & 0xFFFF

    setreg(202, 2305)    # mains voltage 230.5 V
    setreg(210, 2300)    # output voltage 230.0 V
    setreg(213, 1500)    # output power 1500 W
    setreg(215, 240)     # battery voltage 24.0 V
    setreg(216, 25)      # battery current +25 A → charging
    setreg(220, 50)      # PV current 5.0 A
    setreg(223, 1200)    # PV power 1200 W
    setreg(225, 30)      # load 30 %

    out = _smg2.decode("QPIGS", _build_modbus_response(1, regs))
    assert out["grid_voltage"] == "230.5"
    assert out["ac_output_voltage"] == "230.0"
    assert out["battery_voltage"] == "24.00"
    assert out["battery_charging_current"] == "025"
    assert out["battery_discharge_current"] == "00000"
    assert out["pv_charging_power"] == "01200"
    assert out["load_percent"] == "030"
    # Bus voltage placeholder removed — SMG-II has no register for it.
    assert "bus_voltage" not in out


@check("decode QPIRI maps register-encoded enums to readback enum names")
def _():
    regs = [0] * 38

    def setreg(addr: int, val: int) -> None:
        regs[addr - 300] = val & 0xFFFF

    setreg(301, 2)    # output_priority -> SBU
    setreg(302, 1)    # input_voltage_range -> UPS
    setreg(331, 1)    # battery_charging_priority -> SolarFirst
    setreg(324, 568)  # bulk 56.8 V
    setreg(332, 600)  # max charging 60.0 A

    out = _smg2.decode("QPIRI", _build_modbus_response(1, regs))
    assert out["output_source_priority"] == "SBU"
    assert out["ac_input_voltage_range"] == "UPS"
    assert out["charger_source_priority"] == "SolarFirst"
    assert out["bulk_charging_voltage"] == "56.8"
    assert out["max_charging_current"] == "060"


@check("decode QMOD reuses the sensor block and lifts the operation register")
def _():
    regs = [0] * 31
    regs[201 - 201] = 2  # 'Mains' → Line in our enum
    out = _smg2.decode("QMOD", _build_modbus_response(1, regs))
    assert out == {"operating_mode": "Line"}


@check("Modbus exception responses become {'error': ...} with the exception code")
def _():
    body = bytes([0x01, 0x83, 0x02])  # illegal data address
    response = body + crc16_modbus_bytes(body)
    out = _smg2.decode("QPIGS", response)
    assert "error" in out
    assert "0x02" in out["error"]


@check("decode rejects responses with a CRC mismatch")
def _():
    regs = [0] * 31
    response = _build_modbus_response(1, regs)
    corrupted = response[:-1] + bytes([response[-1] ^ 0xFF])
    out = _smg2.decode("QPIGS", corrupted)
    assert out.get("error", "").lower().startswith("modbus crc")


# ---------------------------------------------------------------------------
# Pi18Protocol — frame round-trip
# ---------------------------------------------------------------------------

section("Pi18Protocol")

_pi18 = Pi18Protocol()


def _build_pi18_response(body: str) -> bytes:
    """Wrap an ASCII payload in the ``^D<nnn>...<CRC><CR>`` envelope."""
    body_bytes = body.encode("ascii")
    length = len(body_bytes) + 3
    head = f"^D{length:03d}".encode("ascii") + body_bytes
    return head + crc16_xmodem_bytes(head) + b"\r"


@check("encode wraps QPIGS as ^P005GS<CRC><CR> with computed XMODEM CRC")
def _():
    frame = _pi18.encode("QPIGS")
    assert frame.startswith(b"^P005GS")
    assert frame.endswith(b"\r")
    # frame layout: ^P005GS (7) + CRC (2) + CR (1) = 10 bytes
    assert len(frame) == 10
    assert crc16_xmodem(frame[:-3]) == (frame[-3] << 8) | frame[-2]


@check("encode of native names skips the logical->native mapping")
def _():
    # Encoding "PI" directly should still produce a valid ^P005PI frame.
    frame = _pi18.encode("PI")
    assert frame.startswith(b"^P005PI")
    assert frame.endswith(b"\r")


@check("encode handles longer commands (PIRI -> ^P007PIRI)")
def _():
    frame = _pi18.encode("QPIRI")
    assert frame.startswith(b"^P007PIRI")


@check("decode GS returns multi-section qpigs+qpigs2 with no bus_voltage hardcode")
def _():
    # 28-field GS reply with realistic-ish numbers. PI18 uses 0.1 V and 0.1 Hz
    # encoding for voltages/frequencies, raw amps for currents.
    body = (
        "2305,500,2300,500,1500,1500,030,2456,2456,0000,000,025,"
        "100,45,40,40,1200,0500,2400,1500,0,2,0,1,1,2,1,0"
    )
    out = _pi18.decode("QPIGS", _build_pi18_response(body))

    qpigs = out["qpigs"]
    assert qpigs["grid_voltage"] == "230.5"
    assert qpigs["grid_frequency"] == "50.0"
    assert qpigs["ac_output_voltage"] == "230.0"
    assert qpigs["battery_voltage"] == "245.60"
    assert qpigs["battery_charging_current"] == "025"
    assert qpigs["battery_discharge_current"] == "00000"
    assert qpigs["pv_charging_power"] == "01200"
    assert qpigs["pv_input_voltage"] == "240.0"
    assert qpigs["load_percent"] == "030"
    # PI1 current synthesised from power/voltage: 1200 W / 240 V = 5.0 A
    assert qpigs["pv_input_current"] == "5.0"
    # bus_voltage placeholder removed — sensor falls through to Unavailable.
    assert "bus_voltage" not in qpigs

    qpigs2 = out["qpigs2"]
    # PV2 voltage = 1500 / 10 = 150.0 V; PV2 power = 500 W; current = 500/150
    assert qpigs2["pv_voltage"] == "150.0"
    assert qpigs2["pv_current"].startswith("3.")  # ~3.33 A


@check("decode PIRI swaps PI18 III/JJJ onto the right Axpert thresholds")
def _():
    # Reproduces the real 48 V LFP system in the user's screenshots:
    # III=480 (re-charge → battery low) should land on
    # ``low_battery_to_ac_bypass_voltage``; JJJ=530 (re-discharge → battery
    # high) on ``high_battery_voltage_to_battery_mode``.
    body = (
        "2300,260,2300,500,260,6000,6000,480,480,530,420,565,565,"
        "2,2,100,0,1,2,9,0,0,0,1,1"
    )
    out = _pi18.decode("QPIRI", _build_pi18_response(body))
    assert out["battery_type"] == "UserDefined"
    assert out["ac_input_voltage_range"] == "Appliance"  # Q=0
    assert out["output_source_priority"] == "SBU"        # R=1
    assert out["charger_source_priority"] == "OnlySolar" # S=2
    assert out["bulk_charging_voltage"] == "56.5"
    assert out["max_charging_current"] == "100"

    # The swap: low (battery → AC) = III, high (battery → battery mode) = JJJ.
    assert out["low_battery_to_ac_bypass_voltage"] == "48.0"
    assert out["high_battery_voltage_to_battery_mode"] == "53.0"

    # Reserved fields are not emitted for PI18 — sensors go Unavailable
    # rather than report a misleading constant 0.
    for key in ("reserved_uu", "reserved_v", "reserved_b", "reserved_ccc"):
        assert key not in out


@check("decode PIRI omits enum keys when the device returns blank or unknown codes")
def _():
    # Position 13 (battery_type), 16 (input_voltage_range), 17 (output_priority),
    # 18 (charger_priority) are all blank — decoder must drop them so sensors
    # land at Unavailable rather than displaying a raw numeric token.
    body = (
        "2300,260,2300,500,260,6000,6000,480,480,530,420,565,565,"
        ",2,100,,,,9,0,0,0,1,1"
    )
    out = _pi18.decode("QPIRI", _build_pi18_response(body))
    for key in (
        "battery_type",
        "ac_input_voltage_range",
        "output_source_priority",
        "charger_source_priority",
    ):
        assert key not in out, f"unexpected key {key} in {out}"


@check("decode MOD maps PI18 mode codes 0..5 onto OperatingMode names")
def _():
    cases = {
        "00": "PowerOn",
        "01": "Standby",
        "02": "Line",        # Bypass
        "03": "Battery",
        "04": "Fault",
        "05": "Line",        # Hybrid (Line/Grid)
    }
    for code, expected in cases.items():
        out = _pi18.decode("QMOD", _build_pi18_response(code))
        assert out == {"operating_mode": expected}, (code, out)


@check("decode recognises ^1 / ^0 set-command markers as ACK / NAK")
def _():
    ack = _pi18.decode("POPM", b"^1\xab\xcd\r")
    nak = _pi18.decode("POPM", b"^0\xab\xcd\r")
    assert ack == {"status": "ACK"}
    assert nak == {"status": "NAK"}


@check("decode reports a structured error for empty / null replies")
def _():
    assert _pi18.decode("QPIGS", b"").get("error")
    assert _pi18.decode("QPIGS", b"null").get("error")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

section("ProtocolRegistry")


@check("default registry resolves axpert / smg2_modbus / pi18 by name")
def _():
    assert isinstance(default_registry.get("axpert"), AxpertProtocol)
    assert isinstance(default_registry.get("smg2_modbus"), Smg2ModbusProtocol)
    assert isinstance(default_registry.get("pi18"), Pi18Protocol)


@check("default registry falls back to axpert for unknown names")
def _():
    assert isinstance(default_registry.get("does-not-exist"), AxpertProtocol)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print(f"\n{'-' * 60}")
print(f"passed: {len(_PASSED)}    failed: {len(_FAILED)}")
if _FAILED:
    print("\nFailures:")
    for name, msg in _FAILED:
        print(f"  - {name}: {msg.splitlines()[0] if msg else '(no message)'}")
    sys.exit(1)
sys.exit(0)
