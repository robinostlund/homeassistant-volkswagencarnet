"""Number support for Volkswagen Connect integration."""

import logging

from datetime import timedelta

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.const import CONF_SCAN_INTERVAL

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

    # Entity attributes (Home Assistant 2024+)
    _attr_has_entity_name = True

    def __init__(self, *args, **kwargs):
        """Initialize the number entity."""
        super().__init__(*args, **kwargs)
        # Set attributes based on instrument
        self._attr_native_min_value = self._get_min_value()
        self._attr_native_max_value = self._get_max_value()
        self._attr_native_step = self._get_step()
        self._attr_native_unit_of_measurement = self._get_unit()
        self._attr_device_class = self._get_device_class()
        self._attr_entity_category = self._get_entity_category()

    def _get_min_value(self) -> float | None:
        """Get minimum value from instrument."""
        return self.instrument.min_value or None

    def _get_max_value(self) -> float | None:
        """Get maximum value from instrument."""
        return self.instrument.max_value or None

    def _get_step(self) -> float | None:
        """Get step value from instrument."""
        return self.instrument.native_step or None

    def _get_unit(self) -> str | None:
        """Get unit of measurement from instrument."""
        return self.instrument.unit or None

    def _get_device_class(self) -> NumberDeviceClass | None:
        """Get device class from instrument."""
        try:
            device_class = self.instrument.device_class
            if device_class is None:
                return None

            # Validate against NumberDeviceClass enum
            if device_class in NumberDeviceClass.__members__.values():
                return device_class

            _LOGGER.warning(
                "Unknown device class '%s' for %s",
                device_class,
                self.instrument.attr,
            )
            return None
        except (ValueError, AttributeError):
            _LOGGER.warning(
                "Invalid device class '%s' for %s",
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
    def native_value(self) -> float | None:
        """Return the entity value to represent the entity state."""
        return self.instrument.state or None

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        try:
            # Special handling for scan_interval
            if self.instrument.attr == "scan_interval":
                await self._set_scan_interval(int(value))
                return

            # Normal instrument value setting
            await self.instrument.set_value(value)
            self.notify_updated()
        except Exception as err:
            _LOGGER.error(
                "Failed to set value for %s to %s: %s",
                self.instrument.attr,
                value,
                err,
            )
            raise

    async def _set_scan_interval(self, minutes: int) -> None:
        """Set scan interval and persist to config entry."""

        if self.coordinator:
            # Update coordinator interval
            new_interval = timedelta(minutes=minutes)
            self.coordinator.update_interval = new_interval

            # Update instrument state
            self.instrument._current_interval = minutes

            # Persist to config entry options
            self.hass.config_entries.async_update_entry(
                self.coordinator.entry,
                options={
                    **self.coordinator.entry.options,
                    CONF_SCAN_INTERVAL: minutes,
                },
            )

            _LOGGER.debug(
                "Scan interval changed to %s minutes for VIN %s",
                minutes,
                self.vin,
            )

            # Update the state
            self.async_write_ha_state()
