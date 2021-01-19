from datetime import timedelta

DOMAIN = "volkswagencarnet"
DATA_KEY = DOMAIN
CONF_REGION = "region"
DEFAULT_REGION = "SV"
CONF_MUTABLE = "mutable"
CONF_SPIN = "spin"
CONF_SCANDINAVIAN_MILES = "scandinavian_miles"
CONF_VEHICLE = "vehicle"

DATA = "data"
UNDO_UPDATE_LISTENER = "undo_update_listener"

SIGNAL_STATE_UPDATED = f"{DOMAIN}.updated"

MIN_UPDATE_INTERVAL = timedelta(minutes=1)
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=5)

COMPONENTS = {
    "sensor": "sensor",
    "binary_sensor": "binary_sensor",
    "lock": "lock",
    "device_tracker": "device_tracker",
    "switch": "switch",
    "climate": "climate",
}
RESOURCES_DICT = {
    "position":                               "Position",
    "distance":                               "Distance",
    "electric_climatisation":                 "Electric Climatisation",
    "combustion_climatisation":               "Combustion Climatisation",
    "window_heater":                          "Window Heater",
    "combustion_engine_heating":              "Combustion Engine Heating",
    "charging":                               "Charging",
    "adblue_level":                           "Adblue Level",
    "battery_level":                          "Battery Level",
    "fuel_level":                             "Fuel Level",
    "service_inspection":                     "Service Inspection",
    "oil_inspection":                         "Oil Inspection",
    "last_connected":                         "Last Connected",
    "charging_time_left":                     "Charging Time Left",
    "electric_range":                         "Electric Range",
    "combustion_range":                       "Combustion Range",
    "combined_range":                         "Combined Range",
    "charge_max_ampere":                      "Charge Max Ampere",
    "climatisation_target_temperature":       "Climatisation Target Temperature",
    "external_power":                         "External Power",
    "parking_light":                          "Parking Light",
    "climatisation_without_external_power":   "Climatisation Without External Power",
    "door_locked":                            "Door Locked",
    "door_closed_left_front":                 "Door Closed Left Front",
    "door_closed_right_front":                "Door Closed Right Front",
    "door_closed_left_back":                  "Door Closed Left Back",
    "door_closed_right_back":                 "Door Closed Right Back",
    "trunk_locked":                           "Trunk Locked",
    "trunk_closed":                           "Trunk Closed",
    "request_in_progress":                    "Request In Progress",
    "windows_closed":                         "Windows Closed",
    "window_closed_left_front":               "Window Closed Left Front",
    "window_closed_right_front":              "Window Closed Right Front",
    "window_closed_left_back":                "Window Closed Left Back",
    "window_closed_right_back":               "Window Closed Right Back",
    "sunroof_closed":                         "Sunroof Closed",
    "trip_last_average_speed":                "Trip Last Average Speed",
    "trip_last_average_electric_consumption": "Trip Last Average Electric Consumption",
    "trip_last_average_fuel_consumption":     "Trip Last Average Fuel Consumption",
    "trip_last_duration":                     "Trip Last Duration",
    "trip_last_length":                       "Trip Last Length",
}

RESOURCES = [
    "position",
    "distance",
    "electric_climatisation",
    "combustion_climatisation",
    "window_heater",
    "combustion_engine_heating",
    "charging",
    "adblue_level",
    "battery_level",
    "fuel_level",
    "service_inspection",
    "oil_inspection",
    "last_connected",
    "charging_time_left",
    "electric_range",
    "combustion_range",
    "combined_range",
    "charge_max_ampere",
    "climatisation_target_temperature",
    "external_power",
    "parking_light",
    "climatisation_without_external_power",
    "door_locked",
    "door_closed_left_front",
    "door_closed_right_front",
    "door_closed_left_back",
    "door_closed_right_back",
    "trunk_locked",
    "trunk_closed",
    "request_in_progress",
    "windows_closed",
    "window_closed_left_front",
    "window_closed_right_front",
    "window_closed_left_back",
    "window_closed_right_back",
    "sunroof_closed",
    "trip_last_average_speed",
    "trip_last_average_electric_consumption",
    "trip_last_average_fuel_consumption",
    "trip_last_duration",
    "trip_last_length",
]
