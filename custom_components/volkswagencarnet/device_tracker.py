"""
Support for Volkswagen Carnet Platform
"""
import logging

from homeassistant.util import slugify
from homeassistant.helpers.dispatcher import (dispatcher_connect, dispatcher_send)
from custom_components.volkswagencarnet import SIGNAL_VEHICLE_SEEN, DATA_KEY

_LOGGER = logging.getLogger(__name__)

def setup_scanner(hass, config, see, discovery_info=None):
    """Set up the Volvo tracker."""
    if discovery_info is None:
        return

    vin, _ = discovery_info
    vw = hass.data[DATA_KEY]
    vehicle = vw.vehicles[vin]

    def see_vehicle(vehicle):
        """Handle the reporting of the vehicle position."""
        host_name = vw.vehicle_name(vehicle)
        dev_id = '{}'.format(slugify(host_name))
        attrs = {}
        if vehicle.model_image:
            attrs['entity_picture'] = vehicle.model_image
        _LOGGER.debug('Updating location of %s' % host_name)
        see(dev_id=dev_id, host_name=host_name, gps=(vehicle.position['lat'], vehicle.position['lng']), attributes=attrs, icon='mdi:car')

    dispatcher_connect(hass, SIGNAL_VEHICLE_SEEN, see_vehicle)
    dispatcher_send(hass, SIGNAL_VEHICLE_SEEN, vehicle)
    return True
