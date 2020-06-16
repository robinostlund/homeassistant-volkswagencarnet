"""
Support for Volkswagen Carnet Platform
"""
import logging
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (HVAC_MODE_HEAT, HVAC_MODE_OFF, SUPPORT_TARGET_TEMPERATURE)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT, STATE_UNKNOWN

SUPPORT_HVAC = [HVAC_MODE_HEAT, HVAC_MODE_OFF]

from . import VolkswagenEntity, DATA_KEY

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """ Setup the volkswagen climate."""
    if discovery_info is None:
        return
    async_add_entities([VolkswagenClimate(hass.data[DATA_KEY], *discovery_info)])

class VolkswagenClimate(VolkswagenEntity, ClimateEntity):
    """Representation of a Volkswagen Carnet Climate."""

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_TARGET_TEMPERATURE

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.
        Need to be one of HVAC_MODE_*.
        """
        if self.instrument.hvac_mode:
            return HVAC_MODE_HEAT
        return HVAC_MODE_OFF

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.
        Need to be a subset of HVAC_MODES.
        """
        return SUPPORT_HVAC

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        if self.instrument.target_temperature:
            return float(self.instrument.target_temperature)
        else:
            return STATE_UNKNOWN

    async def async_set_temperature(self, **kwargs):
        """Set new target temperatures."""
        _LOGGER.debug("Setting temperature for: %s", self.instrument.attr)
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature:
            await self.instrument.set_temperature(temperature)

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        _LOGGER.debug("Setting mode for: %s", self.instrument.attr)
        if hvac_mode == HVAC_MODE_OFF:
            await self.instrument.set_hvac_mode(False)
        elif hvac_mode == HVAC_MODE_HEAT:
            await self.instrument.set_hvac_mode(True)
