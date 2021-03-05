from datetime import timedelta

DOMAIN = "volkswagencarnet"
DATA_KEY = DOMAIN
CONF_REGION = "region"
DEFAULT_REGION = "SV"
CONF_MUTABLE = "mutable"
CONF_SPIN = "spin"
CONF_SCANDINAVIAN_MILES = "scandinavian_miles"
CONF_VEHICLE = "vehicle"
CONF_REPORT_REQUEST = "report_request"
CONF_REPORT_SCAN_INTERVAL = "report_scan_interval"

DATA = "data"
UNDO_UPDATE_LISTENER = "undo_update_listener"

SIGNAL_STATE_UPDATED = f"{DOMAIN}.updated"

MIN_UPDATE_INTERVAL = timedelta(minutes=1)
DEFAULT_UPDATE_INTERVAL = 5
DEFAULT_REPORT_UPDATE_INTERVAL = 1

COMPONENTS = {
    "sensor": "sensor",
    "binary_sensor": "binary_sensor",
    "lock": "lock",
    "device_tracker": "device_tracker",
    "switch": "switch",
    "climate": "climate",
}
RESOURCES_DICT = {
    "adblue_level": "Adblue Level",
    "battery_level": "Battery Level",
    "charge_max_ampere": "Charge Max Ampere",
    "charging": "Charging",
    "charging_time_left": "Charging Time Left",
    "climatisation_target_temperature": "Climatisation Target Temperature",
    "climatisation_without_external_power": "Climatisation Without External Power",
    "combined_range": "Combined Range",
    "combustion_climatisation": "Combustion Climatisation",
    "combustion_engine_heating": "Combustion Engine Heating",
    "combustion_range": "Combustion Range",
    "distance": "Distance",
    "door_closed_left_back": "Door Closed Left Back",
    "door_closed_left_front": "Door Closed Left Front",
    "door_closed_right_back": "Door Closed Right Back",
    "door_closed_right_front": "Door Closed Right Front",
    "door_locked": "Door Locked",
    "electric_climatisation": "Electric Climatisation",
    "electric_range": "Electric Range",
    "external_power": "External Power",
    "fuel_level": "Fuel Level",
    "last_connected": "Last Connected",
    "oil_inspection": "Oil Inspection",
    "parking_light": "Parking Light",
    "position": "Position",
    "request_in_progress": "Request In Progress",
    "service_inspection": "Service Inspection",
    "sunroof_closed": "Sunroof Closed",
    "trip_last_average_electric_consumption": "Trip Last Average Electric Consumption",
    "trip_last_average_fuel_consumption": "Trip Last Average Fuel Consumption",
    "trip_last_average_speed": "Trip Last Average Speed",
    "trip_last_duration": "Trip Last Duration",
    "trip_last_length": "Trip Last Length",
    "trip_last_recuperation": "Trip Last Recuperation",
    "trip_last_average_auxillary_consumption": "Trip Last Avarage Auxillary Consumption",
    "trip_last_total_electric_consumption": "Trip Last Total Electricity Consumption",
    "trunk_closed": "Trunk Closed",
    "trunk_locked": "Trunk Locked",
    "window_closed_left_back": "Window Closed Left Back",
    "window_closed_left_front": "Window Closed Left Front",
    "window_closed_right_back": "Window Closed Right Back",
    "window_closed_right_front": "Window Closed Right Front",
    "window_heater": "Window Heater",
    "windows_closed": "Windows Closed",
}
