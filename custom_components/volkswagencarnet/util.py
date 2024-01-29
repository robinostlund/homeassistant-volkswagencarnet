import logging
from typing import Optional, Union

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import DeviceRegistry, DeviceEntry
from volkswagencarnet.vw_vehicle import Vehicle

from .const import CONF_SCANDINAVIAN_MILES, CONF_NO_CONVERSION, DOMAIN
from .error import ServiceError

_LOGGER = logging.getLogger(__name__)


def get_convert_conf(entry: ConfigEntry) -> Optional[str]:
    """
    Convert old configuration.

    Used in migrating config entry to version 2.
    """
    return (
        CONF_SCANDINAVIAN_MILES
        if entry.options.get(CONF_SCANDINAVIAN_MILES, entry.data.get(CONF_SCANDINAVIAN_MILES, False))
        else CONF_NO_CONVERSION
    )


async def get_coordinator_by_device_id(hass: HomeAssistant, device_id: str):
    """Get the ConfigEntry."""
    registry: DeviceRegistry = device_registry.async_get(hass)
    dev_entry: DeviceEntry = registry.async_get(device_id)

    config_entry = hass.config_entries.async_get_entry(list(dev_entry.config_entries)[0])
    return await get_coordinator(hass, config_entry)


async def get_coordinator(hass: HomeAssistant, config_entry: ConfigEntry):
    """Get the VolkswagenCoordinator."""
    if config_entry.domain != DOMAIN:
        raise ServiceError("Unknown entity")
    coordinator = config_entry.data.get(
        "coordinator",
    )
    if coordinator is None:
        coordinator = hass.data[DOMAIN][config_entry.entry_id]["data"].coordinator
    if coordinator is None:
        raise ServiceError("Unknown entity")
    return coordinator


def get_vehicle(coordinator) -> Vehicle:
    """Find requested vehicle."""
    # find VIN
    _LOGGER.debug(f"Found VIN {coordinator.vin}")
    # parse service call

    v: Optional[Vehicle] = None
    for vehicle in coordinator.connection.vehicles:
        if vehicle.vin.upper() == coordinator.vin:
            v = vehicle
            break
    if v is None:
        raise Exception("Vehicle not found")
    return v


def validate_charge_max_current(charge_max_current: Optional[Union[int, str]]) -> Optional[int]:
    """
    Validate value against known valid ones and return numeric value.

    Maybe there is a way to actually check which values the car supports?
    """
    if (
        charge_max_current is None
        #  not working # or charge_max_current == "max"
        or str(charge_max_current) in ["5", "10", "13", "16", "32", "reduced", "max"]
    ):
        if charge_max_current is None:
            return None
        elif charge_max_current == "max":
            return 254
        elif charge_max_current == "reduced":
            return 252
        return int(charge_max_current)
    raise ValueError(f"{charge_max_current} looks to be an invalid value")
