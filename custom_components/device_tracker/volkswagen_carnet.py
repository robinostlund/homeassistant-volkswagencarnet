"""
Support for the Volkswagen Carnet platform.

"""
import logging

from homeassistant.helpers.event import track_utc_time_change
from homeassistant.util import slugify

from custom_components.volkswagen_carnet import CARNET_DATA

_LOGGER = logging.getLogger(__name__)

def setup_scanner(hass, config, see, discovery_info = None):
    """Set up the Volkswagen tracker."""

    VolkswagenDeviceTracker(hass, config, see, hass.data[CARNET_DATA])

    return True

class VolkswagenDeviceTracker(object):
    """A class representing a Tesla device."""

    def __init__(self, hass, config, see, vw):
        """Initialize the Volkswagen device scanner."""
        self.hass = hass
        self.see = see
        self.vw = vw
        self.vehicles = self.vw.vehicles
        self._update_location()

        track_utc_time_change(self.hass, self._update_location, second=range(0, 60, 30))

    def _update_location(self, now=None):
        """Update the device info."""
        for vehicle in self.vehicles:
            vehicle_data = self.vehicles[vehicle]
            name = vehicle_data.get('name')
            car_id = 'vw_%s' % vehicle_data.get('vin')

            _LOGGER.debug("Updating device position for vehicle: %s", vehicle_data.get('vin'))

            dev_id = slugify(car_id)
            lat = vehicle_data.get('location_latitude')
            lon = vehicle_data.get('location_longitude')
            if lat and lon:
                attrs = {
                    'trackr_id': dev_id,
                    'id': dev_id,
                    'name': dev_id,
                    'entity_picture': vehicle_data.get('model_image_url')
                }
                self.see(
                    dev_id=dev_id, host_name=name,
                    gps=(lat, lon), attributes=attrs,
                    icon='mdi:car', battery=vehicle_data['sensor_battery_left']
                )