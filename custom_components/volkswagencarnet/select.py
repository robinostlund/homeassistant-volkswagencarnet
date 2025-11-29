"""Select support for Volkswagen Connect integration."""

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

    # Entity attributes (Home Assistant 2024+)
    _attr_has_entity_name = True

    def __init__(self, *args, **kwargs):
        """Initialize the select entity."""
        super().__init__(*args, **kwargs)
        # Set attributes based on instrument
        self._attr_options = self._get_options()
        self._attr_entity_category = self._get_entity_category()

    def _get_options(self) -> list[str] | None:
        """Get options from instrument."""
        options = self.instrument.options
        if options:
            return list(options)
        return None

    def _get_entity_category(self) -> EntityCategory | None:
        """Get entity category from instrument."""
        entity_type = self.instrument.entity_type

        if entity_type == "diag":
            return EntityCategory.DIAGNOSTIC
        if entity_type == "config":
            return EntityCategory.CONFIG

        return None

    @property
    def current_option(self) -> str | None:
        """Return the current option."""
        current = self.instrument.current_option
        if current:
            return str(current)
        return None

    async def async_select_option(self, option: str) -> None:
        """Update the current value."""
        try:
            await self.instrument.set_value(option)
            self.notify_updated()
        except Exception as err:
            _LOGGER.error(
                "Failed to set option for %s to %s: %s",
                self.instrument.attr,
                option,
                err,
            )
            raise
