"""Number support for Volkswagen We Connect integration."""

import logging
from typing import Union

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import VolkswagenEntity, VolkswagenData
from .const import DATA_KEY, DATA, DOMAIN, UPDATE_CALLBACK

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass: HomeAssistant, config: ConfigEntry, async_add_entities, discovery_info=None):
    """Set up the Volkswagen number platform."""
    if discovery_info is None:
        return
    async_add_entities([VolkswagenNumber(hass.data[DATA_KEY], *discovery_info)])


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the Volkswagen number."""
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    coordinator = data.coordinator
    if coordinator.data is not None:
        async_add_devices(
            VolkswagenNumber(
                data=data,
                vin=coordinator.vin,
                component=instrument.component,
                attribute=instrument.attr,
                callback=hass.data[DOMAIN][entry.entry_id][UPDATE_CALLBACK],
            )
            for instrument in (instrument for instrument in data.instruments if instrument.component == "number")
        )

    return True


class VolkswagenNumber(VolkswagenEntity, NumberEntity):
    """Representation of a Volkswagen number."""

    def __init__(self, data: VolkswagenData, vin: str, component: str, attribute: str, callback=None):
        """Initialize switch."""
        super().__init__(data, vin, component, attribute, callback)

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        if self.instrument.min_value:
            return self.instrument.min_value
        return None

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        if self.instrument.max_value:
            return self.instrument.max_value
        return None

    @property
    def native_step(self) -> float:
        if self.instrument.native_step:
            return self.instrument.native_step
        return None

    @property
    def native_unit_of_measurement(self) -> str:
        if self.instrument.unit:
            return self.instrument.unit
        return ""

    @property
    def entity_category(self) -> Union[EntityCategory, str, None]:
        """Return entity category."""
        if self.instrument.entity_type == "diag":
            return EntityCategory.DIAGNOSTIC
        if self.instrument.entity_type == "config":
            return EntityCategory.CONFIG

    @property
    def native_value(self) -> float:
        """Return the entity value to represent the entity state."""
        return self.instrument.state

    async def async_set_native_value(self, value: int) -> None:
        """Update the current value."""
        _LOGGER.debug("Update current value to %s." % value)
        await self.instrument.set_value(value)
        # self.notify_updated()
