"""Climate support for Volkswagen WeConnect Platform."""
import logging

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_UNKNOWN,
    TEMP_CELSIUS,
)

from . import VolkswagenEntity
from .const import DATA_KEY, DATA, DOMAIN

SUPPORT_HVAC = [HVAC_MODE_COOL, HVAC_MODE_HEAT, HVAC_MODE_OFF]
_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Perform climate platform setup."""
    if discovery_info is None:
        return
    async_add_entities([VolkswagenClimate(hass.data[DATA_KEY], *discovery_info)])


async def async_setup_entry(hass, entry, async_add_devices):
    """Perform climate device setup."""
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    coordinator = data.coordinator
    if coordinator.data is not None:
        async_add_devices(
            VolkswagenClimate(data=data, vin=coordinator.vin, component=instrument.component, attribute=instrument.attr)
            for instrument in (instrument for instrument in data.instruments if instrument.component == "climate")
        )

    return True


class VolkswagenClimate(VolkswagenEntity, ClimateEntity):
    """Representation of a Volkswagen WeConnect Climate."""

    def set_temperature(self, **kwargs) -> None:
        """Not implemented."""
        raise NotImplementedError("Use async_set_temperature instead")

    def set_humidity(self, humidity: int) -> None:
        """Not implemented."""
        raise NotImplementedError

    def set_fan_mode(self, fan_mode: str) -> None:
        """Not implemented."""
        raise NotImplementedError

    def set_hvac_mode(self, hvac_mode: str) -> None:
        """Not implemented."""
        raise NotImplementedError("Use async_set_hvac_mode instead")

    def set_swing_mode(self, swing_mode: str) -> None:
        """Not implemented."""
        raise NotImplementedError

    def set_preset_mode(self, preset_mode: str) -> None:
        """Not implemented."""
        raise NotImplementedError

    def turn_aux_heat_on(self) -> None:
        """Not implemented."""
        raise NotImplementedError

    def turn_aux_heat_off(self) -> None:
        """Not implemented."""
        raise NotImplementedError

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_TARGET_TEMPERATURE

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.

        Need to be one of HVAC_MODE_*.
        """
        if not self.instrument.hvac_mode:
            return HVAC_MODE_OFF

        hvac_modes = {
            "HEATING": HVAC_MODE_HEAT,
            "COOLING": HVAC_MODE_COOL,
        }
        return hvac_modes.get(self.instrument.hvac_mode, HVAC_MODE_OFF)

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
            self.notify_updated()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        _LOGGER.debug("Setting mode for: %s", self.instrument.attr)
        if hvac_mode == HVAC_MODE_OFF:
            await self.instrument.set_hvac_mode(False)
        elif hvac_mode == HVAC_MODE_HEAT:
            await self.instrument.set_hvac_mode(True)
        self.notify_updated()
