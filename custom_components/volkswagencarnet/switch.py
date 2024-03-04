"""Support for Volkswagen WeConnect Platform."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import ToggleEntity, EntityCategory

from . import VolkswagenEntity, VolkswagenData
from .const import DATA, DATA_KEY, DOMAIN, UPDATE_CALLBACK

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    """Set up the volkswagen switch platform."""
    if discovery_info is None:
        return
    async_add_entities([VolkswagenSwitch(hass.data[DATA_KEY], *discovery_info)])


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Add configured devices for this entity."""
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    coordinator = data.coordinator
    if coordinator.data is not None:
        async_add_devices(
            VolkswagenSwitch(
                data=data,
                vin=coordinator.vin,
                component=instrument.component,
                attribute=instrument.attr,
                callback=hass.data[DOMAIN][entry.entry_id][UPDATE_CALLBACK],
            )
            for instrument in (instrument for instrument in data.instruments if instrument.component == "switch")
        )
    return True


class VolkswagenSwitch(VolkswagenEntity, ToggleEntity):
    """Representation of a Volkswagen WeConnect Switch."""

    def __init__(
        self,
        data: VolkswagenData,
        vin: str,
        component: str,
        attribute: str,
        callback=None,
    ):
        """Initialize switch."""
        super().__init__(data, vin, component, attribute, callback)

    def turn_on(self, **kwargs: object) -> None:
        """Don't support sync methods."""
        raise NotImplementedError

    def turn_off(self, **kwargs: object) -> None:
        """Don't support sync methods."""
        raise NotImplementedError

    @property
    def is_on(self):
        """Return true if switch is on."""
        _LOGGER.debug("Getting state of %s" % self.instrument.attr)
        return self.instrument.state

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.debug("Turning ON %s." % self.instrument.attr)
        await self.instrument.turn_on()
        self.notify_updated()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.debug("Turning OFF %s." % self.instrument.attr)
        await self.instrument.turn_off()
        self.notify_updated()

    @property
    def entity_category(self) -> EntityCategory | str | None:
        """Return entity category."""
        if self.instrument.entity_type == "diag":
            return EntityCategory.DIAGNOSTIC
        if self.instrument.entity_type == "config":
            return EntityCategory.CONFIG

    @property
    def assumed_state(self):
        """Return state assumption."""
        return self.instrument.assumed_state

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return extra state attributes."""
        return {
            **super().extra_state_attributes,
            **(self.instrument.attributes if self.instrument is not None else {}),
        }
