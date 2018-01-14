"""
Support for Volkswagen Carnet.
"""
import logging

from homeassistant.helpers.entity import ToggleEntity

_LOGGER = logging.getLogger(__name__)

CARNET_DATA = "volkswagen_carnet"
DEPENDENCIES = ['volkswagen_carnet']

SWITCHES = [
    {
        'name': 'climat',
        'friendly_name': 'Climat',
        'icon': 'mdi:car'
    },
    {
        'name': 'charge',
        'friendly_name': 'Charge',
        'icon': 'mdi:car'
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
            print(switch)
            functions.append(VolkswagenCarnetSwitch(hass, vehicle, switch))

    _LOGGER.debug("Adding switches %s", functions)

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

    def update(self):
        """Update the states of Volkswagen Carnet switches."""
        _LOGGER.debug("Running switch update")
        self.vw._carnet_update_status()

    @property
    def name(self):
        """Return the name of the switch."""
        return 'vw_%s_%s' % (self.vehicle, self.switch_name)

    @property
    def available(self):
        """Return True if entity is available."""
        return True

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self.vw._get_state(self.vehicle, self.switch_name)


    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self.vw._set_state(self.vehicle, self.switch_name, True)


    def turn_off(self, **kwargs):
        """Turn the switch off."""
        self.vw._set_state(self.vehicle, self.switch_name, False)

    @property
    def icon(self):
        """Return the icon."""
        return self.switch_icon
