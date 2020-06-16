"""
Support for Volkswagen Carnet.
"""
import logging
from . import VolkswagenEntity, DATA_KEY
from homeassistant.components.binary_sensor import BinarySensorEntity, DEVICE_CLASSES

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Volkswagen binary sensors."""
    if discovery_info is None:
        return
    async_add_entities([VolkswagenBinarySensor(hass.data[DATA_KEY], *discovery_info)])

class VolkswagenBinarySensor(VolkswagenEntity, BinarySensorEntity):
    """Representation of a Volkswagen Binary Sensor """

    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        _LOGGER.debug('Getting state of %s' % self.instrument.attr)
        return self.instrument.is_on

    @property
    def device_class(self):
        """Return the class of this sensor, from DEVICE_CLASSES."""
        if self.instrument.device_class in DEVICE_CLASSES:
            return self.instrument.device_class
        return None