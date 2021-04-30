"""
Support for Volkswagen WeConnect.
"""
import logging

from homeassistant.components.binary_sensor import DEVICE_CLASSES, BinarySensorEntity

from . import UPDATE_CALLBACK, DATA, DATA_KEY, DOMAIN, VolkswagenEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Volkswagen binary sensors."""
    if discovery_info is None:
        return
    async_add_entities([VolkswagenBinarySensor(hass.data[DATA_KEY], *discovery_info)])


async def async_setup_entry(hass, entry, async_add_devices):
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    coordinator = data.coordinator
    if coordinator.data is not None:
        async_add_devices(
            VolkswagenBinarySensor(
                data, coordinator.vin, instrument.component, instrument.attr, hass.data[DOMAIN][entry.entry_id][UPDATE_CALLBACK]
            )
            for instrument in (
                instrument
                for instrument in data.instruments
                if instrument.component == "binary_sensor"
            )
        )

    return True


class VolkswagenBinarySensor(VolkswagenEntity, BinarySensorEntity):
    """Representation of a Volkswagen Binary Sensor """

    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        _LOGGER.debug("Getting state of %s" % self.instrument.attr)
        return self.instrument.is_on

    @property
    def device_class(self):
        """Return the class of this sensor, from DEVICE_CLASSES."""
        if self.instrument.device_class in DEVICE_CLASSES:
            return self.instrument.device_class
        return None
