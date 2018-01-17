"""
Support for Volkswagen Carnet.
"""
from custom_components.volkswagen_carnet import CARNET_DATA, VolkswagenCarnetEntity

import logging
from datetime import timedelta

SENSORS = [
    {
        'name': 'battery',
        'friendly_name': 'Battery left',
        'icon': 'mdi:battery',
        'attr': {
            'unit_of_measurement': '%',
            'hidden': False
        }
    },
    {
        'name': 'charge_max_ampere',
        'friendly_name': 'Charge max ampere',
        'icon': 'mdi:flash',
        'attr': {
            'unit_of_measurement': 'A',
            'hidden': False
        }
    },
    {
        'name': 'charging_time_left',
        'friendly_name': 'Charging time left',
        'icon': 'mdi:battery-charging-100',
        'attr': {
            'unit_of_measurement': 'min',
            'hidden': False
        }
    },
    {
        'name': 'climat_target_temperature',
        'friendly_name': 'Climatisation target temperature',
        'icon': 'mdi:thermometer',
        'attr': {
            'unit_of_measurement': '°C',
            'hidden': False
        }
    },
    {
        'name': 'electric_range_left',
        'friendly_name': 'Electric range left',
        'icon': 'mdi:car',
        'attr': {
            'unit_of_measurement': 'km',
            'hidden': False,
        }
    },
    {
        'name': 'distance',
        'friendly_name': 'Distance',
        'icon': 'mdi:speedometer',
        'attr': {
            'unit_of_measurement': 'km',
            'hidden': False
        }
    },
    {
        'name': 'last_connected',
        'friendly_name': 'Last connected',
        'icon': 'mdi:clock',
        'attr': {
            'unit_of_measurement': '',
            'hidden': False
        }
    },
    {
        'name': 'next_service_inspection',
        'friendly_name': 'Next service inspection',
        'icon': 'mdi:garage',
        'attr': {
            'unit_of_measurement': '',
            'hidden': False
        }
    }
]

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the sensor platform."""

    if discovery_info is None:
        return

    vehicles = hass.data[CARNET_DATA].vehicles

    functions = []
    for vehicle in vehicles:
        for sensor in SENSORS:
            functions.append(VolkswagenCarnetSensor(hass, vehicle, sensor))
    add_devices(functions)


class VolkswagenCarnetSensor(VolkswagenCarnetEntity):
    """Representation of a Volkswagen Carnet Sensor."""

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def available(self):
        """Return True if entity is available."""
        if self._state:
            return True
        else:
            return False

    def update(self):
        """Fetch new state data for the sensor."""
        _LOGGER.debug("Updating %s sensor for vehicle: %s", self._sensor_name, self.vehicle)
        return self._state


