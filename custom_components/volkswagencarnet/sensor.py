"""Sensor support for Volkswagen Connect platform."""

import logging

from homeassistant.components.sensor import (
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

    # Entity attributes (Home Assistant 2024+)
    _attr_has_entity_name = True

    def __init__(self, *args, **kwargs):
        """Initialize the sensor entity."""
        super().__init__(*args, **kwargs)
        # Set attributes based on instrument
        self._attr_native_unit_of_measurement = self._get_unit()
        self._attr_device_class = self._get_device_class()
        self._attr_state_class = self._get_state_class()
        self._attr_suggested_display_precision = self._get_suggested_precision()
        self._attr_entity_category = self._get_entity_category()

    def _get_unit(self) -> str | None:
        """Get unit of measurement from instrument."""
        return self.instrument.unit or None

    def _get_device_class(self) -> SensorDeviceClass | None:
        """Get device class from instrument."""
        try:
            device_class = self.instrument.device_class
            if device_class is None:
                return None

            # Validate against SensorDeviceClass enum
            return SensorDeviceClass(device_class)
        except ValueError:
            _LOGGER.warning(
                "Unknown device class '%s' for %s",
                self.instrument.device_class,
                self.instrument.attr,
            )
            return None

    def _get_state_class(self) -> SensorStateClass | None:
        """Get state class from instrument."""
        try:
            state_class = self.instrument.state_class
            if state_class is None:
                return None

            # Validate against SensorStateClass enum
            return SensorStateClass(state_class)
        except ValueError:
            _LOGGER.warning(
                "Unknown state class '%s' for %s",
                self.instrument.state_class,
                self.instrument.attr,
            )
            return None

    def _get_suggested_precision(self) -> int | None:
        """Get suggested display precision for UI."""
        device_class = self.instrument.device_class

        # No decimal places for distance and speed
        if device_class in (
            SensorDeviceClass.DISTANCE,
            SensorDeviceClass.SPEED,
        ):
            return 0

        # One decimal place for energy consumption, power, and volume
        if device_class in (
            SensorDeviceClass.ENERGY_DISTANCE,
            SensorDeviceClass.POWER,
            SensorDeviceClass.VOLUME,
        ):
            return 1

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
    def native_value(self):
        """Return the state of the sensor."""
        if self.instrument is None:
            _LOGGER.warning("Getting state of a broken entity")
            return None

        _LOGGER.debug("Getting state of %s", self.instrument.attr)
        return self.instrument.state
