"""
Support for Volkswagen Carnet.
"""
import logging
from custom_components.volkswagen_carnet import VolkswagenEntity, RESOURCES
from homeassistant.components.binary_sensor import BinarySensorDevice

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Volvo sensors."""
    if discovery_info is None:
        return
    add_devices([VolkswagenSensor(hass, *discovery_info)])

class VolkswagenSensor(VolkswagenEntity, BinarySensorDevice):
    """Representation of a Volvo sensor."""

    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        _LOGGER.debug('Getting state of %s binary sensor' % self._attribute)
        val = getattr(self.vehicle, self._attribute)
        if self._attribute == 'door_locked':
            if val:
                return 'open'
            else:
                return 'closed'
        else:
            return val

    @property
    def device_class(self):
        """Return the class of this sensor, from DEVICE_CLASSES."""
        return RESOURCES[self._attribute][3]

    @property
    def icon(self):
        """Return the icon."""
        return RESOURCES[self._attribute][2]