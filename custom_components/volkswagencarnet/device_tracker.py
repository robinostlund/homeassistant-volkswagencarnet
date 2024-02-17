"""
Support for Volkswagen WeConnect Platform
"""

import logging

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import slugify

from . import VolkswagenEntity
from .const import DATA, DATA_KEY, DOMAIN, SIGNAL_STATE_UPDATED

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    coordinator = data.coordinator
    if coordinator.data is not None:
        async_add_devices(
            VolkswagenDeviceTracker(
                data=data,
                vin=coordinator.vin,
                component=instrument.component,
                attribute=instrument.attr,
            )
            for instrument in (
                instrument for instrument in data.instruments if instrument.component == "device_tracker"
            )
        )

    return True


async def async_setup_scanner(hass, config, async_see, discovery_info=None):
    """Set up the Volkswagen tracker."""
    if discovery_info is None:
        return

    vin, component, attr = discovery_info
    data = hass.data[DATA_KEY]
    instrument = data.instrument(vin, component, attr)

    async def see_vehicle():
        """Handle the reporting of the vehicle position."""
        host_name = data.vehicle_name(instrument.vehicle)
        dev_id = f"{slugify(host_name)}"
        _LOGGER.debug("Getting location of %s" % host_name)
        await async_see(
            dev_id=dev_id,
            host_name=host_name,
            source_type=SourceType.GPS,
            gps=instrument.state,
            icon="mdi:car",
        )

    async_dispatcher_connect(hass, SIGNAL_STATE_UPDATED, see_vehicle)

    return True


class VolkswagenDeviceTracker(VolkswagenEntity, TrackerEntity):
    @property
    def latitude(self) -> float:
        """Return latitude value of the device."""
        return self.instrument.state[0]

    @property
    def longitude(self) -> float:
        """Return longitude value of the device."""
        return self.instrument.state[1]

    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return SourceType.GPS

    @property
    def icon(self):
        """Return the icon."""
        return "mdi:car"
