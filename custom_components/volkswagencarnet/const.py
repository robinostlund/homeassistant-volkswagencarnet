"""Common constants."""

from datetime import timedelta

DOMAIN = "volkswagencarnet"
DATA_KEY = DOMAIN

DEFAULT_REGION = "DE"
DEFAULT_DEBUG = False

CONF_REGION = "region"
CONF_MUTABLE = "mutable"
CONF_SPIN = "spin"
CONF_SCANDINAVIAN_MILES = "scandinavian_miles"
CONF_IMPERIAL_UNITS = "imperial_units"
CONF_NO_CONVERSION = "no_conversion"
CONF_CONVERT = "convert"
CONF_VEHICLE = "vehicle"
CONF_REPORT_REQUEST = "report_request"
CONF_REPORT_SCAN_INTERVAL = "report_scan_interval"
CONF_DEBUG = "debug"
CONF_AVAILABLE_RESOURCES = "available_resources"

UPDATE_CALLBACK = "update_callback"
DATA = "data"
UNDO_UPDATE_LISTENER = "undo_update_listener"

SIGNAL_STATE_UPDATED = f"{DOMAIN}.updated"

MIN_UPDATE_INTERVAL = timedelta(minutes=1)
DEFAULT_UPDATE_INTERVAL = 5
DEFAULT_REPORT_UPDATE_INTERVAL = 1

CONVERT_DICT = {
    CONF_NO_CONVERSION: "No conversion",
    CONF_IMPERIAL_UNITS: "Imperial units",
    CONF_SCANDINAVIAN_MILES: "km to mil",
}

COMPONENTS = {
    "sensor": "sensor",
    "binary_sensor": "binary_sensor",
    "lock": "lock",
    "device_tracker": "device_tracker",
    "switch": "switch",
    "number": "number",
}

SERVICE_SET_CHARGER_MAX_CURRENT = "set_charger_max_current"
