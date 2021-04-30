"""
Support for Volkswagen WeConnect Platform
"""
import logging
from typing import Any, Dict, Optional

from homeassistant.helpers.entity import ToggleEntity

from . import DATA, DATA_KEY, DOMAIN, VolkswagenEntity, UPDATE_CALLBACK

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """ Setup the volkswagen switch."""
    if discovery_info is None:
        return
    async_add_entities([VolkswagenSwitch(hass.data[DATA_KEY], *discovery_info)])


async def async_setup_entry(hass, entry, async_add_devices):
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    coordinator = data.coordinator
    if coordinator.data is not None:
        async_add_devices(
            VolkswagenSwitch(
                data, coordinator.vin, instrument.component, instrument.attr, hass.data[DOMAIN][entry.entry_id][UPDATE_CALLBACK]
            )
            for instrument in (
                instrument
                for instrument in data.instruments
                if instrument.component == "switch"
            )
        )

    return True


class VolkswagenSwitch(VolkswagenEntity, ToggleEntity):
    """Representation of a Volkswagen WeConnect Switch."""

    @property
    def is_on(self):
        """Return true if switch is on."""
        _LOGGER.debug("Getting state of %s" % self.instrument.attr)
        return self.instrument.state

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.debug("Turning ON %s." % self.instrument.attr)
        await self.instrument.turn_on()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.debug("Turning OFF %s." % self.instrument.attr)
        await self.instrument.turn_off()
        self.async_write_ha_state()

    @property
    def assumed_state(self):
        return self.instrument.assumed_state

    @property
    def state_attributes(self) -> Optional[Dict[str, Any]]:
        return self.instrument.attributes
