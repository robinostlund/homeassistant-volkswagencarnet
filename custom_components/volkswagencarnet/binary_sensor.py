"""BinarySensor support for Volkswagen We Connect integration."""

import logging

from homeassistant.components.binary_sensor import (
    DEVICE_CLASSES,
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import VolkswagenEntity
from .const import DATA_KEY, DATA, DOMAIN, UPDATE_CALLBACK

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass: HomeAssistant, config: ConfigEntry, async_add_entities, discovery_info=None):
    """Set up the Volkswagen binary sensors platform."""
    if discovery_info is None:
        return
    async_add_entities([VolkswagenBinarySensor(hass.data[DATA_KEY], *discovery_info)])


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the Volkswagen binary sensor."""
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    coordinator = data.coordinator
    if coordinator.data is not None:
        async_add_devices(
            VolkswagenBinarySensor(
                data=data,
                vin=coordinator.vin,
                component=instrument.component,
                attribute=instrument.attr,
                callback=hass.data[DOMAIN][entry.entry_id][UPDATE_CALLBACK],
            )
            for instrument in (instrument for instrument in data.instruments if instrument.component == "binary_sensor")
        )

    return True


class VolkswagenBinarySensor(VolkswagenEntity, BinarySensorEntity):
    """Representation of a Volkswagen Binary Sensor."""

    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        _LOGGER.debug("Getting state of %s" % self.instrument.attr)
        return self.instrument.is_on

    @property
    def device_class(self) -> BinarySensorDeviceClass | str | None:
        """Return the device class."""
        if self.instrument.device_class in DEVICE_CLASSES:
            return self.instrument.device_class
        _LOGGER.warning(f"Unknown device class {self.instrument.device_class}")
        return None

    @property
    def entity_category(self) -> EntityCategory | str | None:
        """Return entity category."""
        if self.instrument.entity_type == "diag":
            return EntityCategory.DIAGNOSTIC
        if self.instrument.entity_type == "config":
            return EntityCategory.CONFIG
