"""
Support for Volkswagen Carnet Platform
"""
import logging
from homeassistant.helpers.entity import ToggleEntity
from custom_components.volkswagencarnet import VolkswagenEntity, RESOURCES

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up Tellstick switches."""
    if discovery_info is None:
        return
    add_devices([VolkswagenCarnetSwitch(hass, *discovery_info)])


class VolkswagenCarnetSwitch(VolkswagenEntity, ToggleEntity):
    """Representation of a Volvo switch."""

    @property
    def is_on(self):
        """Return true if switch is on."""
        _LOGGER.debug('Getting status of %s' % self._attribute)
        if self._attribute == 'climatisation':
            return self.vehicle.is_climatisation_on
        elif self._attribute == 'window_heater':
            return self.vehicle.is_window_heater_on
        elif self._attribute == 'charging':
            return self.vehicle.is_charging_on

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.debug("Turning on %s." % self._attribute)
        if self._attribute == 'climatisation':
            self.vehicle.start_climatisation()
        elif self._attribute == 'window_heater':
            self.vehicle.start_window_heater()
        elif self._attribute == 'charging':
            self.vehicle.start_charging()

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.debug("Turning off %s." % self._attribute)
        if self._attribute == 'climatisation':
            self.vehicle.stop_climatisation()
        elif self._attribute == 'window_heater':
            self.vehicle.stop_window_heater()
        elif self._attribute == 'charging':
            self.vehicle.stop_charging()

    @property
    def icon(self):
        """Return the icon."""
        return RESOURCES[self._attribute][2]
