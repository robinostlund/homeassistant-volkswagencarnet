"""Sensor support for Volkswagen Connect platform."""

import logging

from homeassistant.components.sensor import (
    DEVICE_CLASSES,
    STATE_CLASSES,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from . import VolkswagenEntity
from .const import DATA, DATA_KEY, DOMAIN, UPDATE_CALLBACK

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities, discovery_info=None
):
    """Set up the Volkswagen sensors."""
    if discovery_info is None:
        return
    async_add_entities([VolkswagenSensor(hass.data[DATA_KEY], *discovery_info)])


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Set up the entity."""
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    coordinator = data.coordinator
    if coordinator.data is not None:
        async_add_devices(
            VolkswagenSensor(
                data=data,
                vin=coordinator.vin,
                component=instrument.component,
                attribute=instrument.attr,
                callback=hass.data[DOMAIN][entry.entry_id][UPDATE_CALLBACK],
            )
            for instrument in (
                instrument
                for instrument in data.instruments
                if instrument.component == "sensor"
            )
        )

    return True


class VolkswagenSensor(VolkswagenEntity, SensorEntity):
    """Representation of a Volkswagen Connect Sensor."""

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.instrument is not None:
            _LOGGER.debug("Getting state of %s", self.instrument.attr)
        else:
            _LOGGER.debug("Getting state of of a broken entity?")
            return ""

        return self.instrument.state

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        if self.instrument.unit:
            return self.instrument.unit

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Return the device class."""
        if (
            self.instrument.device_class is None
            or self.instrument.device_class in DEVICE_CLASSES
        ):
            return self.instrument.device_class
        _LOGGER.warning("Unknown device class %s", self.instrument.device_class)
        return None

    @property
    def state_class(self) -> SensorStateClass | None:
        """Return the state class."""
        if (
            self.instrument.state_class is None
            or self.instrument.state_class in STATE_CLASSES
        ):
            return self.instrument.state_class
        _LOGGER.warning("Unknown state class %s", self.instrument.state_class)
        return None

    @property
    def entity_category(self) -> EntityCategory | str | None:
        """Return entity category."""
        if self.instrument.entity_type == "diag":
            return EntityCategory.DIAGNOSTIC
        if self.instrument.entity_type == "config":
            return EntityCategory.CONFIG
