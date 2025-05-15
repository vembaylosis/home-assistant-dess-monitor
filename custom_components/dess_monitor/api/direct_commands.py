def decode_ascii_response(hex_string):
    hex_values = hex_string.strip().split()
    byte_values = bytes(int(b, 16) for b in hex_values)
    ascii_str = byte_values.decode('ascii', errors='ignore').strip()
    if ascii_str.startswith('('):
        ascii_str = ascii_str[1:]
    return ascii_str


def decode_qpigs(ascii_str):
    values = ascii_str.split()
    fields = [
        "grid_voltage",
        "grid_frequency",
        "ac_output_voltage",
        "ac_output_frequency",
        "output_apparent_power",
        "output_active_power",
        "load_percent",
        "bus_voltage",
        "battery_voltage",
        "battery_charging_current",
        "battery_capacity",
        "inverter_heat_sink_temperature",
        "pv_input_current",
        "pv_input_voltage",
        "scc_battery_voltage",
        "battery_discharge_current",
        "device_status_bits_b7_b0",
        "battery_voltage_offset",
        "eeprom_version",
        "pv_charging_power",
        "device_status_bits_b10_b8",
        "reserved_a",
        "reserved_bb",
        "reserved_cccc"
    ]
    return dict(zip(fields, values))


def decode_qpiri(ascii_str):
    values = ascii_str.split()
    fields = [
        "Rated Grid Voltage", "Rated Input Current", "Rated AC Output Voltage",
        "Rated Output Frequency", "Rated Output Current", "Rated Output Apparent Power",
        "Rated Output Active Power", "Rated Battery Voltage", "Low Battery to AC Bypass Voltage",
        "Shut Down Battery Voltage", "Bulk Charging Voltage", "Float Charging Voltage",
        "Battery Type", "Max Utility Charging Current", "Max Charging Current",
        "AC Input Voltage Range", "Output Source Priority", "Charger Source Priority",
        "Parallel Max Number", "Reserved UU", "Reserved V", "Parallel Mode",
        "High Battery Voltage to Battery Mode", "Solar Work Condition in Parallel",
        "Solar Max Charging Power Auto Adjust", "Rated Battery Capacity", "Reserved b", "Reserved ccc"
    ]
    return dict(zip(fields, values))


def decode_qmod(ascii_str):
    mode = ascii_str.strip()[0]  # Only first character
    modes = {
        'P': "Power On",
        'S': "Standby",
        'L': "Line (Bypass)",
        'B': "Battery Inverter Mode",
        'D': "Shutdown Approaching",
        'F': "Fault"
    }
    return {"Operating Mode": modes.get(mode, "Unknown")}


def decode_qmn(ascii_str):
    return {"Model": ascii_str.strip()}


def decode_qid(ascii_str):
    return {"Device ID": ascii_str.strip()}


def decode_qflag(ascii_str):
    return {"Enabled/Disabled Flags": ascii_str.strip()}


def decode_qvfw(ascii_str):
    return {"Firmware Version": ascii_str.replace("VERFW:", "").strip()}


def decode_qbeqi(ascii_str):
    values = ascii_str.split()
    fields = [
        "Equalization Function", "Equalization Time (min)", "Interval Days",
        "Max Charging Current", "Float Voltage", "Reserved 1",
        "Equalization Timeout (min)", "Immediate Activation Flag", "Elapsed Time (min)"
    ]
    return dict(zip(fields, values))


# Тестовый универсальный декодер
def decode_direct_response(command: str, hex_input: str) -> dict:
    ascii_str = decode_ascii_response(hex_input)

    match command.upper():
        case "QPIGS":
            return decode_qpigs(ascii_str)
        case "QPIRI":
            return decode_qpiri(ascii_str)
        case "QMOD":
            return decode_qmod(ascii_str)
        case "QMN":
            return decode_qmn(ascii_str)
        case "QID" | "QSID":
            return decode_qid(ascii_str)
        case "QFLAG":
            return decode_qflag(ascii_str)
        case "QVFW":
            return decode_qvfw(ascii_str)
        case "QBEQI":
            return decode_qbeqi(ascii_str)
        case _:
            return {"Raw": ascii_str}


direct_commands = {
    "QPIGS": "51 50 49 47 53 B7 A9 0D",
    "QPIGS2": "51 50 49 47 53 32 2B 8A 0D",
    "QPIRI": "51 50 49 52 49 F8 54 0D",
    "QMOD": "51 4D 4F 44 49 C1 0D",
    "QPIWS": "51 50 49 57 53 B4 DA 0D",
    "QVFW": "51 56 46 57 62 99 0D",
    "QMCHGCR": "51 4D 43 48 47 43 52 D8 55 0D",
    "QMUCHGCR": "51 4D 55 43 48 47 43 52 26 34 0D",
    "QFLAG": "51 46 4C 41 47 98 74 0D",
    "QSID": "51 53 49 44 BB 05 0D",
    "QID": "51 49 44 D6 EA 0D",
    "QMN": "51 4D 4E BB 64 0D",
    "QBEQI": "51 42 45 51 49 31 6B 0D",  # CRC может отличаться в зависимости от устройства
}


def get_command_hex(command_name: str) -> str:
    return direct_commands.get(command_name.upper(), "Unknown command")


# Функция поиска команды по HEX
def get_command_name_by_hex(hex_string: str) -> str:
    normalized_input = hex_string.strip().upper().replace("  ", " ")
    for name, hex_cmd in direct_commands.items():
        if normalized_input == hex_cmd.upper():
            return name
    return "Unknown HEX command"

# # Пример вызова:
# hex_data = "28 32 33 34 2E 32 20 35 30 2E 30 20 32 33 30 2E 31 20 35 30 2E 30 20 30 31 36 31 20 30 31 30 39 20 30 30 34 20 34 33 30 20 32 37 2E 32 30 20 30 30 33 20 30 38 32 20 30 30 33 30 20 30 30 30 33 20 33 31 37 2E 37 20 30 30 2E 30 30 20 30 30 30 30 30 20 30 30 30 31 30 31 31 30 20 30 30 20 30 30 20 30 30 31 38 31 20 31 31 30 76 26 0D"
# decoded = decode_direct_response('QPIGS', hex_data)
#
# for key, value in decoded.items():
#     print(f"{key:35} : {value}")
