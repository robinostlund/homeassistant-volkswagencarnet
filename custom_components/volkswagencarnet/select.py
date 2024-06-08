"""Number support for Volkswagen Connect integration."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import VolkswagenEntity
from .const import DATA, DATA_KEY, DOMAIN, UPDATE_CALLBACK

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant, config, async_add_entities, discovery_info=None
):
    """Set up the Volkswagen select platform."""
    if discovery_info is None:
        return
    async_add_entities([VolkswagenSelect(hass.data[DATA_KEY], *discovery_info)])


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Set up the Volkswagen select."""
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    coordinator = data.coordinator
    if coordinator.data is not None:
        async_add_devices(
            VolkswagenSelect(
                data=data,
                vin=coordinator.vin,
                component=instrument.component,
                attribute=instrument.attr,
                callback=hass.data[DOMAIN][entry.entry_id][UPDATE_CALLBACK],
            )
            for instrument in (
                instrument
                for instrument in data.instruments
                if instrument.component == "select"
            )
        )

    return True


class VolkswagenSelect(VolkswagenEntity, SelectEntity):
    """Representation of a Volkswagen select."""

    @property
    def options(self) -> list:
        """Return the options list."""
        if self.instrument.options:
            return self.instrument.options
        return None

    @property
    def current_option(self) -> str:
        """Return the current option."""
        if self.instrument.current_option:
            return self.instrument.current_option
        return None

    @property
    def entity_category(self) -> EntityCategory | str | None:
        """Return entity category."""
        if self.instrument.entity_type == "diag":
            return EntityCategory.DIAGNOSTIC
        if self.instrument.entity_type == "config":
            return EntityCategory.CONFIG

    async def async_select_option(self, option: str) -> None:
        """Update the current value."""
        await self.instrument.set_value(option)
        self.notify_updated()
