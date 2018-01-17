"""
Support for Volkswagen Carnet.
"""
from homeassistant.components.binary_sensor import BinarySensorDevice
from custom_components.volkswagen_carnet import CARNET_DATA, VolkswagenCarnetEntity

import logging
from datetime import timedelta

BINARY_SENSORS = [

    {
        'name': 'external_power_connected',
        'friendly_name': 'External power connected',
        'icon': 'mdi:power-plug',
        'class': 'power',
        'attr': {
            'unit_of_measurement': '',
            'hidden': False
        }
    },
    {
        'name': 'door_locked',
        'friendly_name': 'Door Locked',
        'icon': 'mdi:lock',
        'class': 'door',
        'attr': {
            'unit_of_measurement': '',
            'hidden': False
        }
    },
    {
        'name': 'parking_lights',
        'friendly_name': 'Parking Lights',
        'icon': 'mdi:lightbulb',
        'class': 'light',
        'attr': {
            'unit_of_measurement': '',
            'hidden': False,
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
        for binary_sensor in BINARY_SENSORS:
            functions.append(VolkswagenCarnetSensor(hass, vehicle, binary_sensor))
    add_devices(functions)

class VolkswagenCarnetSensor(VolkswagenCarnetEntity, BinarySensorDevice):
    """Representation of a Volkswagen Carnet Binary sensor."""

    @property
    def is_on(self):
        if self._sensor_name == 'external_power_connected':
            return self._get_vehicle_data['sensor_external_power_connected']
        elif self._sensor_name == 'door_locked':
            # class door sees true as open
            if self._get_vehicle_data['sensor_door_locked']:
                return False
            else:
                return True
        elif self._sensor_name == 'parking_lights':
            return self._get_vehicle_data['sensor_parking_lights']
        else:
            return None

    @property
    def device_class(self):
        """Return the class of this sensor, from DEVICE_CLASSES."""
        return self.sensor.get('class')
