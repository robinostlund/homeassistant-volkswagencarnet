import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry, DeviceRegistry

# pylint: disable=no-name-in-module,hass-relative-import
from volkswagencarnet.vw_vehicle import Vehicle

from .const import CONF_NO_CONVERSION, CONF_SCANDINAVIAN_MILES, DOMAIN
from .error import ServiceError

_LOGGER = logging.getLogger(__name__)


def get_convert_conf(entry: ConfigEntry) -> str | None:
    """Convert old configuration.

    Used in migrating config entry to version 2.
    """
    return (
        CONF_SCANDINAVIAN_MILES
        if entry.options.get(
            CONF_SCANDINAVIAN_MILES, entry.data.get(CONF_SCANDINAVIAN_MILES, False)
        )
        else CONF_NO_CONVERSION
    )


async def get_coordinator_by_device_id(hass: HomeAssistant, device_id: str):
    """Get the ConfigEntry."""
    registry: DeviceRegistry = dr.async_get(hass)
    dev_entry: DeviceEntry = registry.async_get(device_id)

    config_entry = hass.config_entries.async_get_entry(
        list(dev_entry.config_entries)[0]
    )
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
    _LOGGER.debug("Found VIN %s", coordinator.vin)
    # parse service call

    v: Vehicle | None = None
    for vehicle in coordinator.connection.vehicles:
        if vehicle.vin.upper() == coordinator.vin:
            v = vehicle
            break
    if v is None:
        raise Exception("Vehicle not found")  # pylint: disable=broad-exception-raised
    return v


def validate_charge_max_current(charge_max_current: int | str | None) -> int | None:
    """Validate value against known valid ones and return numeric value.

    Maybe there is a way to actually check which values the car supports?
    """
    if (
        charge_max_current is None
        #  not working # or charge_max_current == "max"
        or str(charge_max_current) in ["5", "10", "13", "16", "32", "reduced", "max"]
    ):
        if charge_max_current is None:
            return None
        if charge_max_current == "max":
            return 254
        if charge_max_current == "reduced":
            return 252
        return int(charge_max_current)
    raise ValueError(f"{charge_max_current} looks to be an invalid value")
