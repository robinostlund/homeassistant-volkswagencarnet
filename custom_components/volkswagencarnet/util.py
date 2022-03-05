from typing import Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import DeviceRegistry, DeviceEntry
from volkswagencarnet.vw_vehicle import Vehicle

import const
from custom_components.volkswagencarnet import DOMAIN
from error import ServiceError
from services import _LOGGER


def get_convert_conf(entry: ConfigEntry) -> Optional[str]:
    return (
        const.CONF_SCANDINAVIAN_MILES
        if entry.options.get(const.CONF_SCANDINAVIAN_MILES, entry.data.get(const.CONF_SCANDINAVIAN_MILES, False))
        else const.CONF_NO_CONVERSION
    )


async def get_coordinator(hass: HomeAssistant, device_id: str):
    """Get the VolkswagenCoordinator."""
    registry: DeviceRegistry = device_registry.async_get(hass)
    dev_entry: DeviceEntry = registry.async_get(device_id)

    # Get coordinator handling the device entry
    config_entry = hass.config_entries.async_get_entry(list(dev_entry.config_entries)[0])
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
