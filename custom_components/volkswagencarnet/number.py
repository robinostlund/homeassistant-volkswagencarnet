"""Number support for Volkswagen Connect integration."""

import logging

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import VolkswagenEntity
from .const import DATA, DATA_KEY, DOMAIN, UPDATE_CALLBACK

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant, config, async_add_entities, discovery_info=None
):
    """Set up the Volkswagen number platform."""
    if discovery_info is None:
        return
    async_add_entities([VolkswagenNumber(hass.data[DATA_KEY], *discovery_info)])


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
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
            for instrument in (
                instrument
                for instrument in data.instruments
                if instrument.component == "number"
            )
        )

    return True


class VolkswagenNumber(VolkswagenEntity, NumberEntity):
    """Representation of a Volkswagen number."""

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
        """Return the increment/decrement step."""
        return self.instrument.native_step

    @property
    def native_unit_of_measurement(self) -> str:
        """Return unit of measurement."""
        if self.instrument.unit:
            return self.instrument.unit
        return ""

    @property
    def native_value(self) -> float:
        """Return the entity value to represent the entity state."""
        if self.instrument.state:
            return self.instrument.state
        return None

    @property
    def device_class(self) -> NumberDeviceClass | None:
        """Return the device class."""
        if (
            self.instrument.device_class is None
            or self.instrument.device_class in NumberDeviceClass
        ):
            return self.instrument.device_class
        _LOGGER.warning("Unknown device class %s", self.instrument.device_class)
        return None

    @property
    def entity_category(self) -> EntityCategory | str | None:
        """Return entity category."""
        if self.instrument.entity_type == "diag":
            return EntityCategory.DIAGNOSTIC
        if self.instrument.entity_type == "config":
            return EntityCategory.CONFIG

    async def async_set_native_value(self, value: int) -> None:
        """Update the current value."""
        await self.instrument.set_value(value)
        self.notify_updated()
