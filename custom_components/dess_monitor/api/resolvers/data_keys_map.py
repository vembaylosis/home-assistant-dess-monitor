from typing import Dict

SENSOR_KEYS_MAP: Dict[str, list[str]] = {
    "battery_charging_current": [
        "bt_eybond_read_29",
        "bt_battery_charging_current",
        "Battery charging current",
    ],
    "battery_charging_voltage": [
        "bt_vulk_charging_voltage",
        "Battery charging voltage",
    ],
    "battery_discharge_current": [
        "bt_eybond_read_29",
        "bt_battery_discharge_current",
        "bt_discharge_current",
        "Battery discharge current",
    ],
    "battery_voltage": [
        "bt_battery_voltage",
        "Battery Voltage",
    ],
    "active_load_power": [
        "load_active_power",
        "output_power",
        "bc_load_active_power",
    ],
    "active_load_percentage": [
        "bc_eybond_read_37",
        "bc_battery_capacity",
        "bc_load_percent",
    ],
    "output_priority": [
        "bc_output_source_priority",
        "Output priority",
    ],
    "charge_priority": [
        "bt_charger_source_priority",
    ],
    "grid_in_power": [
        "gd_grid_active_power",
    ],
    "battery_capacity": [
        "bt_battery_capacity",
    ],
    "grid_frequency": [
        "gd_grid_frequency",
        "gd_ac_input_frequency",
        "Grid frequency",
    ],
    "pv_power": [
        "pv_output_power",
    ],
    "pv_voltage": [
        "pv_input_voltage",
        "pv_voltage",
        "PV Voltage",
        "PV Input Voltage",
    ],
    "grid_input_voltage": [
        "gd_ac_input_voltage",
        "gd_grid_voltage",
        "Grid Voltage",
    ],
    "grid_output_voltage": [
        "bc_output_voltage",
        "Output Voltage",
    ],
    "dc_module_temperature": [
        "DC Module Termperature",
    ],
    "inv_temperature": [
        "INV Module Termperature",
    ],
    "bt_utility_charge": [
        "bt_utility_charge",
    ],
    "bt_total_charge_current": [
        "bt_total_charge_current",
    ],
    "bt_cutoff_voltage": [
        "bt_battery_cut_off_voltage",
    ],
    "sy_nominal_out_power": [
        "sy_nonimal_output_active_power",
    ],
    "sy_rated_battery_voltage": [
        "sy_rated_battery_voltage",
    ],
    "bt_comeback_utility_voltage": [
        "bt_comeback_utility_iode",
    ],
    "bt_comeback_battery_voltage": [
        "bt_battery_mode_voltage",
    ],
}
