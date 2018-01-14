"""
Support for the Volkswagen Carnet platform.

"""
import logging

from homeassistant.helpers.event import track_utc_time_change
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)

CARNET_DATA = "volkswagen_carnet"

def setup_scanner(hass, config, see, discovery_info = None):
    """Set up the Volkswagen tracker."""

    VolkswagenDeviceTracker(hass, config, see, hass.data[CARNET_DATA])

    return True

class VolkswagenDeviceTracker(object):
    """A class representing a Tesla device."""

    def __init__(self, hass, config, see, vw):
        """Initialize the Tesla device scanner."""
        self.hass = hass
        self.see = see
        self.vw = vw
        self.devices = self.vw.vehicles
        self._update_location()

        track_utc_time_change(self.hass, self._update_location, second=range(0, 60, 30))

    def _update_location(self, now=None):
        """Update the device info."""
        for device in self.devices:
            device_data = self.devices[device]
            self.vw._carnet_update_location(device_data.get('name'))
            name = "vw_%s" % (device_data.get('name'))
            _LOGGER.debug("Updating device position: %s", name)
            dev_id = slugify(name)
            lat = device_data.get('latitude')
            lon = device_data.get('longitude')
            if lat and lon:
                attrs = {
                    'trackr_id': dev_id,
                    'id': dev_id,
                    'name': name,
                }
                self.see(
                    dev_id=dev_id, host_name=name,
                    gps=(lat, lon), attributes=attrs, icon='mdi:car'
                )