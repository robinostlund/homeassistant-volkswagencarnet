# -*- coding: utf-8 -*-
import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from datetime import timedelta
from homeassistant.const import (CONF_USERNAME, CONF_PASSWORD, CONF_NAME, CONF_RESOURCES)
from homeassistant.helpers import discovery
from homeassistant.helpers.event import track_point_in_utc_time
from homeassistant.util.dt import utcnow
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.dispatcher import dispatcher_send


_LOGGER = logging.getLogger(__name__)

DOMAIN = 'volkswagencarnet'
DATA_KEY = DOMAIN

REQUIREMENTS = ['volkswagencarnet==2.0.22']
CONF_UPDATE_INTERVAL = 'update_interval'

SIGNAL_VEHICLE_SEEN = '{}.vehicle_seen'.format(DOMAIN)

MIN_UPDATE_INTERVAL = timedelta(minutes=3)
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=5)


RESOURCES = {
    'position': ('device_tracker',),
    'climatisation': ('switch', 'Climatisation', 'mdi:radiator'),
    'window_heater': ('switch', 'Window Heater', 'mdi:speedometer'),
    'charging': ('switch', 'Charging', 'mdi:battery'),
    'distance': ('sensor', 'Odometer', 'mdi:speedometer', 'km'),
    'battery_level': ('sensor', 'Battery level', 'mdi:battery', '%'),
    'fuel_level': ('sensor', 'Fuel level', 'mdi:fuel', '%'),
    'service_inspection' : ('sensor', 'Service inspection', 'mdi:garage', ''),
    'last_connected' : ('sensor', 'Last connected', 'mdi:clock', ''),
    'charging_time_left': ('sensor', 'Charging time left', 'mdi:battery-charging-100', 'min'),
    'external_power': ('binary_sensor', 'External power', 'mdi:power-plug', 'power'),
    'parking_light': ('binary_sensor', 'Parking light', 'mdi:lightbulb', 'light'),
    'climatisation_without_external_power': ('binary_sensor', 'Climatisation without external power', 'mdi:power-plug', 'power'),
    'doors_locked':  ('lock', 'Doors locked', 'mdi:lock'),
    'trunk_locked':  ('lock', 'Trunk locked', 'mdi:lock'),
    'electric_range': ('sensor', 'Electric range', 'mdi:car', 'km'),
    'combustion_range': ('sensor', 'Combustion range', 'mdi:car', 'km'),
    'combined_range': ('sensor', 'Combined Range', 'mdi:car', 'km'),
    'charge_max_ampere': ('sensor', 'Charge max ampere', 'mdi:flash', 'A'),
    'climatisation_target_temperature': ('sensor', 'Climatisation target temperature', 'mdi:thermometer', '°C')
}

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): (
            vol.All(cv.time_period, vol.Clamp(min=MIN_UPDATE_INTERVAL))),
        vol.Optional(CONF_NAME, default={}): vol.Schema(
            {cv.slug: cv.string}),
        vol.Optional(CONF_RESOURCES): vol.All(
            cv.ensure_list, [vol.In(RESOURCES)]),
    }),
}, extra = vol.ALLOW_EXTRA)

def setup(hass, config):
    """Setup Volkswagen Carnet component"""
    from volkswagencarnet import Connection

    username = config[DOMAIN].get(CONF_USERNAME)
    password = config[DOMAIN].get(CONF_PASSWORD)
    interval = config[DOMAIN].get(CONF_UPDATE_INTERVAL)
    state = hass.data[DATA_KEY] = VolkswagenData(config)

    # create carnet connection
    connection = Connection(username, password)
    # login to carnet
    _LOGGER.debug("Creating connection to carnet")
    connection._login()
    if not connection.logged_in:
        _LOGGER.warning('Could not login to carnet')

    def discover_vehicle(vehicle):
        """Load relevant platforms."""
        state.entities[vehicle.vin] = []
        for attr, (component, *_) in RESOURCES.items():
            if (getattr(vehicle, attr + '_supported', True) and
                    attr in config[DOMAIN].get(CONF_RESOURCES, [attr])):
                discovery.load_platform(
                    hass, component, DOMAIN, (vehicle.vin, attr), config)

    def update_vehicle(vehicle):
        """Review updated information on vehicle."""
        state.vehicles[vehicle.vin] = vehicle
        if vehicle.vin not in state.entities:
            discover_vehicle(vehicle)

        for entity in state.entities[vehicle.vin]:
            entity.schedule_update_ha_state()

        dispatcher_send(hass, SIGNAL_VEHICLE_SEEN, vehicle)

    def update(now):
        """Update status from Volkswagen Carnet"""
        try:
            if not connection.logged_in:
                connection._login()
                if not connection.logged_in:
                    _LOGGER.warning('Could not login to carnet')
            else:
                if not connection.update():
                    _LOGGER.warning("Could not query carnet")
                    return False
                else:
                    _LOGGER.debug("Updating data from carnet")

                for vehicle in connection.vehicles:
                    update_vehicle(vehicle)

            return True

        finally:
            track_point_in_utc_time(hass, update, utcnow() + interval)

    _LOGGER.info("Starting service")
    return update(utcnow())


class VolkswagenData:
    """Hold component state."""

    def __init__(self, config):
        """Initialize the component state."""
        self.entities = {}
        self.vehicles = {}
        self.config = config[DOMAIN]
        self.names = self.config.get(CONF_NAME)

    def vehicle_name(self, vehicle):
        """Provide a friendly name for a vehicle."""
        if (vehicle.vin and vehicle.vin.lower() in self.names):
            return self.names[vehicle.vin.lower()]
        elif vehicle.vin:
            return vehicle.vin
        else:
            return ''


class VolkswagenEntity(Entity):
    """Base class for all VOC entities."""

    def __init__(self, hass, vin, attribute):
        """Initialize the entity."""
        self._hass = hass
        self._vin = vin
        self._attribute = attribute
        self._state.entities[self._vin].append(self)

    @property
    def _state(self):
        return self._hass.data[DATA_KEY]

    @property
    def vehicle(self):
        """Return vehicle."""
        return self._state.vehicles[self._vin]

    @property
    def _entity_name(self):
        return RESOURCES[self._attribute][1]

    @property
    def _vehicle_name(self):
        return self._state.vehicle_name(self.vehicle)

    @property
    def name(self):
        """Return full name of the entity."""
        return '{} {}'.format(
            self._vehicle_name,
            self._entity_name)

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def assumed_state(self):
        """Return true if unable to access real state of entity."""
        return True

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        return dict(model='{}/{}'.format(self.vehicle.model,self.vehicle.model_year))
