import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry, DeviceRegistry

# pylint: disable=no-name-in-module,hass-relative-import
from volkswagencarnet.vw_vehicle import Vehicle

from .const import CONF_NO_CONVERSION, CONF_SCANDINAVIAN_MILES, DATA, DOMAIN
from .error import ServiceError

if TYPE_CHECKING:
    from . import VolkswagenCoordinator

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


async def get_coordinator_by_device_id(
    hass: HomeAssistant, device_id: str
) -> "VolkswagenCoordinator":
    """Get the ConfigEntry."""
    registry: DeviceRegistry = dr.async_get(hass)
    dev_entry: DeviceEntry = registry.async_get(device_id)

    config_entry = hass.config_entries.async_get_entry(
        list(dev_entry.config_entries)[0]
    )
    return await get_coordinator(hass, config_entry)


async def get_coordinator(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> "VolkswagenCoordinator":
    """Get the VolkswagenCoordinator."""
    if config_entry.domain != DOMAIN:
        raise ServiceError("Integration domain mismatch")

    if config_entry.entry_id not in hass.data.get(DOMAIN, {}):
        raise ServiceError("Integration not loaded for this config entry")

    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    data = entry_data.get(DATA)

    if data is None or data.coordinator is None:
        raise ServiceError("Coordinator not available")

    return data.coordinator


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
        raise ServiceError("Vehicle not found")
    return v
