"""
Support for Volkswagen Carnet.
"""
from homeassistant.helpers.entity import Entity
from custom_components.volkswagen_carnet import CARNET_DATA
from datetime import datetime

import logging
from datetime import timedelta
from math import floor

SENSORS = [
    {
        'name': 'battery',
        'friendly_name': 'Battery left',
        'icon': 'mdi:battery',
        'unit_of_measurement': '%'
    },
    {
        'name': 'charge_max_ampere',
        'friendly_name': 'Charge max ampere',
        'icon': 'mdi:flash',
        'unit_of_measurement': 'A'
    },
    {
        'name': 'external_power_connected',
        'friendly_name': 'External power connected',
        'icon': 'mdi:power-plug',
        'unit_of_measurement': ''
    },
    {
        'name': 'charging_time_left',
        'friendly_name': 'Charging time left',
        'icon': 'mdi:battery-charging-100',
        'unit_of_measurement': 'seconds'
    },
    {
        'name': 'climat_target_temperature',
        'friendly_name': 'Climatisation target temperature',
        'icon': 'mdi:thermometer',
        'unit_of_measurement': '°C'
    },
    {
        'name': 'electric_range_left',
        'friendly_name': 'Electric range left',
        'icon': 'mdi:car',
        'unit_of_measurement': 'km'
    },
    {
        'name': 'distance',
        'friendly_name': 'Distance',
        'icon': 'mdi:speedometer',
        'unit_of_measurement': 'km'
    },
    {
        'name': 'last_update',
        'friendly_name': 'Updated',
        'icon': 'mdi:clock',
        'unit_of_measurement': ''
    }
]

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the sensor platform."""

    if discovery_info is None:
        return

    vehicles = hass.data[CARNET_DATA].vehicles

    functions = []
    for vehicle in vehicles:
        for sensor in SENSORS:
            functions.append(VolkswagenCarnet(hass, vehicle, sensor))
    add_devices(functions)


class VolkswagenCarnet(Entity):
    """Representation of a Sensor."""

    def __init__(self, hass, vehicle, sensor):
        """Initialize the sensor."""
        self.vw = hass.data[CARNET_DATA]
        self.hass = hass
        self._state = None
        self.sensor = sensor
        self.sensor_name = self.sensor.get('name')
        self.sensor_icon = self.sensor.get('icon')
        self.sensor_unit_of_measurement = self.sensor.get('unit_of_measurement')
        self.vehicle = vehicle

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'vw_%s_%s' % (self.vehicle, self.sensor_name)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self.sensor_unit_of_measurement

    def update(self):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = self.vw._sensor_get_state(self.vehicle, self.sensor_name)

    @property
    def icon(self):
        """Return the icon."""
        return self.sensor_icon

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {}
        if self._last_updated:
            attrs['time_last_updated'] = self._last_updated
        return attrs

    @property
    def _last_updated(self):
        """Return the last update of a device."""
        datetime_object = self.vw.vehicles[self.vehicle].get('last_connected')
        if datetime_object:
            return datetime_object.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return None
