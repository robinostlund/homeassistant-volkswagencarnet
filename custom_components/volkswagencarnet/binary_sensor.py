"""BinarySensor support for Volkswagen Connect integration."""

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import VolkswagenEntity
from .const import DATA, DATA_KEY, DOMAIN, UPDATE_CALLBACK

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities,
    discovery_info=None,
):
    """Set up the Volkswagen binary sensors platform."""
    if discovery_info is None:
        return
    async_add_entities([VolkswagenBinarySensor(hass.data[DATA_KEY], *discovery_info)])


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
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
            for instrument in (
                instrument
                for instrument in data.instruments
                if instrument.component == "binary_sensor"
            )
        )

    return True


class VolkswagenBinarySensor(VolkswagenEntity, BinarySensorEntity):
    """Representation of a Volkswagen Binary Sensor."""

    # Entity attributes (Home Assistant 2024+)
    _attr_has_entity_name = True

    def __init__(self, *args, **kwargs):
        """Initialize the binary sensor."""
        super().__init__(*args, **kwargs)
        # Set attributes based on instrument
        self._attr_device_class = self._get_device_class()
        self._attr_entity_category = self._get_entity_category()

    def _get_device_class(self) -> BinarySensorDeviceClass | None:
        """Get device class from instrument."""
        try:
            device_class_str = self.instrument.device_class
            if device_class_str is None:
                return None
            return BinarySensorDeviceClass(device_class_str)
        except ValueError:
            _LOGGER.warning(
                "Unknown device class '%s' for %s",
                self.instrument.device_class,
                self.instrument.attr,
            )
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
    def is_on(self) -> bool:
        """Return True if the binary sensor is on."""
        _LOGGER.debug("Getting state of %s", self.instrument.attr)
        return self.instrument.is_on
