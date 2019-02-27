"""
Support for Volkswagen Carnet Platform
"""
import logging
from custom_components.volkswagen_carnet import VolkswagenEntity, RESOURCES
from homeassistant.helpers.icon import icon_for_battery_level


_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Volvo sensors."""
    if discovery_info is None:
        return
    add_devices([VolkswagenSensor(hass, *discovery_info)])


class VolkswagenSensor(VolkswagenEntity):
    """Representation of a Volkswagen Carnet Sensor."""
    @property
    def state(self):
        """Return the state of the sensor."""
        _LOGGER.debug('Getting state of %s sensor' % self._attribute)

        val = getattr(self.vehicle, self._attribute)
        if val is None:
            return val
        if self._attribute in ['last_connected', 'service_inspection']:
            return str(val)
        else:
            return int(float(val))

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return RESOURCES[self._attribute][3]

    @property
    def icon(self):
        """Return the icon."""
        if self._attribute == 'battery_level':
            val = getattr(self.vehicle, self._attribute)
            return icon_for_battery_level(battery_level = int(val), charging = self.vehicle.is_charging_on)
        else:
            return RESOURCES[self._attribute][2]

    @property
    def available(self):
        """Return True if entity is available."""
        if self._attribute == 'charging_time_left':
            if self.vehicle.is_charging_on:
                return True
            else:
                return False
        else:
            return True

