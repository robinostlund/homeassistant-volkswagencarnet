"""
Support for Volkswagen Carnet.
"""
from homeassistant.const import (STATE_OFF, STATE_ON)
from homeassistant.helpers.entity import ToggleEntity
from custom_components.volkswagen_carnet import CARNET_DATA


SWITCHES = [
    {
        'name': 'climat',
        'friendly_name': 'Climat',
        'icon': 'mdi:radiator'
    },
    {
        'name': 'charge',
        'friendly_name': 'Charge',
        'icon': 'mdi:battery-charging'
    },
    {
        'name': 'melt',
        'friendly_name': 'Window melt',
        'icon': 'mdi:car-wash'
    }
]


def setup_platform(hass, config, add_devices, discovery_info = None):
    """Set up the Volkswagen Carnet switches."""
    if discovery_info is None:
        return

    vehicles = hass.data[CARNET_DATA].vehicles

    functions = []
    for vehicle in vehicles:
        for switch in SWITCHES:
            functions.append(VolkswagenCarnetSwitch(hass, vehicle, switch))

    add_devices(functions)

class VolkswagenCarnetSwitch(ToggleEntity):
    """Volkswagen Carnet Switch."""

    def __init__(self, hass, vehicle, switch):
        self.vw = hass.data[CARNET_DATA]
        self.hass = hass
        self.vehicle = vehicle
        self.switch = switch
        self.switch_name = self.switch.get('name')
        self.switch_friendly_name = self.switch.get('friendly_name')
        self.switch_icon = self.switch.get('icon')
        self._state = STATE_OFF

    @property
    def should_poll(self):
        """Poll for status regularly."""
        return True

    @property
    def name(self):
        """Return the name of the switch."""
        return 'vw_%s_%s' % (self.vehicle, self.switch_name)

    @property
    def available(self):
        """Return True if entity is available."""
        return self._state

    @property
    def icon(self):
        """Return the icon."""
        return self.switch_icon

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state == STATE_ON

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self.vw._switch_update_state(self.vehicle, self.switch_name, True)


    def turn_off(self, **kwargs):
        """Turn the switch off."""
        self.vw._switch_update_state(self.vehicle, self.switch_name, False)

    def update(self):
        """Update the states of Volkswagen Carnet switches."""
        self._state = STATE_ON if self.vw._switch_get_state(self.vehicle, self.switch_name) else STATE_OFF