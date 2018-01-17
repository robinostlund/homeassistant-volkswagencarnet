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
        'unit_of_measurement': '',
        'hidden': False,
        'class': 'plug'
    },
    {
        'name': 'door_locked',
        'friendly_name': 'Door Locked',
        'icon': 'mdi:lock',
        'unit_of_measurement': '',
        'hidden': False,
        'class': 'door'
    },
    {
        'name': 'parking_lights',
        'friendly_name': 'Parking Lights',
        'icon': 'mdi:lightbulb',
        'unit_of_measurement': '',
        'hidden': False,
        'class': 'light'
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
            functions.append(VolkswagenCarnetBinarySensor(hass, vehicle, binary_sensor))
    add_devices(functions)

class VolkswagenCarnetBinarySensor(VolkswagenCarnetEntity, BinarySensorDevice):
    """Representation of a Volkswagen Carnet Binary sensor."""

    @property
    def is_on(self):
        return self.vw._sensor_get_state(self.vehicle, self.sensor_name)


    @property
    def device_class(self):
        """Return the class of this sensor, from DEVICE_CLASSES."""
        return self.sensor.get('class')
