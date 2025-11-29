"""Support for Volkswagen Connect Platform."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import VolkswagenData, VolkswagenEntity
from .const import DATA, DATA_KEY, DOMAIN, UPDATE_CALLBACK

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant, config, async_add_entities, discovery_info=None
):
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
            for instrument in (
                instrument
                for instrument in data.instruments
                if instrument.component == "switch"
            )
        )
    return True


class VolkswagenSwitch(VolkswagenEntity, SwitchEntity):
    """Representation of a Volkswagen Connect Switch."""

    # Entity attributes (Home Assistant 2024+)
    _attr_has_entity_name = True

    def __init__(
        self,
        data: VolkswagenData,
        vin: str,
        component: str,
        attribute: str,
        callback=None,
    ) -> None:
        """Initialize switch."""
        super().__init__(data, vin, component, attribute, callback)
        # Set attributes based on instrument
        self._attr_entity_category = self._get_entity_category()
        self._attr_assumed_state = self.instrument.assumed_state

    def _get_entity_category(self) -> EntityCategory | None:
        """Get entity category from instrument."""
        entity_type = self.instrument.entity_type

        if entity_type == "diag":
            return EntityCategory.DIAGNOSTIC
        if entity_type == "config":
            return EntityCategory.CONFIG

        return None

    @property
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        _LOGGER.debug("Getting state of %s", self.instrument.attr)
        return self.instrument.state

    async def async_turn_on(self, **kwargs: object) -> None:
        """Turn the switch on."""
        try:
            _LOGGER.debug("Turning ON %s", self.instrument.attr)
            await self.instrument.turn_on()
            self.notify_updated()
        except Exception as err:
            _LOGGER.error("Failed to turn on %s: %s", self.instrument.attr, err)
            raise

    async def async_turn_off(self, **kwargs: object) -> None:
        """Turn the switch off."""
        try:
            _LOGGER.debug("Turning OFF %s", self.instrument.attr)
            await self.instrument.turn_off()
            self.notify_updated()
        except Exception as err:
            _LOGGER.error("Failed to turn off %s: %s", self.instrument.attr, err)
            raise

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return extra state attributes."""
        return {
            **super().extra_state_attributes,
            **(self.instrument.attributes if self.instrument is not None else {}),
        }
